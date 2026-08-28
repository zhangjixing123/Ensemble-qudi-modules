from scipy.signal import find_peaks
from scipy.stats import trim_mean
import numpy as np
from random import randint
from math import pi

from qudi.core.module import LogicBase
from qudi.core.connector import Connector
from qudi.core.statusvariable import StatusVar
from qudi.util.mutex import Mutex
from qudi.util.datafitting import FitContainer, FitConfigurationsModel
from qudi.logic.odmr_logic import OdmrLogic
from qudi.interface.microwave_interface import MicrowaveInterface


class MagnetometerLogic(LogicBase):
    """
    This is the Logic class for a magnetometer type measurement setup.
    This includes an automatic frequency finder and scalar factor optimization
    
    example config for copy-paste:

    TODO
    """

    # declare connectors
    _odmr1 = Connector(name='odmr1',interface='ODMRLogic',optional=True)
    _odmr2 = Connector(name='odmr2',interface='ODMRLogic',optional=True)
    _microwave1 = Connector(name='microwave1',interface='microwave')
    _microwave2 = Connector(name='microwave2',interface='microwave')
    _awg_hfs = Connector(name='awg_hfs',interface='') #TODO
    _awg_mod = Connector(name='awg_mod',interface='')

    # declare status variables
    _scan_averages = StatusVar(name='scan_averages',default=5)
    _odmr_spacing = StatusVar(name='odmr_spacing',default=2e6)
    _sample_rate = StatusVar(name='sample_rate', default=200)
    _meas_mode = StatusVar(name='measurement_mode',default='magnetic')
    _fm_power_bounds = StatusVar(name='fm_power_bounds',default=[(-20, 10)])
    _fm_dev_bounds = StatusVar(name='fm_deviation_bounds',default=[(10, 300e3)])
    _fm_power_step_size = StatusVar(name='fm_power_step_size',default=2)
    _fm_dev_step_size = StatusVar(name='fm_deviation_step_size',default=5e3)
    _hillclimber_iterations = StatusVar(name='hillclimber_iterations',default=20)

    __default_odmrfit_configs = (
        {'name'             : 'Lorentzian Dip',
         'model'            : 'Lorentzian',
         'estimator'        : 'Dip',
         'custom_parameters': None},
    )

    __default_sinfit_configs = (
        {'name'             : 'Sine',
         'model'            : 'Sine',
         'estimator'        : 'default',
         'custom_parameters': None},
    )

    def __init__(self,*args, **kwargs):
        super().__init__(*args,**kwargs)
        self.threadlock = Mutex()
        self._odmrfit_container = None
        self._odmrfit_config_model = None
        self._sinfit_container = None
        self._sinfit_config_model = None


    def on_activate(self):
        self._odmrfit_config_model = FitConfigurationsModel(parent=self)
        self._odmrfit_config_model.load_configs(self.__default_odmrfit_configs)
        self._odmrfit_container = FitContainer(parent=self, config_model=self._odmrfit_config_model)
        self._sinfit_config_model = FitConfigurationsModel(parent=self)
        self._sinfit_config_model.load_configs(self.__default_sinfit_configs)
        self._sinfit_container = FitContainer(parent=self, config_model=self._sinfit_config_model)

    def on_deactivate(self):
        #TODO
        pass

    def run_locking(self,f_start,f_stop,f_points,scan_power):
        """

        For simplicity all odmr scans are run with the same parameter set 
        (although they use different sets of hardware and software connectors)
        
        Note that it is assumed that there is only ever a single frequency channel for 
        each odmr class
        
        """
        odmr1 = self._odmr1()
        odmr2 = self._odmr2()

        mw1 = self._microwave1() 
        mw2 = self._microwave2()

        awg_hfs = self._awg_hfs()
        awg_mod = self._awg_mod()

        sample_rate = self._sample_rate
        scan_averages = self._scan_averages
        odmr_spacing = self._odmr_spacing

        frequency1, frequency2 = self.frequency_finder(odmr1,scan_power,
                                                       f_start,f_stop,f_points,
                                                       0,sample_rate,
                                                       scan_averages,odmr_spacing)


        # Frequency 1 detailed determination and sf optimization
        # TODO: implement functionalities in the awg
        awg_hfs.configure()
        awg_hfs.on()

        # Assumed linewidth of the transition is smaller than 400kHz
        f1_start = frequency1-7e5
        f1_stop = frequency1+7e5
        frequency1 = self.detailed_frequency_finder(odmr1,scan_power,f1_start,
                                                    f1_stop,f_points,0,
                                                    sample_rate,scan_averages)

        #TODO: change from odmr mode to differential

        sf1, power1,dev1 =  self.hillclimber(mw1,self._hillclimber_iterations)

        

        # Frequency 2 detailed determination and sf optimization

        # TODO: implement functionalities in the awg
        awg_hfs.configure()
        awg_hfs.on()

        #TODO: set mode to odmr

        # Assumed linewidth of the transition is smaller than 400kHz
        f2_start = frequency2-7e5
        f2_stop = frequency2+7e5
        
        frequency2 = self.detailed_frequency_finder(odmr2,scan_power,f2_start,
                                                    f2_stop,f_points,0,
                                                    sample_rate,scan_averages)

        #TODO: change from odmr mode to differential


        #TODO: awg_mod channel selection
        self.modulation_phase_optimization(odmr2,mw2,awg_mod,self._meas_mode)

        sf2, power2,dev2 =  self.hillclimber(mw2,self._hillclimber_iterations)

        return frequency1, sf1, power1, dev1, frequency2, sf2, power2, dev2

    def time_tracer(self):
        #TODO
        pass




    def frequency_finder(self,odmr_logic,scan_power,f_start,f_stop,f_steps,sample_rate,averages,spacing=2e6):
        """Helper function to determine the central dips of the NV direction 
        with the highest projected magnetic field.
        Note that the number of averages is only approximate and might be slightly
          lower than specified;

        @param class odmr_logic: Instance of the odmr-logic class
        @param float scan_power: Microwave power to run the odmr with; Unit [dBm]
        @param float start: starting frequency of the scan
        @param float stop: stopping frequency of the scan
        @param int points: number of frequency points in the scan
        @param float sample_rate: sample rate of the odmr scan
        @param int averages: number of individual odmr scans
        @param float spacing: minimal frequency spacing to be detected; Unit: [Hz]

        @return float freq1, float freq2: Found frequencies for the ms=-1 and +1
          states of the NV axis with the largest magnetic field projection
        """

        assert issubclass(odmr_logic,OdmrLogic), 'Parameter odmr_logic is not a subclass of `OdmrLogic`'
        
        # Qudi doesnt allow to directly give the number of scans to run only a total runtime
        # estimate the time it will take and add 1s of buffer
        time_per_scan = f_steps*sample_rate
        run_time = time_per_scan*averages+1
        odmr_logic.runtime = run_time
        odmr_logic.scans_to_average = 0

        # prepare variables for the odmr scan
        odmr_logic.scan_power = scan_power
        odmr_logic.set_frequency_range(f_start,f_stop,f_steps,0)
        odmr_logic.data_rate = sample_rate
        
        odmr_logic.start_odmr_scan()

        data = odmr_logic.signal_data
        x_data = data[0][0][:,0]
        y_data = data[0][0][:,1]

        peak_frequencies = self.odmr_peakfinder(y_data,x_data,spacing)

        # assume the relavant frequencies are well defined center peaks of the 
        # outermost HFS triplet
        freq1 = peak_frequencies[1]
        freq2 = peak_frequencies[-2]

        return freq1, freq2 


    def detailed_frequency_finder(self,odmr_logic,scan_power,f_start,f_stop,f_steps,sample_rate,averages):
        """
        Frequency finder helper function for a single transition using a 
        Lorentzian fitting function

        @param class odmr_logic: instance of the odmr-logic class
        @param iterable frequencies: frequency array of the scan
                
        @return float frequency: Central frequency of the transition; Unit: [Hz]
        """

        assert issubclass(odmr_logic,OdmrLogic), 'Parameter odmr_logic is not a subclass of `OdmrLogic`'


        # Qudi doesnt allow to directly give the number of scans to run only a total runtime
        # estimate the time it will take and add 1s of buffer
        time_per_scan = f_steps*sample_rate
        run_time = time_per_scan*averages+1
        odmr_logic.runtime = run_time
        odmr_logic.scans_to_average = 0

        # prepare variables for the odmr scan
        odmr_logic.scan_power = scan_power
        odmr_logic.set_frequency_range(f_start,f_stop,f_steps,0)
        odmr_logic.data_rate = sample_rate
        
        odmr_logic.start_odmr_scan()

        data = odmr_logic.signal_data
        x_data = data[0][0][:,0]
        y_data = data[0][0][:,1]

        try:
            dump, fit_result = self._odmrfit_container.fit_data('Lorentzian Dip', x_data, y_data)
        except:
            self.log.error('ODMR data fitting failed:')
            return -1


        # Limit the precicion to 1 kHz
        frequency = int(round(fit_result[0][0][1].best_values['center'],-4))

        return frequency


    def modulation_phase_optimization(self,odmr_logic,mw_hardware,awg_hardware,mode):

        assert issubclass(odmr_logic,OdmrLogic), 'Parameter odmr_logic is not a subclass of `OdmrLogic`'
        assert issubclass(mw_hardware,MicrowaveInterface), 'Parameter mw_hardware is not a subclass of `MicrowaveInterface`'
        #TODO: implement awg interface
        assert issubclass(awg_hardware,...), 'Parameter awg_hardware is not a subclass of `...`'
        

        #TODO: awg programming check
        phase_current = 0
        awg_hardware.set_phase(phase_current)

        odmr_logic.start_odmr_scan()

        # Determine current regimes of temperature and magnetic mode

        data = odmr_logic.signal_data
        x_data = data[0][0][:,0]
        y_data = data[0][0][:,1]
        imax = np.argmax(self.smooth(y_data,5))
        imin = np.argmin(self.smooth(y_data,5))

        if x_data[imax] < x_data[imin] and mode=='magnetic':
            freq = x_data[imin]
        elif x_data[imax] < x_data[imin] and mode=='temp':
            freq = x_data[imax]
        elif x_data[imax] > x_data[imin] and mode=='magnetic':
            freq = x_data[imax]
        elif x_data[imax] > x_data[imin] and mode=='temp':
            freq = x_data[imin]
        else:
            self.log.error('Couldn`t determine requested mode; must be `magnetic` or `temp`')
            raise ValueError

        mw_hardware.set_frequency(freq)
        
        
        voltages = None
        phase_vals = np.linspace(0,360,12) #TODO:Find suitable number of points
        for i,phase_current in enumerate(phase_vals):
            awg_hardware.set_phase(phase_current)
            data = self.measure()
            voltages[i] = np.means(data)

        try:
            dump, fit_result = self._sinfit_container.fit_data('Sine', phase_vals*pi/180, voltages)
        except:
            self.log.error('ODMR data fitting failed:')
            return -1

        xvals,yvals = fit_result.high_res_best_fit #TODO: check fit_result structure
        pos = np.argmax(yvals)
        phase_best = xvals(pos)

        return phase_best

    def odmr_peakfinder(self,y_data,frequency,distance_spacing=2e6):
        """Helper function to identify frequencies of peaks/dips in the odmr spectrum
        through the scipy.find_peaks function.
        If no spacing is provided a HFS is assumed and set to 2e6 Hz (2MHz)

        @param iterable y_data: odmr data to be sampled; Unit: [Hz]
        @param itarable frequency: frequency array of the odmr data
        @param value distance_spacing: optional, frequency spacing of the expected 
        peaks; Unit: [Hz]

        @return numpy.ndarray: new array with the frequencies of the found peaks
        """
        

        delta_f = abs((frequency[0]-frequency[1]))
        distance = int(distance_spacing / delta_f)

        if distance == 0:
            self.log.warning('Frequency spacing insufficient to detect specified distance spacing; defaulting to no distance spacing')
            distance = 1

        data_min = min(y_data)
        data_max = max(y_data)
        data_mean = trim_mean(y_data,0.1)
        prom_positive = abs(data_mean-data_max)
        prom_negative = abs(data_mean-data_min)

        # TODO: test if orientation check behaves like expected
        if prom_positive > 1.5*prom_negative:
            prominence = prom_positive*0.3
            peaks, dump = find_peaks(y_data,prominence=prominence,distance=distance)
        elif prom_negative > 1.5*prom_positive:
            prominence = prom_negative*0.3
            peaks, dump = find_peaks(-y_data,prominence=prominence,distance=distance)
        else:
            self.log.warning('Unsure of data orientation; assuming standard ODMR')
            prominence = prom_negative*0.3
            peaks, dump = find_peaks(-y_data,prominence=prominence,distance=distance)

        if not peaks.size:
            self.log.error('No peaks detected; something might be wrong with the data')
            return -1 
        
        peak_frequencies = frequency[peaks]

        return peak_frequencies



    def in_bounds(point, bounds):
        """
        Helper function to check if a point is within the bounds of the search
        @param iterable bounds: nx2 array containing the upper and lower bounds of
        the parameter

        @return boolean flag: indicating if the value is inside the bounds
        """
        # enumerate all dimensions of the point
        for d in range(len(bounds)):
            # check if out of bounds for this dimension
            if point[d] < bounds[d, 0] or point[d] > bounds[d, 1]:
                return False
        return True



    def sf_measurement(self,mw_hardware):
        """
        Helper function to determine the scalar factor of a single transition
        
        @param class mw_harware: instance of the microwave source class

        @return float sf: measured scalar factor; Unit: [V/10kHz]
        """
        
        assert issubclass(mw_hardware,MicrowaveInterface), 'Parameter mw_hardware is not a subclass of `MicrowaveInterface`'

        old_freq = mw_hardware.cw_frequency

        #TODO: Needs proper coding
        data = self.measure()
        v1 = np.mean(data)

        new_freq = old_freq + 10*10**3
        mw_hardware.set_frequency(new_freq) 

        data = self.measure()

        # Reset freq
        mw_hardware.set_frequency(old_freq) 

        v2 = np.mean(data)

        sf = np.abs(v2-v1)

        return sf



    def hillclimber(self,mw_hardware,n_iterations,threshold=0):
        """
        Helper function to run a stochastic hill climber algorithm for the 
        optimization of the scalar factor. 
        Algorithm adapted from https://machinelearningmastery.com/iterated-local-search-from-scratch-in-python/
        Loop is broken if no improvement or only very slight increaments (< threshold)
        over several rounds are achieved 

        @param class mw_hardware: instance of the microwave source class
        @param int n_iteration: number of total maxium iterations to run the optimization
        @param float threshold: optional, threshold improvement parameter to 
                determine the stopping of the algorithm; default: #TODO experimentally determined good value

        @return float sf_best: Optimized scalar factor; Unit: [V/10kHz]
        @return float power_best: Optimized microwave power; Unit: [dBm]
        @return float dev_best: Optimized modulation deviation; Unit: [kHz/V]
        """
        
        assert issubclass(mw_hardware,MicrowaveInterface), 'Parameter mw_hardware is not a subclass of `MicrowaveInterface`'

        # check bounds against constraints and for a reasonable step_size
        mw_constraints = mw_hardware.constraints

        power_bounds = self._fm_power_bounds
        power_step_size = self._fm_power_step_size
        dev_bounds = self._fm_dev_bounds
        dev_step_size = self._fm_dev_step_size

        
        for ii,bound in enumerate(power_bounds):
            power_bounds[ii] = mw_constraints.power_in_range(bound)

        for ii,bound in enumerate(dev_bounds):
                dev_bounds[ii] = mw_constraints.fm_in_range(bound)

        if power_step_size > abs(power_bounds[0]-power_bounds[1])/4:
            self.log.warning('Power step size to large for the given bounds. Step size is reduced')
            power_step_size = abs(power_bounds[0]-power_bounds[1])/4

        if dev_step_size > abs(dev_bounds[0]-dev_bounds[1])/4:
            self.log.warning('Deviation step size to large for the given bounds. Step size is reduced')
            dev_step_size = abs(dev_bounds[0]-dev_bounds[1])/4


        # initial parameters
        power_best, dev_best, sf_best, sf_list, sf_delta = None, None, None, None, None
        while power_best is None or not self.in_bounds(power_best, power_bounds):
            power_best = power_bounds[0] + randint(0,power_bounds[1]-power_bounds[0])
        while dev_best is None or not self.in_bounds(dev_best, dev_bounds):
            dev_best = dev_bounds[0] + randint(0,dev_bounds[1]-dev_bounds[0])

        mw_hardware.set_power(power_best)
        # Assume no configuration was yet done and do it now
        mw_hardware.configure_modulation(dev_best)
        mw_hardware.set_mod_state('ON')
        sf_best = self.sf_measurement(mw_hardware)

        sf_list.append(sf_best)


        for i in range(n_iterations):

            # take step somewhere close to the current optimal point
            power_current, dev_current = None, None
            while power_current is None or not self.in_bounds(power_current, power_bounds):
                power_current = power_best + randint(-5,5) * power_step_size
            while dev_current is None or not self.in_bounds(dev_current, dev_bounds):
                dev_current = dev_best + randint(-5,5) * dev_step_size

            mw_hardware.set_power(power_current)
            mw_hardware.set_mod_deviation(dev_current)
            sf_current = self.sf_measurement()

            if sf_current >= sf_best:
                sf_best = sf_current
                sf_list.append(sf_best)
                sf_delta.append(sf_list[-1]-sf_list[-2])

                power_best = power_current
                dev_best = dev_current

                improvement_counter = i

                # Termination condition 1: If no significant improvemnt (determined by the user) 
                # can be accomplished over several loops, stop 
                if len(sf_list)>5 and all(sf_delta[-3:-1])<threshold: #TODO: determine appropriate threshold
                    break

            # Termination condition 2: If no improvement can be achieved at some point stop
            if i > n_iterations/2 and i - improvement_counter > n_iterations/3:
                break

        return sf_best, power_best, dev_best        


    def smooth(self,data,wsz):
        """
        Helper function to smooth a given dataset.
        Implemented similar to the Matlab function smooth().

        @param iterable data: Dataset to smooth
        @param int wsz: datapoints to smooth, must be odd 
        """
        if wsz % 2 == 0:
            wsz =- 1
            self.log.warning('Smoothing interval not odd, automatically enforced by reducing the interval by 1')
        out0 = np.convolve(data,np.ones(wsz,dtype=int),'valid')/wsz
        r = np.arange(1,wsz-1,2)
        start = np.cumsum(data[:wsz-1])[::2]/r
        stop = (np.cumsum(data[:-wsz:-1])[::2]/r)[::-1]
        return np.concatenate((  start , out0, stop  ))