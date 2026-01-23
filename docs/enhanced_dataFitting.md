# Enhanced Datafitting in Qudi-Core

## 1. Relevant Files
1. One file is modified under path: `src\qudi\util\fit_models\helpers.py`
2. Add a new file under path: `src\qudi\util\fit_models\Npeak.py`
3. One extra package is used in Npeak to provide a additional external GUI for parameters input: `import easygui`

## 2. Funktion
1. In Npeak.py, I provide two extra classes: ***ArbitraryGaussian*** and ***ArbitraryLorentzian***, it makes it possible to realize a Gaussian/Lorentzian Datafitting with arbitrary number of peaks, which using a externel GUI to locate the external input in the class named **estimate_peaks**.
2.  In helpers.py, I add a new class named **estimate_multiple_peaks**, it`s used to estimate the peaks(offset, center, amplitude, sigma) of data. 
3.  **estimate_multiple_peaks** : When the number of estimated peaks is obviously more than the actual situation(We can avoid this happening by observing the diagramm with our eyes), it will show: *'cannot rightly caculate all the desired peaks!!'*.
4.  Basically, this two classes support all datafitting with a input of Integer. The premise is that he follows the previous rule.
5.  There are two options in menu: **dips or peaks**. Through swithing the option it can fit diffrent types of data. Set path:
Settings -> Fit Configuration -> Estimator
![Alt text](img/image.png)

