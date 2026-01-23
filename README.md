# Ensemble Qudi Modules

This is an extended collection of modules for the [qudi](https://github.com/Ulm-IQO/qudi) software suite, forked from the [Ulm-IQO/qudi-iqo-modules](https://github.com/Ulm-IQO/qudi-iqo-modules). Edited by the [Third Physics Institute of University Stuttgart](https://www.pi3.uni-stuttgart.de/).

---
## 📖 Table of Contents
- [Ensemble Qudi Modules](#ensemble-qudi-modules)
  - [📖 Table of Contents](#-table-of-contents)
  - [🌟 Overview](#-overview)
  - [✨ New Features \& Modules](#-new-features--modules)
  - [🛠 Installation](#-installation)
  - [🔄 Relationship with Upstream](#-relationship-with-upstream)
  - [📜 License \& Credits](#-license--credits)

---

## 🌟 Overview
While the original repository provides a robust foundation for NV center experiments, **Ensemble-qudi-modules** introduces specific enhancements for **ensemble spectroscopy** and high-sensitivity magnetic field imaging.

---

## ✨ New Features & Modules
Compared to the upstream repository, this fork includes:

* **Logic Modules**:
    * `EnsembleODMR`: Supports automated frequency sweeping with lock-in detection integration.
    * `PulsedEnsemble`: Specific timing sequences for T1/T2 measurements on ensembles.
* **Hardware Drivers**:
    * Support for [Insert Device Name]: High-speed DAQ interface.
* **GUI Enhancements**:
    * Custom plotting widgets for real-time ensemble signal monitoring.

---

## 🛠 Installation
1.  Ensure you have `qudi` installed.
2.  Clone this repository into your qudi modules directory:
    ```bash
    git clone [https://github.com/zhangjixing123/Ensemble-qudi-modules](https://github.com/zhangjixing123/Ensemble-qudi-modules)
    ```
3.  Add the path to your `sys.path` or move the modules to your local `qudi_modules` folder.

---

## 🔄 Relationship with Upstream
This project aims to stay compatible with the latest updates from `Ulm-IQO/qudi-iqo-modules`. 
* **Sync Status**: Last synced with upstream on [Insert Date].
* **Contributions**: Bug fixes for core modules will be submitted to the upstream via Pull Requests.

## 📜 License & Credits
* Original Framework: Thanks to the IQO team at Ulm University.
* Extensions: Developed by [Your Name/Lab Name].
* License: [Same as original, e.g., GPL-3.0]