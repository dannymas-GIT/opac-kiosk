# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "This script requires administrator privileges. Requesting elevation..."
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    Exit
}

Write-Host "Starting Firefox Kiosk..." -ForegroundColor Green

# Set execution policy to allow running the script
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force

# Run the kiosk application
& python firefox_kiosk.py 