# Firefox Kiosk Application

A Python-based Firefox kiosk application for Windows 11 that limits user interaction and provides configurable auto-refresh.

## Features

- Uses the latest version of Firefox
- Built-in update mechanism for Firefox
- Configurable browser refresh intervals
- Limited UI access (only back and home buttons)
- Blocks hotkeys and Windows keys
- Runs in fullscreen kiosk mode
- Configurable homepage and allowed domains

## Requirements

- Windows 11
- Python 3.8+
- Firefox browser installed

## Installation

1. Install required Python packages:

```bash
pip install -r requirements.txt
```

This will install:
- selenium - For browser automation
- webdriver-manager - For automatically managing the Firefox driver
- pywin32 - For proper window management (required for Firefox embedding)

2. Download the script files to a directory of your choice.

3. Create a `config.json` file or let the application create one with defaults on first run.

## Configuration

The application uses a JSON configuration file with the following options:

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

- `homepage`: The URL to load when the kiosk starts or when the home button is pressed
- `refresh_interval`: Time in minutes to automatically refresh the browser (0 to disable)
- `allowed_domains`: List of allowed domains (empty for no restrictions)
- `firefox_path`: Path to Firefox executable
- `check_updates`: Whether to periodically check for Firefox updates
- `update_check_interval`: How often to check for updates (in hours)
- `fullscreen`: Whether to run in fullscreen mode
- `allow_back`: Show the back button
- `allow_home`: Show the home button
- `kiosk_title`: Window title

## Running the Application

Run the script with administrator privileges (required for key blocking):

```bash
python firefox_kiosk.py
```

For deployment, you can:

1. Create a Windows shortcut that runs the script
2. Add to Windows Startup folder
3. Create a Windows service

## Advanced Configuration

### Automatic Startup

To configure the application to run at system startup, uncomment the `register_for_startup()` line in the main block.

### Running as Administrator

Key blocking requires administrator privileges. The application can be configured to automatically request elevation by uncommenting the `run_as_admin()` line.

## Security Considerations

This kiosk application:
- Runs Firefox in private browsing mode
- Disables disk cache
- Uses strict content blocking
- Disables extension loading
- Blocks keyboard shortcuts including Alt+Tab, Windows keys, Ctrl combinations

## Troubleshooting

Check the `kiosk.log` file for error information if the application isn't working as expected. 