# Launch Firefox Kiosk
# This script launches the Firefox kiosk application with admin privileges

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File "C:\Users\dmas\OpacKiosk\deploy_kiosk.ps1"" -Verb RunAs
    Exit
}

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath

# Launch with -y flag for auto-accept
python firefox_kiosk_simple.py -y
