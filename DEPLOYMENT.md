# Firefox Kiosk Deployment Guide

This guide is intended for IT administrators and technical staff who need to deploy the Firefox Kiosk application across multiple machines or in an enterprise environment.

## Prerequisites

- Windows 10/11
- Python 3.8 or higher
- Firefox browser installed
- Administrator privileges

## Installation

1. **Install required Python packages:**

```
pip install -r requirements.txt
```

This will install:
- selenium (4.18.1) - For browser automation
- webdriver-manager (4.0.1) - For managing the Firefox driver
- psutil (5.9.8) - For process management
- keyboard (0.13.5) - For keyboard hook functionality
- pywin32 (306) - For Windows API integration

2. **Download geckodriver:**

The application should automatically download the correct geckodriver version using webdriver-manager.

3. **Configuration:**

- The application uses default settings, but you can modify specific parameters in the script if needed.
- Default homepage is set to a library catalog system.

## Running for Testing

### Method 1: Direct Python Execution

Run with administrator privileges (required for key blocking):
```
python firefox_kiosk_simple.py -y
```

The `-y` flag enables auto-accept mode to skip confirmations.

### Method 2: Using the Batch Script

1. Double-click `start_kiosk.bat`
2. Accept the UAC prompt for administrator privileges

## Deployment Options

### 1. Manual Deployment

Follow the steps in [INSTALLATION.md](INSTALLATION.md) for basic installation on a single machine.

### 2. Automated Deployment

For deploying across multiple machines, the following options are available:

#### Using Group Policy (Recommended for Domain Environments)

1. Create a network share containing the application files
2. Create a Group Policy Object (GPO) to:
   - Copy the application files to the local machines (e.g., `C:\Program Files\OpacKiosk`)
   - Run the PowerShell deployment script with elevated privileges
   - Configure the application to start at system boot
   - Apply appropriate security settings

#### Using SCCM/Intune

1. Create an application package with the following components:
   - Application files
   - PowerShell deployment script
   - Detection method (presence of shortcut or registry key)
   - Requirement rules (Windows 10/11, PowerShell 5.1+)

2. Deploy the package to target devices
3. Set up monitoring to verify successful deployment

## Security Considerations

### Locking Down the Kiosk

For maximum security in public kiosk scenarios:

1. **Windows Settings**
   - Use Windows Kiosk mode or Assigned Access
   - Disable Windows shortcuts (Win+X, Ctrl+Alt+Del, etc.)
   - Configure auto-login with a dedicated kiosk user account
   - Remove access to Control Panel, Settings, etc.

2. **Firefox Settings**
   - Already configured in the application
   - Uses private browsing mode
   - Custom user.js with security preferences
   - Custom userChrome.css to hide UI elements

3. **Physical Security**
   - Secure physical access to USB ports and hardware
   - Consider cable locks or enclosures
   - Use screen privacy filters if needed

## Maintenance

### Updates

The application handles Firefox updates automatically. To update the application itself:

1. Pull the latest version from GitHub
2. Run the deployment script again
3. Test the application

### Logging and Monitoring

Logs are stored in the `logs` directory:
- `kiosk_[timestamp].log` - Application logs
- `deploy_[timestamp].log` - Deployment logs

Configure log forwarding or monitoring as needed in your environment.

### Troubleshooting Common Issues

#### Application Won't Start After Deployment

- Check if Firefox is installed and accessible
- Verify Python installation and dependencies
- Examine deployment logs for errors
- Test running the application manually with elevated privileges

#### Keyboard/Mouse Blocking Not Working

- Ensure the application is running with administrator privileges
- Check if any security software is blocking low-level hooks
- Verify Windows User Account Control (UAC) settings

#### Firefox Updates Failing

- Check network connectivity to Mozilla servers
- Verify the user account has sufficient permissions
- Review logs for update-related errors

## Uninstallation

To completely remove the application:

1. Delete the application directory
2. Remove the shortcut from the Start Menu and Startup folder
3. Clear any registry entries (optional)

```powershell
# Example uninstallation script
$appPath = "C:\Program Files\OpacKiosk"
$startupFolder = [System.Environment]::GetFolderPath('Startup')
$startupShortcut = Join-Path $startupFolder "Firefox Kiosk.lnk"

# Remove startup shortcut
if (Test-Path $startupShortcut) {
    Remove-Item $startupShortcut -Force
}

# Remove application directory
if (Test-Path $appPath) {
    Remove-Item $appPath -Recurse -Force
}

# Optional: Clean up registry
# Remove-Item -Path "HKCU:\Software\Firefox_Kiosk" -ErrorAction SilentlyContinue
```

## Testing Checklist

After deployment, verify these features:

- [x] Firefox launches in fullscreen kiosk mode
- [x] Address bar is completely hidden
- [x] Alt+Tab is blocked
- [x] Alt+D is blocked (address bar focus)
- [x] Ctrl+Shift+M is blocked (developer tools)
- [x] Navigation is limited to allowed domains
- [x] Back and home buttons work correctly
- [x] The orange line at top is not visible
- [x] Mozilla links function properly

## Troubleshooting

### Common Issues:

1. **Keyboard shortcuts still work:**
   - Ensure the script is running with administrator privileges
   - Verify no other applications are capturing keyboard input

2. **Address bar still visible:**
   - Check Firefox version compatibility
   - Restart the application

3. **Screen is not fullscreen:**
   - Check monitor resolution settings
   - Verify Firefox is properly configured

4. **Firefox fails to start:**
   - Check Firefox installation
   - Verify selenium and geckodriver versions are compatible

### Advanced Troubleshooting:

For detailed logging, modify the script to increase log level:
```python
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kiosk_debug.log"),
        logging.StreamHandler()
    ]
)
```

## Exit Instructions

If you need to exit the kiosk during testing:
1. Attempt to use the Task Manager (Ctrl+Shift+Esc)
2. If blocked, connect remotely or boot in safe mode
3. Terminate python.exe, firefox.exe, and geckodriver.exe processes 