@echo off
:: Windows wrapper — native messaging on Windows needs an .exe/.bat, not a .py.
:: Chrome launches this; we hand stdin/stdout straight to the Python host.
python "%~dp0harpe_host.py" %*
