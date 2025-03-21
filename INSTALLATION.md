# Firefox Kiosk Installation Guide

## System Requirements

- Windows 10/11
- Firefox browser
- Python 3.8 or later
- Administrator privileges

## Quick Installation

1. **Download the Application**
   - Clone this repository or download it as a ZIP file
   - Extract to a dedicated directory (e.g., `C:\OpacKiosk`)

2. **Run the Deployment Script**
   - Right-click on `deploy_kiosk.ps1` and select "Run with PowerShell"
   - If prompted about execution policy, select "Yes" to proceed
   - The script will:
     - Check for Python and Firefox installations
     - Install required Python packages
     - Create a desktop shortcut for easy launching
     - Configure the application for your system

3. **Launch the Kiosk**
   - Double-click the "Launch Firefox Kiosk" shortcut created on your desktop
   - The application will start in full-screen kiosk mode

## Manual Installation

If the deployment script doesn't work for your environment, follow these manual steps:

1. **Install Python Requirements**
   ```
   python -m pip install -r requirements.txt
   ```

2. **Verify Firefox Installation**
   - Ensure Firefox is installed in the default location
   - If using a custom location, update the `config.json` file accordingly

3. **Run the Application**
   ```
   python firefox_kiosk_simple.py -y
   ```

## Auto-Start at System Boot

To configure the kiosk to start automatically when Windows boots:

1. **Using the Deployment Script**
   - Edit `deploy_kiosk.ps1`
   - Uncomment the "Create autostart option" section
   - Run the script again

2. **Manual Configuration**
   - Copy the created shortcut to the Windows Startup folder:
     `C:\Users\[YourUsername]\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

## Configuration Options

The application can be configured by editing `config.json`:

```json
{
    "homepage": "https://www.google.com",
    "refresh_interval": 30,
    "allowed_domains": [],
    "firefox_path": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
    "check_updates": true,
    "update_check_interval": 24,
    "fullscreen": true,
    "allow_back": true,
    "allow_home": true,
    "kiosk_title": "Firefox Kiosk"
}
```

- `homepage`: URL to load when the kiosk starts
- `refresh_interval`: Time in minutes to refresh the browser (0 to disable)
- `allowed_domains`: List of allowed domains (empty for no restrictions)
- `firefox_path`: Path to Firefox executable
- `fullscreen`: Whether to run in fullscreen mode
- `allow_back`: Show the back button
- `allow_home`: Show the home button

## Troubleshooting

### Application Won't Start
- Ensure Python and Firefox are installed correctly
- Check that all required packages are installed
- Run the application from a command prompt to see error messages

### Keyboard Shortcuts Not Blocked
- Make sure the application is running with administrator privileges
- Check the logs for any error messages related to keyboard blocking

### Screen Resolution Issues
- Edit `firefox_kiosk_simple.py` to customize window size and position

### Logs
- Check the `logs` directory for detailed logs
- The most recent deployment log will contain information about any installation issues 