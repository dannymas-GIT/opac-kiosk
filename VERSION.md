# Kiosk System Version Information

Backup Date: 20250321_114421

## System Information

- **Os**: 10.0.22631 N/A Build 22631

## Software Versions

- **Firefox**: Mozilla Firefox 136.0.2
- **Python**: 3.12.9 (tags/v3.12.9:fdb8142, Feb  4 2025, 15:27:58) [MSC v.1942 64 bit (AMD64)]

# Version History

## Version 1.0.0 (March 21, 2025)

### Feature Highlights
- Full-screen Firefox kiosk mode
- Comprehensive keyboard shortcut blocking including Alt+Tab
- Address bar completely hidden
- Navigation controls (back, home)
- Automatic updates for Firefox
- Configurable refresh intervals
- Domain restriction capabilities

### Technical Improvements
- Nuclear Alt+Tab blocking using Windows API
- Multiple redundant methods for address bar hiding
- Custom userChrome.css implementation
- DOM manipulation for persistent UI elements
- Improved error handling and navigation reliability

### Deployment
- PowerShell deployment script
- Batch file launcher
- Desktop shortcut creation
- Auto-start capabilities
- Comprehensive logging
- Administrative privileges management

## Known Issues
- Strong keyboard blocking may trap users in certain edge cases
- Some Firefox internal pages may still show UI elements
- Need to restart after Firefox updates

## Future Plans
- Fine-tune keyboard blocking to be less aggressive
- Improve UI for browser controls
- Add remote management capabilities
- Add screen timeout and screensaver options
