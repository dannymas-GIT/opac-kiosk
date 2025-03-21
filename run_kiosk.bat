@echo off
:: Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running with administrator privileges...
) else (
    echo Requesting administrator privileges...
    powershell Start-Process -FilePath "%~0" -Verb RunAs
    exit /b
)

:: Run the kiosk application
echo Starting Firefox Kiosk...
python firefox_kiosk_simple.py
pause 