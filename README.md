# Ensemble Qudi Modules

This is an extended collection of modules for the [qudi](https://github.com/Ulm-IQO/qudi) software suite, forked from the [Ulm-IQO/qudi-iqo-modules](https://github.com/Ulm-IQO/qudi-iqo-modules). Edited by the [Third Physics Institute of University Stuttgart](https://www.pi3.uni-stuttgart.de/).

---
## 📖 Table of Contents
- [Ensemble Qudi Modules](#ensemble-qudi-modules)
  - [📖 Table of Contents](#-table-of-contents)
  - [🛠 Installation](#-installation)
  - [🌟 Overview](#-overview)
  - [✨ New Features \& Modules](#-new-features--modules)
  - [🔄 Relationship with Upstream](#-relationship-with-upstream)
  - [📜 License \& Credits](#-license--credits)

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

* **New Hardware**:
    * The newly added hardware are all based on the logic originally provided by Qudi.
    * **Microwave**:
      * `microwave/mw_source_tabor.py`: microwave source from Tabor Company. See configuration and see common features in [Tutorial of Tabor Microwave Source](./docs/guide_for_Tabor.md).
* **New Logic Modules**:
    * All new Logic Modules locate under path `src\pi3LabTool`.
    * `LockIn_Pulse`: Supports automated frequency sweeping with lock-in detection integration. See details in [Tutorial of LockIn_Pulse](./docs/guide_for_LI_Pulse.md).
    * `PulseTimeSeries`: Supports non-continuous time-series functionality with independent GUI, supports Nidaq and Spectrum data acquisition cards. See details in [Tutorial of PulseTimeSeries](test.txt).

* **New GUI Enhancements**:
    * Enhanced data fitting in `ODMR` module, supporting multi-peak fitting capability for arbitrary number of peaks, see details in [Enhanced data fitting in ODMR](./docs/enhanced_dataFitting.md).
* **New Functionality Extand (`pi3LabTool`)**:

---

## 🔄 Relationship with Upstream
This project aims to stay compatible with the latest updates from `Ulm-IQO/qudi-iqo-modules`. 
* **Sync Status**: Last synced with upstream on [Insert Date].
* **Contributions**: Bug fixes for core modules will be submitted to the upstream via Pull Requests.

---

## 📜 License & Credits
* Original Framework: Thanks to the IQO team at Ulm University.
* Extensions: Developed by [Third Physics Institute of University Stuttgart](https://www.pi3.uni-stuttgart.de/).
* License: [![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)