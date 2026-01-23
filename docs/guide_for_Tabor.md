# Common Feature of Tabor Microwave Source
---
## 1. Configuration

In Qudi's configuration file `xxx.cfg`, set up tabor microwave source as following form for example:
```bash
odmr_logic:
        module.Class: 'odmr_logic.OdmrLogic'
        connect:
            microwave: 'tabor_3G' 
            data_scanner: 'ni62xx_finite_sampling_input'

tabor_3G:
        module.Class: 'microwave.mw_source_tabor.MicrowaveTabor'
        options:
            channel : 1
            teVendorId  : 0x168C
            teLucidDesktopId  : 0x6002  # Use this for Lucid Desktop - 6GHz
            teLucidPortableId : 0x6081  # Use this for Lucid Portable - 6GHz + 1 Channel
            teLucidBenchtopId : 0x3002  # Use this for Lucid Benchtop - 12GHz + 2 Channels
            BUFFER_SIZE : 256
            FM_MODE     : 0             # 1-ON, 0-OFF

tabor_12G:
        module.Class: 'microwave.mw_source_tabor.MicrowaveTabor'
        options:
            channel : 1                 
            teVendorId  : 0x168C
            teLucidDesktopId  : 0x6002  # Use this for Lucid Desktop - 6GHz
            teLucidPortableId : 0x6081  # Use this for Lucid Portable - 6GHz + 1 Channel
            teLucidBenchtopId : 0x1202  # Use this for Lucid Benchtop - 12GHz + 2 Channels
            BUFFER_SIZE : 256
            FM_MODE     : 0             # 1-ON, 0-OFF
```

The specific parameters are for reference only and should be based on the actual equipment model and the provided parameters.


---
## 2. Common Problems

1. Some common commands can not be executed in given manual book of Tabor microwave source:
    > **\*WAI**: It was marked in official doc but can not be identified by tabor hardware, i choose time.sleep() to replace this command.

    > **\*OPC?** : No matter what state the system is in, always return **OFF**.

    > **:LIST ON?** : List mode is very special in Tabor. Because it always returns **OFF**, although it can also work in this mode. I use a software method to mark the state of list in hardware file of Tabor.

    > **\*RST** : Reset Command in Tabor seems make no sense. So for *SWEEP MODE* and *LIST MODE*, the only way to reset both modes (it means, let the output back to the first Frequency) is to firstly turn off the output, then initialize the parameters again, finally turn on the output. Anyway it seems Tabor doesn`t support the *soft switching Tech*.
2. Some strange Properties of Tabor:
    > Tabor doesn`t support Pyvisa and cannot be identified by NI MAX, use Pyusb instead to solve this problem.

    > Sometime bad performance in low Frequency. It performes better working above about 300 MHZ, but this seems to only be accidental events.



In **mw_source_tabor.py**, the definition of each functions following the given interface provided by Qudi:

```bash
class MicrowaveTabor(MicrowaveInterface):
   ...
   def on_activate(self):
      # used to connect the device with PC and configure basic parameters

   def on_deactivate(self):
      # used to disconnect the device with PC

   def set_cw(self, frequency, power):
      # configure the parameters in CW mode, which related to frequency and power, and make sure the LIST mode and SWEEP mode are closed.

   def configure_scan(self, power, frequencies, mode, sample_rate):
      # cofigure the parameters in corresponding mode, using parameters we have given before

   def off(self):
      # switch off the microwave output
   
   def cw_on(self):
      # Switches on cw microwave output.
   
   def start_scan(self):
      # Qudi`s logic, using the selected mode and parameters to start scanning. Firstly make sure the corresponding parameters have been successfully written, and then the output is opened.

   def reset_scan(self):
      # only for SWEEP and LIST mode, return to the first state of thedefined list of parameters. Because Tabor dosen`t support a soft reset, this function is important.
   
   def readData(self, data)  &  def _command_wait(self, command_str):
      # used to read data / send data through USB
   
   def _in_list_mode(self):
      # Determine whether the current state is in the LIST mode and return a Boolean variable.
      # ATTENTION: Tabor has some problem of returning a right state of LIST, here I use a variable self._list_state to replace it.

    def _in_sweep_mode(self):
      # Determine whether the current state is in the SWEEP mode and return a Boolean variable.

    def _in_cw_mode(self):
      # Determine whether the current state is in the CW mode and return a Boolean variable.

    def _write_list(self):
      # write parameters of LIST mode.

    def _write_sweep(self):
      # write parameters of SWEEP mode.

    def _set_trigger_edge(self):
      # set the effective direction of trigger.
```