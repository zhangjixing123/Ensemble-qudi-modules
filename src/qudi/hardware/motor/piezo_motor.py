from collections import OrderedDict

from qudi.core.module import Base
#from qudi.util.paths import get_home_dir
#from qudi.util.paths import get_main_dir
#from ctypes import c_long, c_buffer, c_float, windll, pointer
from qudi.interface.process_control_interface import ProcessSetpointInterface
#import os
#import platform
from pylablib.devices import Thorlabs
import numpy as np
from qudi.core.configoption import ConfigOption
from qudi.core.statusvariable import StatusVar


#This is for the use of KIM101 piezo controller with 1 or 2 axis piezo motion (PD1).
#To get the serial number of the device use:
#   print(Thorlabs.list_kinesis_devices())
#and look for the number in the tuple with 'Piezo Motor Controller' 
#in the given dictionary.
#To use the channels onto which the piezo motors
#are connected give a tuple channel=(x,y) (for example: channel=(1,2),
#with x Axis connected to channel 1 and y Axis to channel 2)
#to the class. If only one motor is connected, implement the
#channels by setting the not used Axis to a not used channel (for example: channel=(1,3),
#with no x Axis used and y Axis connected to channel 3).
#Mention: Always the second number in the tuple will be y Axis 
#and th first will be x Axis --> can be (3,1) aswell (x Axis on 3 and y Axis on 1)

class PiezoStage(Base):
    """
    ...

    PiezoStage:
        module.Class: 'motor.piezo_motor.PiezoStage'
        options:
            serialnumber: '97250048'
            channel: '(1,2)' # tuple

    
    
    """

    _serialnumber = ConfigOption(name='serialnumber', missing='error')
    _channel = ConfigOption(name='channel', missing='error')
    _setpoints = StatusVar(name='current_setpoints', default=dict())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.channel_x = int(self._channel[1])
        self.channel_y = int(self._channel[3])
        

    def on_activate(self):
        self.travel_size = 0.01
        self.step_size = 0.0000028
        self.max_step_size = 0.000003  # m
        self.max_step_frequency = 2000  # Hz
        self.max_velocity = 0.003  # mm/s
        self.max_voltage = 125  # V
        self.velocity_x = 0.0005
        self.velocity_y = 0.0005
        self.controller = Thorlabs.kinesis.KinesisPiezoMotor(self._serialnumber)
        if self.controller.is_opened() == True:
            self.controller.setup_drive(max_voltage=self.max_voltage, velocity=int(self.velocity_x / self.step_size),
                                        channel=self.channel_x)
            self.controller.setup_drive(max_voltage=self.max_voltage, velocity=int(self.velocity_y / self.step_size),
                                        channel=self.channel_y)
        else:
            raise NameError("Motor is not connected, check serial number")
        return

    def on_deactivate(self):
        self.controller.stop()
        self.controller.setup_drive(max_voltage=self.max_voltage, velocity=int(self.velocity_x / self.step_size), channel=self.channel_x)
        self.controller.setup_drive(max_voltage=self.max_voltage, velocity=int(self.velocity_y / self.step_size), channel=self.channel_y)
        self.controller.close()
        return

    def get_constraints(self):
        constraints = OrderedDict()
        axis0 = {'label': 'x',
                 'unit': 'm',
                 'pos_min': -self.travel_size,
                 'pos_max': self.travel_size,
                 'pos_step': self.step_size,
                 'vel_min': 0,
                 'vel_max': self.max_velocity,
                 'voltage_max': self.max_voltage,
                 'max_step_freq': self.max_step_frequency}

        axis1 = {'label': 'y',
                 'unit': 'm',
                 'pos_min': -self.travel_size,
                 'pos_max': self.travel_size,
                 'pos_step': self.step_size,
                 'vel_min': 0,
                 'vel_max': self.max_velocity,
                 'voltage_max': self.max_voltage,
                 'max_step_freq': self.max_step_frequency}
        
        constraints[axis0['label']] = axis0
        constraints[axis1['label']] = axis1     
        return constraints   

    def set_activity_state(self, channel: str, active: bool) -> None:
        """ Set activity state for given channel.
        State is bool type and refers to active (True) and inactive (False).
        """
        if active == True:
            self.controller.enable_channels(channel)
        else:
            pass
        
        
    def get_activity_state(self, channel: str) -> bool:
        """ Get activity state for given channel.
        State is bool type and refers to active (True) and inactive (False).
        """
        self.controller.get_status(channel)

    def activity_states(self) -> dict[str, bool]:
        return {ch: self.controller.get_status(ch)["enable"] for ch in range(1,5)}

    def set_setpoint(self, channel: str, value: float) -> None:
        """ Set new setpoint for a single channel """
        self._setpoints[channel] = value
        

    def get_setpoint(self, channel: str) -> float:
        """ Get current setpoint for a single channel """
        return self._setpoints[channel]


    def move_rel(self, param_dict):
        x = param_dict['x']
        y = param_dict['y']
        if np.absolute(self.controller.get_position(channel=self.channel_x) * self.step_size + x) < self.travel_size:
            if self.controller.is_moving(channel=self.channel_x) == False and self.controller.is_moving(
                    channel=self.channel_y) == False:
                self.controller.enable_channels(channel=self.channel_x)
                self.controller.move_by(x / self.step_size, channel=self.channel_x)
                self.controller.wait_move(channel=self.channel_x)
                self.controller.stop()
            else:
                raise NameError("Motor is moving, wait until done before giving a new command")
        else:
            raise NameError("Distance is out of possible x travel size (max_travel_size = +-0.01)")
        if np.absolute(self.controller.get_position(channel=self.channel_y) * self.step_size + y) < self.travel_size:
            if self.controller.is_moving(channel=self.channel_x) == False and self.controller.is_moving(
                    channel=self.channel_y) == False:
                self.controller.enable_channels(channel=self.channel_y)
                self.controller.move_by(y / self.step_size, channel=self.channel_y)
                self.controller.wait_move(channel=self.channel_y)
                self.controller.stop()
            else:
                raise NameError("Motor is moving, wait until done before giving a new command")
        else:
            raise NameError("Distance is out of possible y travel size (max_travel_size = +-0.01)")
        return

    def move_abs(self, param_dict):
        x = param_dict['x']
        y = param_dict['y']
        if np.absolute(x) < self.travel_size:
            if self.controller.is_moving(channel=self.channel_x) == False and self.controller.is_moving(
                    channel=self.channel_y) == False:
                self.controller.enable_channels(channel=self.channel_x)
                self.controller.move_to(x / self.step_size, channel=self.channel_x)
                self.controller.wait_move(channel=self.channel_x)
            else:
                raise NameError("Motor is moving, wait until done before giving a new command")
        else:
            raise NameError("Distance is out of possible x travel size (max_travel_size = +-0.01)")
        if np.absolute(y) < self.travel_size / self.step_size:
            if self.controller.is_moving(channel=self.channel_x) == False and self.controller.is_moving(
                    channel=self.channel_y) == False:
                self.controller.enable_channels(channel=self.channel_y)
                self.controller.move_to(y / self.step_size, channel=self.channel_y)
                self.controller.wait_move(channel=self.channel_y)
            else:
                raise NameError("Motor is moving, wait until done before giving a new command")
        else:
            raise NameError("Distance is out of possible y travel size (max_travel_size = +-0.01)")
        return

    def abort(self):
        self.controller.stop()
        return 0

    def get_pos(self, param_list=None):
        x_position = self.controller.get_position(channel=self.channel_x) * self.step_size
        y_position = self.controller.get_position(channel=self.channel_y) * self.step_size
        return x_position, y_position

    def get_status(self, param_list=None):
        return self.controller.get_status(channel=self.channel_x), self.controller.get_status(channel=self.channel_y)

    def calibrate(self, param_list=None):
        if param_list is not None:
            if 'x' in param_list:
                self.controller.set_position(channel=self.channel_x) == 0
            if 'y' in param_list:
                self.controller.set_position(channel=self.channel_y) == 0
        else:
            self.controller.set_position(channel=self.channel_x) == 0
            self.controller.set_position(channel=self.channel_y) == 0
        return 0

    def get_velocity(self, param_list=None):
        return self.controller.get_drive_parameters(self.channel_x)[1] * self.step_size, self.controller.get_drive_parameters(self.channel_y)[1] * self.step_size

    def set_velocity(self, param_dict):
        if param_dict['x'] >= 0 and param_dict['x'] <= self.max_velocity:
            self.velocity_x = param_dict['x']
            self.controller.setup_drive(max_voltage=self.max_voltage, velocity=int(self.velocity_x / self.step_size),
                                        channel=self.channel_x)
        if param_dict['y'] >= 0 and param_dict['y'] <= self.max_velocity:
            self.velocity_y = param_dict['y']
            self.controller.setup_drive(max_voltage=self.max_voltage, velocity=int(self.velocity_y / self.step_size),
                                        channel=self.channel_y)
        if param_dict['x'] > self.max_velocity or param_dict['y'] > self.max_velocity:
            raise NameError("The Velocity can't be set > 0.003 mm/s (max velocity)")
        return 0


"""
class piezo_controller():
    def __init__(self, path_dll, serialnumber, hwtype, label='', unit='m'):
        return

    def getNumberOfHardwareUnits(self):
        return

    def getSerialNumberByIdx(self, index):
        return

    def setSerialNumber(self, SerialNum):
        return

    def initializeHardwareDevice(self):
        return

    def getHardwareInformation(self):
        return

    def get_stage_axis_info(self):
        return

    def set_stage_axis_info(self, pos_min, pos_max, pitch, unit=1):
        return

    def getHardwareLimitSwitches(self):
        return

    def setHardwareLimitSwitches(self, switch_reverse, switch_forward):
        return

    def getVelocityParameters(self):
        return

    def get_velocity(self):
        return

    def setVelocityParameters(self, minVel, acc, maxVel):
        return

    def set_velocity(self, maxVel):
        return

    def getVelocityParameterLimits(self):
        return

    def get_home_parameter(self):
        return

    def set_home_parameter(self, home_dir, switch_dir, home_vel, zero_offset):
        return

    def get_pos(self):
        return

    def move_rel(self, relDistance):
        return

    def move_abs(self, absPosition):
        return

    def mcRel(self, relDistance, moveVel=0.5e-3):
        return

    def mcAbs(self, absPosition, moveVel=0.5):
        return

    def move_bc_rel(self, relDistance):
        return

    def mbAbs(self, absPosition):
        return

    def get_status(self):
        return

    def identify(self):
        return

    def cleanUpAPT(self):
        return

    def abort(self):
        return

    def go_home(self):
        return

    def set_backlash(self, backlash):
        return

    def get_backlash(self):
        return
"""