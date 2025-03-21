@echo off
REM Quick Start Firefox Kiosk
REM This is a simplified launcher for the Firefox kiosk application

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

REM Launch with auto-accept and minimal output
python firefox_kiosk_simple.py -y --quiet

REM If Python returns an error, show a message
if %ERRORLEVEL% neq 0 (
    echo.
    echo Error launching kiosk application.
    echo For detailed logs, check the logs directory.
    timeout /t 10
) 