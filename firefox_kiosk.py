#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Firefox Kiosk Application for Windows
-------------------------------------

A kiosk application that runs Firefox in a restricted environment,
limiting user interaction and providing configurable auto-refresh.
"""

import os
import sys
import json
import time
import logging
import ctypes
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from urllib.parse import urlparse
import ctypes.wintypes
import winreg

from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from webdriver_manager.firefox import GeckoDriverManager

# Configure logging
logging.basicConfig(
    filename='kiosk.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('firefox_kiosk')

# Constants
DEFAULT_CONFIG = {
    "homepage": "https://www.google.com",
    "refresh_interval": 30,
    "allowed_domains": [],
    "firefox_path": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
    "check_updates": True,
    "update_check_interval": 24,
    "fullscreen": True,
    "allow_back": True,
    "allow_home": True,
    "kiosk_title": "Firefox Kiosk"
}
CONFIG_FILE = "config.json"

# Windows API Constants for key blocking
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# List of virtual key codes to block
BLOCKED_KEYS = [
    0x09,  # TAB
    0x5B,  # LEFT WINDOWS
    0x5C,  # RIGHT WINDOWS
    0x73,  # F4 (Alt+F4)
    # Ctrl key combinations
    0x41,  # A
    0x45,  # E
    0x46,  # F
    0x4E,  # N
    0x50,  # P
    0x53,  # S
    0x54,  # T
    0x57,  # W
]

def is_admin():
    """Check if the script is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Re-run the script as administrator if not already running as such."""
    if not is_admin():
        # Re-run the program with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

def load_config():
    """Load configuration from JSON file or create default if not exists."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Update config with any missing default values
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                return config
        else:
            # Create default config file
            with open(CONFIG_FILE, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, sort_keys=True)
            logger.info(f"Created default configuration file: {CONFIG_FILE}")
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config):
    """Save configuration to JSON file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4, sort_keys=True)
        logger.info(f"Configuration saved to: {CONFIG_FILE}")
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def check_firefox_path(firefox_path):
    """Check if Firefox exists at the specified path."""
    if os.path.exists(firefox_path):
        return firefox_path
    
    # Try common installation paths
    common_paths = [
        "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
        "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
    ]
    
    for path in common_paths:
        if os.path.exists(path):
            logger.info(f"Found Firefox at: {path}")
            return path
    
    logger.error("Firefox not found. Please install Firefox or specify the correct path.")
    return None

def update_firefox(firefox_path):
    """Check for and install Firefox updates."""
    try:
        # Firefox has a built-in update mechanism that can be triggered with -update flag
        subprocess.run([firefox_path, "-update"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE,
                      creationflags=subprocess.CREATE_NO_WINDOW)
        logger.info("Firefox update check completed")
        return True
    except Exception as e:
        logger.error(f"Error updating Firefox: {e}")
        return False

def register_for_startup(app_name, app_path):
    """Register the application to run at Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
        winreg.CloseKey(key)
        logger.info(f"Added {app_name} to startup registry")
        return True
    except Exception as e:
        logger.error(f"Error registering for startup: {e}")
        return False

def unregister_from_startup(app_name):
    """Remove the application from Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        logger.info(f"Removed {app_name} from startup registry")
        return True
    except Exception as e:
        logger.error(f"Error unregistering from startup: {e}")
        return False

class KioskKeyboardHook:
    """Class to manage low-level keyboard hooks to block specific keys."""
    
    def __init__(self):
        self.hooked = False
        self.keyboard_hook = None
        self.keyboard_hook_ptr = None
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        
        # Define HOOKPROC prototype
        self.HOOKPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int, 
            ctypes.c_int, 
            ctypes.wintypes.WPARAM, 
            ctypes.wintypes.LPARAM
        )
        
        # Define KBDLLHOOKSTRUCT structure
        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", ctypes.wintypes.DWORD),
                ("scanCode", ctypes.wintypes.DWORD),
                ("flags", ctypes.wintypes.DWORD),
                ("time", ctypes.wintypes.DWORD),
                ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
            ]
            
        self.PKBDLLHOOKSTRUCT = ctypes.POINTER(KBDLLHOOKSTRUCT)
        self.kbdllhookstruct = KBDLLHOOKSTRUCT
        
    def keyboard_hook_proc(self, n_code, w_param, l_param):
        """Callback for keyboard hook."""
        if n_code >= 0:
            kb_struct = ctypes.cast(l_param, self.PKBDLLHOOKSTRUCT).contents
            vk_code = kb_struct.vkCode
            
            # Check if key should be blocked
            if (w_param in (WM_KEYDOWN, WM_KEYUP, WM_SYSKEYDOWN, WM_SYSKEYUP) and 
                (vk_code in BLOCKED_KEYS or 
                 # Block Alt+Tab combination
                 (vk_code == 0x09 and (kb_struct.flags & 0x20)))):
                return 1  # Block the key
                
            # Block Ctrl+key combinations
            if ((w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN) and 
                (self.user32.GetAsyncKeyState(0x11) & 0x8000) and  # Ctrl key is down
                vk_code in BLOCKED_KEYS):
                return 1  # Block the key
                
            # Block Alt+key combinations
            if ((w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN) and 
                (self.user32.GetAsyncKeyState(0x12) & 0x8000) and  # Alt key is down
                vk_code in BLOCKED_KEYS):
                return 1  # Block the key
                
        # Call the next hook in the chain
        return self.user32.CallNextHookEx(None, n_code, w_param, l_param)
        
    def install_hook(self):
        """Install the keyboard hook."""
        if self.hooked:
            return
            
        # Create hook procedure
        self.keyboard_hook = self.HOOKPROC(self.keyboard_hook_proc)
        self.keyboard_hook_ptr = self.keyboard_hook
        
        # Install hook
        self.hook_id = self.user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self.keyboard_hook_ptr,
            None,
            0
        )
        
        if not self.hook_id:
            error = ctypes.get_last_error()
            logger.error(f"Failed to install keyboard hook. Error code: {error}")
            return False
            
        self.hooked = True
        logger.info("Keyboard hook installed successfully")
        return True
        
    def uninstall_hook(self):
        """Uninstall the keyboard hook."""
        if not self.hooked:
            return
            
        if self.hook_id:
            result = self.user32.UnhookWindowsHookEx(self.hook_id)
            self.hooked = not result
            if result:
                logger.info("Keyboard hook uninstalled successfully")
            else:
                error = ctypes.get_last_error()
                logger.error(f"Failed to uninstall keyboard hook. Error code: {error}")
        
class KioskApplication:
    """Main kiosk application class."""
    
    def __init__(self, config):
        self.config = config
        self.root = tk.Tk()
        self.root.title(config.get("kiosk_title", "Firefox Kiosk"))
        
        # Hide taskbar
        self.taskbar_hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
        if self.taskbar_hwnd:
            ctypes.windll.user32.ShowWindow(self.taskbar_hwnd, 0)
        
        # Initialize variables
        self.driver = None
        self.keyboard_hook = KioskKeyboardHook()
        self.keyboard_hook.install_hook()
        
        # Set up UI
        self.setup_ui()
        
        # Block Alt+F4 and other close attempts
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Make window fullscreen and remove decorations
        if config.get("fullscreen", True):
            # Order matters: first remove decorations, then set fullscreen
            self.root.overrideredirect(True)
            self.root.attributes('-topmost', True)
            
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        
        # Start browser initialization
        self.initialize_browser()
        
        # Set up periodic position check
        self.root.after(1000, self.check_browser_window_position)
        
    def setup_ui(self):
        """Set up the UI elements."""
        # Configure the main window
        self.root.configure(bg='black')
        
        # Configure the grid
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)
        
        # Create control frame for back/home buttons
        self.control_frame = tk.Frame(self.root, bg='black', height=30)
        self.control_frame.grid(row=0, column=0, sticky='ew')
        
        # Add buttons based on config
        btn_column = 0
        
        if self.config["allow_back"]:
            self.back_btn = ttk.Button(self.control_frame, text="← Back", command=self.go_back)
            self.back_btn.grid(row=0, column=btn_column, padx=5, pady=5)
            btn_column += 1
            
        if self.config["allow_home"]:
            self.home_btn = ttk.Button(self.control_frame, text="🏠 Home", command=self.go_home)
            self.home_btn.grid(row=0, column=btn_column, padx=5, pady=5)
            btn_column += 1
            
        # Add status label
        self.status_label = tk.Label(self.control_frame, text="Starting browser...", bg="black", fg="white")
        self.status_label.grid(row=0, column=btn_column, padx=5, pady=5, sticky='e')
        
        # Make the window fullscreen if configured
        if self.config["fullscreen"]:
            self.root.attributes('-fullscreen', True)
        else:
            # Set a reasonable default size if not fullscreen
            self.root.geometry("1024x768")
            
        # Remove window decorations for kiosk mode
        self.root.overrideredirect(True)
        
        # Update the UI once before launching browser to show controls
        self.root.update()
        
    def initialize_browser(self):
        """Initialize and configure Firefox browser."""
        try:
            firefox_options = webdriver.FirefoxOptions()
            firefox_options.add_argument('--kiosk')
            firefox_options.add_argument('--private-window')
            
            # Create Firefox profile with restricted settings
            firefox_profile = webdriver.FirefoxProfile()
            firefox_profile.set_preference("browser.privatebrowsing.autostart", True)
            firefox_profile.set_preference("browser.sessionstore.resume_from_crash", False)
            firefox_profile.set_preference("browser.tabs.forceHide", True)
            firefox_profile.set_preference("browser.toolbars.bookmarks.visibility", "never")
            firefox_profile.set_preference("browser.fullscreen.autohide", False)
            firefox_profile.set_preference("browser.tabs.firefox-view", False)
            firefox_profile.set_preference("browser.chrome.toolbar_tips", False)
            firefox_profile.set_preference("browser.urlbar.trimURLs", True)
            firefox_profile.set_preference("browser.urlbar.hideGoButton", True)
            firefox_profile.set_preference("browser.newtabpage.enabled", False)
            firefox_profile.set_preference("browser.newtab.preload", False)
            firefox_profile.set_preference("dom.disable_window_move_resize", True)
            firefox_profile.set_preference("dom.disable_window_flip", True)
            firefox_profile.set_preference("dom.event.contextmenu.enabled", False)
            
            # Create userChrome.css to hide UI elements
            chrome_dir = os.path.join(firefox_profile.path, 'chrome')
            os.makedirs(chrome_dir, exist_ok=True)
            
            with open(os.path.join(chrome_dir, 'userChrome.css'), 'w') as f:
                f.write("""
                    @namespace url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");
                    * { -moz-window-dragging: none !important; }
                    #nav-bar, #TabsToolbar, #sidebar-header, #navigator-toolbox,
                    #identity-box, #tracking-protection-icon-container,
                    #urlbar-container, #PanelUI-button, #page-action-buttons,
                    .browser-toolbar, #titlebar, .tab-line, .tabbrowser-tab,
                    #back-button, #forward-button, #reload-button, #stop-button,
                    #home-button, #downloads-button, #library-button, #sidebar-button,
                    #pocket-button, #fxa-toolbar-menu-button, #new-tab-button,
                    #alltabs-button, #urlbar-zoom-button, #identity-icon,
                    #tracking-protection-icon, #urlbar-label-box,
                    #urlbar-search-mode-indicator, #star-button-box,
                    #pageActionButton, #pageActionSeparator, #reader-mode-button,
                    #containers-panelmenu, #nav-bar-overflow-button,
                    #customizationui-widget-panel, #widget-overflow-fixed-list,
                    #widget-overflow-list, #window-controls,
                    .titlebar-buttonbox-container, .titlebar-spacer,
                    #main-window:not([tabsintitlebar]) .titlebar-buttonbox-container,
                    .titlebar-button, #toolbar-menubar {
                        display: none !important;
                    }
                    
                    #main-window, #content-deck, #browser, browser {
                        margin: 0 !important;
                        padding: 0 !important;
                    }
                    
                    #main-window {
                        -moz-appearance: none !important;
                        background-color: transparent !important;
                    }
                    
                    #titlebar, #TabsToolbar {
                        -moz-window-dragging: no-drag !important;
                    }
                """)
            
            firefox_profile.set_preference("toolkit.legacyUserProfileCustomizations.stylesheets", True)
            firefox_options.profile = firefox_profile
            
            # Initialize WebDriver
            self.status_label.config(text="Starting GeckoDriver...")
            self.root.update()
            
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=firefox_options)
            
            # Navigate to homepage
            homepage = self.config.get("homepage", "")
            if homepage:
                self.driver.get(homepage)
                
            # Position browser window
            self.position_browser_window()
            
        except Exception as e:
            logger.error(f"Error initializing browser: {e}")
            self.status_label.config(text=f"Error: {str(e)}")
            self.show_error(f"Failed to initialize browser: {str(e)}")
    
    def position_browser_window(self):
        """Position and configure the Firefox window."""
        try:
            if not self.driver:
                return
                
            # Get screen dimensions
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            
            # Find Firefox window
            def callback(hwnd, windows):
                if "Mozilla Firefox" in ctypes.windll.user32.GetWindowTextW(hwnd):
                    windows.append(hwnd)
                return True
            
            windows = []
            ctypes.windll.user32.EnumWindows(callback, id(windows))
            
            for hwnd in windows:
                # Remove window styles
                style = ctypes.windll.user32.GetWindowLongW(hwnd, -16)  # GWL_STYLE
                style &= ~(0x00C00000 | 0x00080000 | 0x00040000 | 0x00020000 | 
                          0x00010000 | 0x00000800 | 0x00000400 | 0x00000200 |
                          0x00000100 | 0x00000080 | 0x00000040)
                style |= 0x40000000  # WS_CHILD
                ctypes.windll.user32.SetWindowLongW(hwnd, -16, style)
                
                # Remove extended window styles
                ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
                ex_style &= ~(0x00000100 | 0x00000200 | 0x00000001 |
                            0x00000004 | 0x00040000 | 0x00080000)
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, ex_style)
                
                # Set window position and size
                ctypes.windll.user32.SetWindowPos(
                    hwnd, 0, 0, 0, screen_width, screen_height,
                    0x0002 | 0x0004 | 0x0010 | 0x0020  # SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE
                )
                
                # Create and set window region
                region = ctypes.windll.gdi32.CreateRectRgn(0, 0, screen_width, screen_height)
                ctypes.windll.user32.SetWindowRgn(hwnd, region, True)
                
                # Force window update
                ctypes.windll.user32.UpdateWindow(hwnd)
                
        except Exception as e:
            logger.error(f"Error positioning browser window: {e}")
    
    def navigate_to(self, url):
        """Navigate to a URL, checking domain restrictions if configured."""
        try:
            # Check if URL is allowed based on domain restrictions
            if self.config["allowed_domains"] and not self.is_allowed_domain(url):
                logger.warning(f"Attempted to access restricted domain: {url}")
                self.go_home()
                return
                
            self.driver.get(url)
            logger.info(f"Navigated to: {url}")
            
        except WebDriverException as e:
            logger.error(f"Browser navigation error: {e}")
            
    def is_allowed_domain(self, url):
        """Check if the URL's domain is in the allowed domains list."""
        if not self.config["allowed_domains"]:
            return True
            
        try:
            domain = urlparse(url).netloc
            for allowed in self.config["allowed_domains"]:
                if domain == allowed or domain.endswith(f".{allowed}"):
                    return True
            return False
        except:
            return False
            
    def go_back(self):
        """Navigate back in the browser history."""
        if self.driver:
            self.driver.back()
            
    def go_home(self):
        """Navigate to the configured homepage."""
        if self.driver:
            self.navigate_to(self.config["homepage"])
            
    def refresh_browser(self):
        """Refresh the current page and schedule the next refresh."""
        if self.driver:
            try:
                self.driver.refresh()
                logger.info(f"Auto-refreshed page: {self.driver.current_url}")
            except Exception as e:
                logger.error(f"Error refreshing page: {e}")
                
    def check_for_updates(self):
        """Check for Firefox updates if enabled."""
        if not self.config["check_updates"]:
            return
            
        current_time = datetime.now()
        
        # Check if we need to perform an update check
        if (self.last_update_check is None or 
            (current_time - self.last_update_check).total_seconds() >= 
            self.config["update_check_interval"] * 3600):
            
            logger.info("Checking for Firefox updates...")
            
            # Update Firefox in a separate thread to avoid blocking the UI
            thread = threading.Thread(target=update_firefox, 
                                      args=(self.config["firefox_path"],))
            thread.daemon = True
            thread.start()
            
            self.last_update_check = current_time
            
    def show_error(self, message):
        """Display an error message to the user."""
        error_window = tk.Toplevel(self.root)
        error_window.title("Error")
        error_window.geometry("400x200")
        
        error_label = tk.Label(error_window, text=message, wraplength=380, justify="center")
        error_label.pack(pady=20)
        
        ok_button = ttk.Button(error_window, text="OK", command=error_window.destroy)
        ok_button.pack(pady=10)
        
        # Center the error window
        error_window.update_idletasks()
        width = error_window.winfo_width()
        height = error_window.winfo_height()
        x = (error_window.winfo_screenwidth() // 2) - (width // 2)
        y = (error_window.winfo_screenheight() // 2) - (height // 2)
        error_window.geometry(f'{width}x{height}+{x}+{y}')
        
    def start(self):
        """Start the kiosk application."""
        # Set up periodic update checks
        if self.config["check_updates"]:
            self.last_update_check = datetime.now() - timedelta(
                hours=self.config["update_check_interval"] + 1)  # Force initial check
            self.check_for_updates()
            
            # Schedule periodic update checks
            update_ms = 3600 * 1000  # Check once per hour
            self.root.after(update_ms, self.check_for_updates)
            
        # Set up auto-refresh if enabled
        if self.config["refresh_interval"] > 0:
            # Convert minutes to milliseconds
            refresh_ms = self.config["refresh_interval"] * 60 * 1000
            self.root.after(refresh_ms, self.refresh_browser)
            
        # Start the UI main loop
        self.root.mainloop()
        
    def on_close(self):
        """Clean up and close the application."""
        try:
            # Remove keyboard hook
            if self.keyboard_hook:
                self.keyboard_hook.uninstall_hook()
            
            # Quit browser
            if self.driver:
                self.driver.quit()
            
            # Show taskbar
            if self.taskbar_hwnd:
                ctypes.windll.user32.ShowWindow(self.taskbar_hwnd, 5)  # SW_SHOW
                
            # Force Windows to refresh shell
            ctypes.windll.user32.UpdatePerUserSystemParameters(1, True)
            
            # Restart Explorer if needed
            subprocess.run(['taskkill', '/F', '/IM', 'explorer.exe'],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         creationflags=subprocess.CREATE_NO_WINDOW)
            time.sleep(1)
            subprocess.Popen('explorer.exe')
            
            # Destroy root window
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            # Emergency taskbar restoration
            if self.taskbar_hwnd:
                ctypes.windll.user32.ShowWindow(self.taskbar_hwnd, 5)
            subprocess.Popen('explorer.exe')

def main():
    """Main entry point for the application."""
    logger.info("Starting Firefox Kiosk Application")
    
    # Check for administrator privileges - required for key blocking
    if not is_admin():
        logger.warning("Running without administrator privileges. Key blocking will not work properly.")
        logger.info("Uncomment the run_as_admin() line below for full functionality.")
    
    # Uncomment to require administrator privileges
    # run_as_admin()
    
    # Load configuration
    config = load_config()
    
    # Check Firefox installation
    firefox_path = check_firefox_path(config["firefox_path"])
    if not firefox_path:
        logger.error("Firefox not found. Please install Firefox or specify the correct path in config.json.")
        messagebox.showerror("Firefox Not Found", 
                                "Firefox not found. Please install Firefox or specify the correct path in config.json.")
        sys.exit(1)
    config["firefox_path"] = firefox_path
    save_config(config)
    
    # Uncomment to register for startup
    # register_for_startup("Firefox Kiosk", sys.executable + " " + os.path.abspath(__file__))
    
    # Start the kiosk application
    app = KioskApplication(config)
    app.start()
    
if __name__ == "__main__":
    main() 