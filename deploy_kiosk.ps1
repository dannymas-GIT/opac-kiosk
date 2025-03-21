# Firefox Kiosk Deployment Script
# This script will prepare the environment and launch the kiosk application

# Ensure script is running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Warning "This script requires Administrator privileges. Please re-run as Administrator."
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    Exit
}

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Set up log directory
$logDir = Join-Path $scriptPath "logs"
if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
    Write-Host "Created logs directory" -ForegroundColor Green
}

# Define log file with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "deploy_$timestamp.log"

function Write-Log {
    param ([string]$message)
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $logFile -Append
    Write-Host $message
}

Write-Log "Starting Firefox Kiosk deployment..."

# Check for Python installation
try {
    $pythonVersion = & python --version 2>&1
    Write-Log "Found Python: $pythonVersion"
}
catch {
    Write-Log "Python not found. Please install Python 3.8 or later and try again."
    exit 1
}

# Install required packages
Write-Log "Installing required Python packages..."
try {
    & python -m pip install -r requirements.txt
    Write-Log "Successfully installed required packages"
}
catch {
    Write-Log "Failed to install required packages: $_"
    exit 1
}

# Check for Firefox installation
$firefoxPath = "C:\Program Files\Mozilla Firefox\firefox.exe"
$firefoxExists = Test-Path $firefoxPath

if (-not $firefoxExists) {
    Write-Log "Firefox not found at default location. Checking alternative locations..."
    
    # Check Program Files (x86)
    $firefoxPath = "C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
    $firefoxExists = Test-Path $firefoxPath
    
    if (-not $firefoxExists) {
        Write-Log "Firefox not found. Please install Firefox and try again."
        exit 1
    }
}

Write-Log "Found Firefox at: $firefoxPath"

# Create shortcut for launching kiosk
$WshShell = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path $scriptPath "Launch Firefox Kiosk.lnk"
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = "powershell.exe"
$shortcut.Arguments = "-ExecutionPolicy Bypass -File `"$scriptPath\run_kiosk.ps1`""
$shortcut.WorkingDirectory = $scriptPath
$shortcut.IconLocation = Join-Path $scriptPath "firefox_kiosk.ico"
$shortcut.Description = "Launch Firefox Kiosk Application"
$shortcut.Save()

Write-Log "Created shortcut: $shortcutPath"

# Create autostart option (disabled by default - uncomment to enable)
<#
$startupFolder = [System.IO.Path]::Combine([System.Environment]::GetFolderPath('Startup'))
$startupShortcutPath = Join-Path $startupFolder "Firefox Kiosk.lnk"
Copy-Item -Path $shortcutPath -Destination $startupShortcutPath -Force
Write-Log "Added shortcut to startup folder: $startupShortcutPath"
#>

# Check for geckodriver and download if needed
Write-Log "Checking for geckodriver..."
$geckodriverPath = Join-Path $scriptPath "geckodriver.exe"

if (-not (Test-Path $geckodriverPath)) {
    Write-Log "Geckodriver not found. It will be downloaded automatically when the application runs."
}

# Create/update run_kiosk.ps1 script
$runKioskPath = Join-Path $scriptPath "run_kiosk.ps1"
$runKioskContent = @"
# Launch Firefox Kiosk
# This script launches the Firefox kiosk application with admin privileges

if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    Exit
}

`$scriptPath = Split-Path -Parent `$MyInvocation.MyCommand.Path
Set-Location `$scriptPath

# Launch with -y flag for auto-accept
python firefox_kiosk_simple.py -y
"@

Set-Content -Path $runKioskPath -Value $runKioskContent
Write-Log "Created/updated run_kiosk.ps1 script"

# Offer to run the application
$runNow = Read-Host "Would you like to start the kiosk application now? (y/n)"

if ($runNow -eq "y" -or $runNow -eq "Y") {
    Write-Log "Starting kiosk application..."
    try {
        & python firefox_kiosk_simple.py -y
    }
    catch {
        Write-Log "Failed to start kiosk application: $_"
        exit 1
    }
}
else {
    Write-Log "Deployment completed. You can start the kiosk application by double-clicking 'Launch Firefox Kiosk' shortcut."
}

Write-Log "Deployment script completed successfully." 