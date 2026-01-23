# -*- coding: utf-8 -*-
__all__ = ('multiple_gaussian', 'multiple_lorentzian', 'ArbitraryGaussian', 'ArbitraryLorentzian')

import numpy as np
import easygui
import traceback
from qudi.util.fit_models.model import FitModelBase, estimator
from qudi.util.fit_models.helpers import correct_offset_histogram, smooth_data, sort_check_data
from qudi.util.fit_models.helpers import estimate_multiple_peaks


def multiple_gaussian(x, centers, sigmas, amplitudes):
    """ Mathematical definition of the sum of multiple gaussian functions without any bias.

    WARNING: iterable parameters "centers", "sigmas" and "amplitudes" must have same length.

    @param float x: The independent variable to calculate gauss(x)
    @param iterable centers: Iterable containing center positions for all gaussians
    @param iterable sigmas: Iterable containing sigmas for all gaussians
    @param iterable amplitudes: Iterable containing amplitudes for all gaussians
    """
    assert len(centers) == len(sigmas) == len(amplitudes)
    return sum(amp * np.exp(-((x - c) ** 2) / (2 * sig ** 2)) for c, sig, amp in
               zip(centers, sigmas, amplitudes))


def multiple_lorentzian(x, centers, sigmas, amplitudes):
    """ Mathematical definition of the sum of multiple (physical) Lorentzian functions without any
    bias.

    WARNING: iterable parameters "centers", "sigmas" and "amplitudes" must have same length.

    @param float x: The independent variable to calculate lorentz(x)
    @param iterable centers: Iterable containing center positions for all lorentzians
    @param iterable sigmas: Iterable containing sigmas for all lorentzians
    @param iterable amplitudes: Iterable containing amplitudes for all lorentzians
    """
    assert len(centers) == len(sigmas) == len(amplitudes)
    return sum(amp * sig ** 2 / ((x - c) ** 2 + sig ** 2) for c, sig, amp in
               zip(centers, sigmas, amplitudes))


class ArbitraryGaussian(FitModelBase):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)

    @staticmethod
    def _model_function(x, **kwargs):
        number_peak = (len(kwargs) - 1) // 3
        offset = kwargs['offset']
        tuple_center = list()
        tuple_sigma = list()
        tuple_amplitude = list()
        for i in range(number_peak):
            # tuple_center.append({'center_' + str(i + 1) : kwargs['center_' + str(i + 1)]}) 
            # tuple_sigma.append({'sigma_' + str(i + 1) : kwargs['sigma_' + str(i + 1)]})
            # tuple_amplitude.append({'amplitude_' + str(i + 1) : kwargs['amplitude_' + str(i + 1)]})
            tuple_center.append(kwargs['center_' + str(i + 1)]) 
            tuple_sigma.append(kwargs['sigma_' + str(i + 1)])
            tuple_amplitude.append(kwargs['amplitude_' + str(i + 1)])

        tuple_center = tuple(tuple_center)
        tuple_sigma = tuple(tuple_sigma)
        tuple_amplitude = tuple(tuple_amplitude)

        return offset + multiple_gaussian(x,
                                            tuple_center,
                                            tuple_sigma,
                                            tuple_amplitude)

    @estimator('Peak')
    def estimate_peaks(self, data, x):
        data, x = sort_check_data(data, x)
    
        data_smoothed, filter_width = smooth_data(data)
        leveled_data_smooth, offset = correct_offset_histogram(data_smoothed,
                                                               bin_width=2 * filter_width)
        self.number_peak = easygui.enterbox("input the desired number of peaks", "Datafitting of ODMR")
        self.number_peak = int(self.number_peak)
        # remove some init precesses to here to avoid unnecessary bugs
        temp_sequnse = (list(range(1,self.number_peak + 1)) + [0])*3
        count = 0
        temp_dic = ['amplitude_', 'center_','sigma_']
        # to make the name space not so chaos
        for i in temp_sequnse:
            if i == 0:
                count += 1
                continue
            if count == 0:
                name = temp_dic[count] + str(i)
                self.set_param_hint(name, value=0, min=-np.inf, max=np.inf)
            elif count == 1:
                name = temp_dic[count] + str(i)
                self.set_param_hint(name, value=0., min=-np.inf, max=np.inf)
            else:
                name = temp_dic[count] + str(i)
                self.set_param_hint(name, value=0., min=0., max=np.inf)

        # self definited func: estimate_multiple_peaks
        estimate, limits = estimate_multiple_peaks(leveled_data_smooth, x, self.number_peak, filter_width)

        params = self.make_params()

        for i in range(self.number_peak):
            name_amplitude, name_center, name_sigma = 'amplitude_' + str(i + 1), 'center_' + str(i + 1), 'sigma_' + str(i + 1)
            params[name_amplitude].set(value=estimate['height'][i],
                                  min=limits['height'][i][0],
                                  max=limits['height'][i][1])
            params[name_center].set(value=estimate['center'][i],
                               min=limits['center'][i][0],
                               max=limits['center'][i][1])
            params[name_sigma].set(value=estimate['fwhm'][i] / 2.3548,
                              min=limits['fwhm'][i][0] / 2.3548,
                              max=limits['fwhm'][i][1] / 2.3548)
        return params

    @estimator('Dip')
    def estimate_dip(self, data, x):
        estimate = self.estimate_peaks(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        
        for i in range(self.number_peak):
            name_amplitude = 'amplitude_' + str(i + 1)
            estimate[name_amplitude].set(value=-estimate[name_amplitude].value,
                                    min=-estimate[name_amplitude].max,
                                    max=-estimate[name_amplitude].min)
        return estimate
    


class ArbitraryLorentzian(FitModelBase):
    """ ToDo: Document
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_param_hint('offset', value=0, min=-np.inf, max=np.inf)


    @staticmethod
    def _model_function(x, **kwargs):
        number_peak = (len(kwargs) - 1) // 3
        offset = kwargs['offset']
        tuple_center = list()
        tuple_sigma = list()
        tuple_amplitude = list()
        for i in range(number_peak):
            # tuple_center.append({'center_' + str(i + 1) : kwargs['center_' + str(i + 1)]}) 
            # tuple_sigma.append({'sigma_' + str(i + 1) : kwargs['sigma_' + str(i + 1)]})
            # tuple_amplitude.append({'amplitude_' + str(i + 1) : kwargs['amplitude_' + str(i + 1)]})
            tuple_center.append(kwargs['center_' + str(i + 1)]) 
            tuple_sigma.append(kwargs['sigma_' + str(i + 1)])
            tuple_amplitude.append(kwargs['amplitude_' + str(i + 1)])

        tuple_center = tuple(tuple_center)
        tuple_sigma = tuple(tuple_sigma)
        tuple_amplitude = tuple(tuple_amplitude)

        return offset + multiple_lorentzian(x,
                                            tuple_center,
                                            tuple_sigma,
                                            tuple_amplitude)

    @estimator('Peaks')
    def estimate_peaks(self, data, x):
        data, x = sort_check_data(data, x)
    
        data_smoothed, filter_width = smooth_data(data)
        leveled_data_smooth, offset = correct_offset_histogram(data_smoothed,
                                                               bin_width=2 * filter_width)
        
        self.number_peak = easygui.enterbox("input the desired number of peaks", "Datafitting of ODMR")
        self.number_peak = int(self.number_peak)

        # remove some init precesses to here to avoid unnecessary bugs
        temp_sequnse = (list(range(1,self.number_peak + 1)) + [0])*3
        count = 0
        temp_dic = ['amplitude_', 'center_','sigma_']
        # to make the name space not so chaos
        for i in temp_sequnse:
            if i == 0:
                count += 1
                continue
            if count == 0:
                name = temp_dic[count] + str(i)
                self.set_param_hint(name, value=0, min=-np.inf, max=np.inf)
            elif count == 1:
                name = temp_dic[count] + str(i)
                self.set_param_hint(name, value=0., min=-np.inf, max=np.inf)
            else:
                name = temp_dic[count] + str(i)
                self.set_param_hint(name, value=0., min=0., max=np.inf)

        # self definited func: estimate_multiple_peaks
        estimate, limits = estimate_multiple_peaks(leveled_data_smooth, x, self.number_peak, filter_width)

        params = self.make_params()

        for i in range(self.number_peak):
            name_amplitude, name_center, name_sigma = 'amplitude_' + str(i + 1), 'center_' + str(i + 1), 'sigma_' + str(i + 1)
            params[name_amplitude].set(value=estimate['height'][i],
                                  min=limits['height'][i][0],
                                  max=limits['height'][i][1])
            params[name_center].set(value=estimate['center'][i],
                               min=limits['center'][i][0],
                               max=limits['center'][i][1])
            params[name_sigma].set(value=estimate['fwhm'][i] / 2.3548,
                              min=limits['fwhm'][i][0] / 2.3548,
                              max=limits['fwhm'][i][1] / 2.3548)
        return params

    @estimator('Dips')
    def estimate_dips(self, data, x):
        estimate = self.estimate_peaks(-data, x)
        estimate['offset'].set(value=-estimate['offset'].value,
                               min=-estimate['offset'].max,
                               max=-estimate['offset'].min)
        
        for i in range(self.number_peak):
            name_amplitude = 'amplitude_' + str(i + 1)
            estimate[name_amplitude].set(value=-estimate[name_amplitude].value,
                                    min=-estimate[name_amplitude].max,
                                    max=-estimate[name_amplitude].min)
        return estimate