@echo off
REM Firefox Kiosk Launcher
REM This script launches the Firefox kiosk application with admin privileges

echo Starting Firefox Kiosk...

REM Check for admin privileges and elevate if needed
NET SESSION >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Administrator privileges required. Attempting to elevate...
    powershell -Command "Start-Process '%~dpnx0' -Verb RunAs"
    exit /b
)

REM Set working directory to script location
cd /d "%~dp0"

REM Launch with -y flag for auto-accept
python firefox_kiosk_simple.py -y

REM If Python returns an error, pause to show the error message
if %ERRORLEVEL% neq 0 (
    echo.
    echo Error launching kiosk application. 
    echo Please check that Python and all required packages are installed.
    echo You can run: python -m pip install -r requirements.txt
    pause
) 