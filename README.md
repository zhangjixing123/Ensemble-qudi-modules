# Ensemble Qudi Modules

[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)

This is an extended collection of modules for the [qudi](https://github.com/Ulm-IQO/qudi) software suite, forked from the [Ulm-IQO/qudi-iqo-modules](https://github.com/Ulm-IQO/qudi-iqo-modules). Edited by the [Third Physics Institute of University Stuttgart](https://www.pi3.uni-stuttgart.de/).

---
## 📖 Table of Contents
- [Ensemble Qudi Modules](#ensemble-qudi-modules)
  - [📖 Table of Contents](#-table-of-contents)
  - [🌟 Overview](#-overview)
  - [✨ New Features \& Modules](#-new-features--modules)
  - [🛠 Installation](#-installation)
  - [🔄 Relationship with Upstream](#-relationship-with-upstream)

---

## 🌟 Overview
While the original repository provides a robust foundation for NV center experiments, **Ensemble-qudi-modules** introduces specific enhancements for **ensemble spectroscopy** and high-sensitivity magnetic field imaging, including 3 main parts:
1. New hardware modules.
2. New logic modules.
3. Enhanced GUI modules.
4. Additional functions (independently running from Qudi: `pi3LabTool`)

---

## ✨ New Features & Modules
Compared to the upstream repository, this fork includes:

> **New Hardware**:
>   * The newly added hardware are all based on the logic originally provided by Qudi.
>   * **Microwave**:
>       * `microwave/mw_source_tabor.py`: microwave source from Tabor Company. See configuration and see common features in [Tutorial of Tabor Microwave Source](./docs/guide_for_Tabor.md).
>       * `microwave/mw_source_anapico_4010`:  microwave source of Anapico 4010. See example of configuration in code.
>   * **Spectrum**:
>       * `spectrum/sepctrum_fast_sampling.py` + `spectrum/sepctrum_control.py`: implement data acquisition function in Pulsed logic Module with spectrum data acquisition card. See details in [Tutorial of Pulsed by Spectrum](test.txt).
>       * `spectrum/sepctrum_finite_sampling_input.py`: support data acquisition function in ODMR logic Module with spectrum data acquisition card. See example of configuration in code.
>   * **Third Party**:
>       * 3rd party files to provide some essential packages support
>       * locates in `hardware/thirdparty/...`
>   * `spectrum_spincore_finite_sampling_input.py`: Hardware support for data measurement functionality of new odmr_logic_ensemble Module, calling both spectrum card and spincore together repectively for data collection and pulse blaster. See example of configuration in code.
>   * `tt_spincore_finite_sampling_input.py`: Hardware support for data measurement functionality of new odmr_logic_ensemble Module, calling both timetagger card and spincore together repectively for data collection and pulse blaster. See example of configuration in code.

> **New Logic Modules**:
>   * This section includes a more complete logic based on the logic provided by Qudi, offering more comprehensive functionality and richer GUI interfaces.
>   * **TimeTagger Logic**: 
>       * New logic for timetagger card, including new GUI, Logic and Hardware files for APD data collection, see details in [Tutorial of Timetagger](test.txt).
>       * Involved files: `gui/timetagger.py`, `gui/timetagger.ui`, `logic/timetagger_logic.py`, `hardware/swabian_instrument/timetagger_api.py`, `hardware/swabian_instrument/timetagger_fast_counter_ensemble.py`
>   * **Enhanced Pulsed Logic (GUI)**: 
>       * Provide more effective GUI interfaces and functionalities based on original Pulse logic module of Qudi, see details in [Tutorial of Enhanced Pulsed Logic](test.txt).
>       * Involved files: `gui/pulsed/pulsed_maingui_ensemble.py`,`gui/pulsed/ui_pulse_analysis_ensemble.ui`,`gui/pulsed/ui_pulse_editor_ensemble.ui`
>   * **Enhanced ODMR Logic**:
>       * Provide more effective interfaces and functionalities based on original ODMR logic module of Qudi, improve versatility and isolate global triggers and data acquisition, see details in [Tutorial of Enhanced ODMR Logic](test.txt).
>       * Involved files: `gui/odmr/odmr_control_dockwidget_ensemble.py`, `gui/odmr/odmr_main_window_ensemble.py`, `gui/odmr/odmrgui_ensemble.py`, `logic/odmr_logic_ensemble.py`
>   * **Enhanced Sequence Generator Logic**:
>       * Specific update for Spincore card, integrated in original pulse logic module, achieving faster loading and bigger configuration of max. available number of pulse in pulse blaster.
>       * Involved files: `hardware/spincore/pulse_blaster_esrpro_fast.py`, `logic/pulsed/sequence_generator_logic_fast.py`


> **New GUI Enhancements**:
>   * Enhanced data fitting in `ODMR` module, supporting multi-peak fitting capability for arbitrary number of peaks, see details in [Enhanced data fitting in ODMR](./docs/enhanced_dataFitting.md).

> **New Functionality Extand (`pi3LabTool`)**:
>   * **pi3LabTool**: Additional auxiliary toolkits independent of Qudi, locates in `src/pi3LabTool/`.
>   * `LockIn_Pulse`: Supports automated frequency sweeping with lock-in detection integration. See details in [Tutorial of LockIn_Pulse](./docs/guide_for_LI_Pulse.md).
>   * `PulseTimeSeries`: Supports non-continuous time-series functionality with independent GUI, supports Nidaq and Spectrum data acquisition cards. See details in [Tutorial of PulseTimeSeries](test.txt).
>   * `AWG`: <span style="background-color:red; color: white;">Add introduction </span>. See details in [Tutorial of AWG](test.txt).


---

## 🛠 Installation
1.  Ensure you have `qudi` installed, open the qudi env in anaconda and navigate to the folder you want the modules to install to,  eg. `cd C:/Software`.
2.  Clone this repository into your qudi modules directory:
    ```bash
    git clone https://github.com/zhangjixing123/Ensemble-qudi-modules.git
    ```
    This will create a new folder `C:/Software/Ensemble-qudi-modules`. Do not copy/move this folder around after finishing the installation!
3. Navigate into the folder `cd C:/Software/Ensemble-qudi-modules`.
4.  Add the path to your `sys.path` or move the modules to your local `qudi_modules` folder.
5.  Install and register the modules to your current qudi environment via `python -m pip install -e .`.
6.  Add necessary dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    (**Not necessary but recommended**. If you only perform the previous steps but encounter errors due to missing necessary libraries during actual runtime, it is recommended to perform this operation again.)
7. Open Qudi, switch to your own configuration file.
8. Part of the 3rd party packages (eg. packages from spectrum/timetagger/... companies) should be installed manually.



---



## 🔄 Relationship with Upstream
This project aims to stay compatible with the latest updates from `Ulm-IQO/qudi-iqo-modules`. 
* **Sync Status**: Last synced with upstream on [Insert Date].
* **Contributions**: Bug fixes for core modules will be submitted to the upstream via Pull Requests.

