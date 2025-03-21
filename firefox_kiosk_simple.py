#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Firefox Kiosk Application - Simplified Version
"""

import os
import sys
import json
import logging
import tkinter as tk
from tkinter import messagebox
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
import win32gui
import win32con
import ctypes
from datetime import datetime
import time
import subprocess
import tempfile
import win32api
import atexit
import psutil

# Windows API constants for key blocking
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
VK_X = 0x58  # Virtual key code for 'X'

# List of virtual key codes to block
BLOCKED_KEYS = [
    0x09,  # TAB (Alt+Tab)
    0x5B,  # LEFT WINDOWS
    0x5C,  # RIGHT WINDOWS
    0x1B,  # ESC
    0x2C,  # PRINT SCREEN
    0x73,  # F4 (Alt+F4)
    0x70,  # F1
    0x71,  # F2
    0x72,  # F3
    0x74,  # F5
    0x75,  # F6
    0x76,  # F7
    0x77,  # F8 
    0x78,  # F9
    0x79,  # F10
    0x7A,  # F11
    0x7B,  # F12
    0x2F,  # HELP
    0x9D,  # Right CTRL
    0xA3,  # Left CTRL
    0xA4,  # Left Menu (Alt)
    0xA5,  # Right Menu (Alt)
]

# Keys to allow only with Alt pressed (for Alt+X to work)
ALLOW_WITH_ALT = [
    0x58,  # X key
    0x78,  # x key
]

# Configure enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("kiosk.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('firefox_kiosk')

# Default configuration
DEFAULT_CONFIG = {
    "homepage": "https://westbabylon-suffc.na.iiivega.com/",
    "admin_password": "kiosk1234",
    "firefox_path": "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
    "nav_links": [
        {"icon": "🎬", "text": "NEW Movies", "color": "#e74c3c", "url": "https://www.libraryaware.com/312/NewsletterIssues/ViewIssue/dadfd9c8-1b0a-4a99-b1e5-1266335f9c7e?postId=f1028901-4afd-4d9a-be04-ce36cf48dd45"},
        {"icon": "🎵", "text": "New Music CDs", "color": "#3498db", "url": "https://www.libraryaware.com/312/NewsletterIssues/ViewIssue/7cd0e0c7-a46a-495d-a376-347db93c2357?postId=546db813-ce96-4d1a-b80e-d2904a6bb979#libraryaware-section-992b6fa5-52b5-45b4-bc55-c3b5b4c805fb"},
        {"icon": "🎮", "text": "New Video Games", "color": "#2ecc71", "url": "https://www.libraryaware.com/312/NewsletterIssues/ViewIssue/6e5b2ba4-b3ce-4868-a164-d6988aa3e7cc?postId=6967c414-861f-447c-91de-d4d9daeabb43"},
        {"icon": "📦", "text": "Binge Box's", "color": "#f1c40f", "url": "https://www.libraryaware.com/312/NewsletterIssues/ViewIssue/8d48aeac-9125-4c0a-b9c3-6e19c1442915?postId=a6b8ab60-eeda-4467-82b6-178782c88687"},
        {"icon": "📺", "text": "Roku Streaming", "color": "#9b59b6", "url": "https://search.livebrary.com/search~S67/YRoku+express+streaming&SORT=AX"},
        {"icon": "📅", "text": "Adult Programs", "color": "#e67e22", "url": "https://westbabylon.librarycalendar.com/events/month?age_groups%5B60%5D=60&age_groups%5B61%5D=61"},
        {"icon": "📚", "text": "Opac Old", "color": "#34495e", "url": "https://search.livebrary.com/search~S68"}
    ]
}

def load_config():
    """Load configuration from JSON file or create default if not exists."""
    config_file = "config.json"
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                config = json.load(f)
                logger.info(f"Loaded configuration from {config_file}")
                
                # Update config with any missing default values
                for key, value in DEFAULT_CONFIG.items():
                    if key not in config:
                        config[key] = value
                
                logger.info(f"Using homepage: {config.get('homepage')}")
                return config
        else:
            # Create default config file
            with open(config_file, 'w') as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            logger.info(f"Created default configuration file: {config_file}")
            return DEFAULT_CONFIG
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return DEFAULT_CONFIG

class KeyboardHook:
    """Class to hook into low-level keyboard input and block certain keys."""
    
    def __init__(self):
        self.user32 = ctypes.windll.user32
        self.hooked = False
        self.hook_id = None
        self.exit_callback = None
        
        # Define low-level keyboard hook callback
        self.LowLevelKeyboardProc = ctypes.CFUNCTYPE(
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
        )
        self.keyboard_callback = self.LowLevelKeyboardProc(self.keyboard_hook_proc)
    
    def set_exit_callback(self, callback):
        """Set callback for exit key combination."""
        self.exit_callback = callback
    
    def keyboard_hook_proc(self, n_code, w_param, l_param):
        """Keyboard hook procedure to block specified keys and handle Alt+X."""
        if n_code >= 0:
            # Extract virtual key code
            vk_code = ctypes.cast(l_param, ctypes.POINTER(ctypes.c_int))[0]
            
            # Check for Alt+X combination
            alt_pressed = self.user32.GetAsyncKeyState(0x12) & 0x8000 != 0  # ALT key
            
            if alt_pressed and vk_code == VK_X and w_param == WM_KEYDOWN:
                logger.info("Alt+X detected through keyboard hook")
                if self.exit_callback:
                    # Schedule exit callback to run on main thread
                    self.exit_callback()
                    return 1  # Block further processing
            
            # Always allow Alt+X combination
            if alt_pressed and vk_code in ALLOW_WITH_ALT:
                return self.user32.CallNextHookEx(0, n_code, w_param, l_param)
                
            # Block Windows keys always
            if vk_code in [0x5B, 0x5C]:  # LEFT/RIGHT WINDOWS keys
                logger.debug(f"Blocking Windows key: {vk_code}")
                return 1
                
            # Block Alt+Tab and other combinations
            if vk_code in BLOCKED_KEYS:
                if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                    logger.debug(f"Blocking key: {vk_code}")
                    return 1
                    
            # Check for modifier key state
            ctrl_pressed = self.user32.GetAsyncKeyState(0x11) & 0x8000 != 0
            
            # Block common browser shortcuts
            if alt_pressed and vk_code in [0x25, 0x27, 0x46]:  # Left, Right, F
                if vk_code != 0x25:  # Allow Alt+Left for back navigation
                    logger.debug(f"Blocking Alt+ combination: {vk_code}")
                    return 1
            
            # Block Ctrl+N, Ctrl+T, Ctrl+W, etc.
            if ctrl_pressed and vk_code in [0x4E, 0x54, 0x57, 0x4F, 0x50]:  # N, T, W, O, P
                logger.debug(f"Blocking Ctrl+ combination: {vk_code}")
                return 1
                
            # Block Tab key with any modifier except Alt (Alt+Tab is already blocked)
            if vk_code == 0x09 and w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                logger.debug("Blocking Tab key combination")
                return 1
                
            # Block system key combinations
            if (ctrl_pressed and alt_pressed and vk_code == 0x2E):  # Ctrl+Alt+Del
                logger.debug("Blocking Ctrl+Alt+Del attempt")
                return 1
                
            # Block Ctrl+Esc (Start menu)
            if (ctrl_pressed and vk_code == 0x1B):
                logger.debug("Blocking Ctrl+Esc")
                return 1
                
            # Block Alt+Space (System menu)
            if (alt_pressed and vk_code == 0x20):
                logger.debug("Blocking Alt+Space")
                return 1
                
            # Block Alt+F4 except for our exit dialog
            if (alt_pressed and vk_code == 0x73 and not hasattr(self, '_exit_dialog_showing')):
                logger.debug("Blocking Alt+F4")
                return 1
        
        # Call the next hook
        return self.user32.CallNextHookEx(0, n_code, w_param, l_param)
    
    def install_hook(self):
        """Install the keyboard hook."""
        if not self.hooked:
            # Try multiple times with different approaches
            for attempt in range(3):
                try:
                    logger.info(f"Attempting to install keyboard hook (attempt {attempt+1})")
                    if attempt == 0:
                        # Standard approach
                        self.hook_id = self.user32.SetWindowsHookExA(
                            WH_KEYBOARD_LL,
                            self.keyboard_callback,
                            ctypes.windll.kernel32.GetModuleHandleW(None),
                            0
                        )
                    elif attempt == 1:
                        # Try with explicit window handle
                        try:
                            import win32gui
                            hwnd = win32gui.GetForegroundWindow()
                            self.hook_id = self.user32.SetWindowsHookExA(
                                WH_KEYBOARD_LL,
                                self.keyboard_callback,
                                ctypes.windll.kernel32.GetModuleHandleW(None),
                                win32gui.GetWindowThreadProcessId(hwnd)[0]
                            )
                        except:
                            # Fallback to default approach
                            self.hook_id = self.user32.SetWindowsHookExA(
                                WH_KEYBOARD_LL,
                                self.keyboard_callback,
                                ctypes.windll.kernel32.GetModuleHandleW(None),
                                0
                            )
                    else:
                        # Last resort - try with thread ID 0
                        self.hook_id = self.user32.SetWindowsHookExA(
                            WH_KEYBOARD_LL,
                            self.keyboard_callback,
                            ctypes.windll.kernel32.GetModuleHandleW(None),
                            0
                        )
                    
                    if self.hook_id != 0:
                        self.hooked = True
                        logger.info(f"Keyboard hook installed successfully on attempt {attempt+1}")
                        
                        # Register additional hooks for system keys through other methods
                        self.register_system_keys_block()
                        return True
                    else:
                        logger.error(f"Failed to install keyboard hook on attempt {attempt+1}")
                except Exception as e:
                    logger.error(f"Error installing keyboard hook on attempt {attempt+1}: {e}")
            
            logger.error("All keyboard hook installation attempts failed")
            return False
        return True
    
    def register_system_keys_block(self):
        """Register additional hooks for system keys."""
        try:
            # Block Windows key using raw input
            self.raw_input_device = ctypes.windll.user32.RegisterRawInputDevices
            
            # Another approach: disable Windows key via registry temporarily
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                     "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer", 
                                     0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "NoWinKeys", 0, winreg.REG_DWORD, 1)
                winreg.CloseKey(key)
                logger.info("Disabled Windows keys via registry")
                self._registry_modified = True
            except Exception as e:
                logger.error(f"Could not disable Windows keys via registry: {e}")
            
            # Register for Win+L specifically (lock workstation)
            try:
                user32 = ctypes.windll.user32
                # Try to block Win+L
                user32.BlockInput(True)  # Block input temporarily
                time.sleep(0.1)
                user32.BlockInput(False)  # Restore input
                logger.info("Attempted to block Win+L")
            except Exception as e:
                logger.error(f"Error blocking Win+L: {e}")
            
            logger.info("Additional system key blocking registered")
        except Exception as e:
            logger.error(f"Error registering system key blocking: {e}")
    
    def uninstall_hook(self):
        """Uninstall the keyboard hook."""
        if self.hooked and self.hook_id != 0:
            # First restore Windows keys in registry if we changed it
            if hasattr(self, '_registry_modified') and self._registry_modified:
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                        "Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer", 
                                        0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(key, "NoWinKeys", 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    logger.info("Restored Windows keys in registry")
                except Exception as e:
                    logger.error(f"Error restoring Windows keys in registry: {e}")
            
            # Now unhook the keyboard hook
            result = self.user32.UnhookWindowsHookEx(self.hook_id)
            if result:
                self.hooked = False
                logger.info("Keyboard hook uninstalled")
                return True
            else:
                logger.error("Failed to uninstall keyboard hook")
                return False
        return True

class KioskApp:
    def __init__(self):
        logger.info("=" * 50)
        logger.info("Starting Firefox Kiosk Application")
        logger.info("=" * 50)
        
        # Store start time for process monitoring
        self.start_time = time.time()
        
        # Load configuration
        self.config = load_config()
        self.driver = None
        self.homepage = self.config.get("homepage")
        self.admin_password = self.config.get("admin_password")
        
        logger.info(f"Configured homepage: {self.homepage}")
        
        # Initialize keyboard hook to block certain keystrokes
        self.keyboard_hook = KeyboardHook()
        # Set the exit callback to show the exit dialog
        self.keyboard_hook.set_exit_callback(self.trigger_exit_dialog)
        self.keyboard_hook.install_hook()
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
        # Create control panel window first
        self.root = tk.Tk()
        self.root.title("Kiosk Control")
        
        # Register system-wide Alt+X hotkey (alternate method)
        self.setup_alt_x_hotkey()
        
        # Configure the control panel
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x50+0+0")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.configure(bg='#f8f9fa')
        
        # Create navigation section
        control_frame = tk.Frame(self.root, bg='#f8f9fa', height=50)
        control_frame.pack(fill=tk.X, side=tk.TOP)
        
        # Left navigation buttons
        left_nav_frame = tk.Frame(control_frame, bg='#f8f9fa')
        left_nav_frame.pack(side=tk.LEFT, padx=10)
        
        # Back and Home buttons
        back_btn = tk.Button(left_nav_frame, text="←", font=('Segoe UI', 20, 'bold'), 
                            command=self.go_back, bg='#f8f9fa', relief='flat',
                            padx=8, pady=3, cursor='hand2')
        back_btn.pack(side=tk.LEFT, padx=5)
        
        home_btn = tk.Button(left_nav_frame, text="⌂", font=('Segoe UI', 20, 'bold'), 
                            command=self.go_home, bg='#f8f9fa', relief='flat',
                            padx=8, pady=3, cursor='hand2')
        home_btn.pack(side=tk.LEFT, padx=5)
        
        # Navigation links bar
        self.nav_frame = tk.Frame(control_frame, bg='#f8f9fa')
        self.nav_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        # Add navigation links
        self.setup_navigation_links()
        
        logger.info("Control panel UI initialized")
        
        # Hide taskbar
        self.taskbar_hwnd = win32gui.FindWindow("Shell_TrayWnd", None)
        if self.taskbar_hwnd:
            win32gui.ShowWindow(self.taskbar_hwnd, win32con.SW_HIDE)
            logger.info("Taskbar hidden")
        
        # Start browser
        logger.info("Starting Firefox browser...")
        self.start_browser()
        
        # Bind Alt+X key for exit (multiple methods)
        self.root.bind_all('<Alt-x>', lambda e: self.trigger_exit_dialog())
        self.root.bind_all('<Alt-KeyPress-x>', lambda e: self.trigger_exit_dialog())
        logger.info("Key bindings configured (Alt+X for exit)")
        
        # Prevent window closing
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Start polling for Alt+X independently
        self.start_hotkey_polling()
        
        # Start periodic checks
        self.root.after(2000, self.perform_security_checks)
        
    def setup_alt_x_hotkey(self):
        """Set up Alt+X exit hotkey using multiple methods for maximum reliability."""
        try:
            # Try the RegisterHotKey API
            hwnd = int(self.root.winfo_id())
            
            # Unregister any existing hotkey first
            try:
                ctypes.windll.user32.UnregisterHotKey(hwnd, 1)
            except:
                pass
            
            # Register Alt+X as global hotkey with ID 1
            result = ctypes.windll.user32.RegisterHotKey(
                hwnd,      # Window handle
                1,         # Hotkey ID
                MOD_ALT,   # ALT modifier
                VK_X       # X key
            )
            
            if result:
                logger.info("Registered global Alt+X hotkey via RegisterHotKey API")
            else:
                logger.error(f"Failed to register global hotkey: {ctypes.GetLastError()}")
                
        except Exception as e:
            logger.error(f"Error setting up Alt+X hotkey: {e}")
    
    def start_hotkey_polling(self):
        """Start polling for Alt+X hotkey."""
        def check_alt_x():
            try:
                # Check for Alt+X combination using direct Windows API
                alt_pressed = win32api.GetAsyncKeyState(0x12) & 0x8000 != 0
                x_pressed = win32api.GetAsyncKeyState(VK_X) & 0x8000 != 0
                
                if alt_pressed and x_pressed:
                    logger.info("Alt+X detected by polling")
                    # Use root.after_idle to run on main thread
                    self.root.after_idle(self.trigger_exit_dialog)
                    
                    # Wait a little bit to prevent multiple triggers
                    time.sleep(0.3)
            except Exception as e:
                logger.error(f"Error in Alt+X polling: {e}")
            
            # Continue polling
            self.root.after(100, check_alt_x)
        
        # Start the polling
        self.root.after(100, check_alt_x)
    
    def trigger_exit_dialog(self):
        """Trigger the exit dialog from any thread."""
        try:
            # Schedule the dialog on the main thread if not already called
            if not hasattr(self, '_exit_dialog_showing') or not self._exit_dialog_showing:
                self._exit_dialog_showing = True
                logger.info("Triggering exit dialog")
                # Use after_idle to ensure it runs on the main thread
                self.root.after_idle(self.show_exit_dialog)
        except Exception as e:
            logger.error(f"Error triggering exit dialog: {e}")
    
    def setup_navigation_links(self):
        """Set up the navigation links in the top bar."""
        # Get navigation links from config
        nav_links = self.config.get("nav_links", DEFAULT_CONFIG["nav_links"])
        
        logger.info(f"Setting up {len(nav_links)} navigation links")
        
        # Create labels for each link
        for link in nav_links:
            icon = link.get("icon")
            text = link.get("text")
            color = link.get("color")
            url = link.get("url")
            
            link_frame = tk.Frame(self.nav_frame, bg='#f8f9fa')
            link_frame.pack(side=tk.LEFT, padx=10)
            
            # Icon with color
            icon_label = tk.Label(
                link_frame,
                text=icon,
                bg='#f8f9fa',
                fg=color,
                font=('Segoe UI', 20),  # Increased from 16 to 20
                cursor='hand2'
            )
            icon_label.pack(side=tk.LEFT)
            
            # Text label
            text_label = tk.Label(
                link_frame,
                text=" " + text,
                bg='#f8f9fa',
                fg='#2c3338',
                font=('Segoe UI', 12, 'bold'),  # Increased from 9 to 12 and added bold
                cursor='hand2'
            )
            text_label.pack(side=tk.LEFT)
            
            # Store URL as a property on each label
            icon_label.url = url
            text_label.url = url
            
            # Bind events to both icon and text
            for label in (icon_label, text_label):
                label.bind('<Button-1>', self.on_link_click)
                label.bind('<Enter>', lambda e, i=icon_label, t=text_label, c=color: 
                          self.on_link_enter(i, t, c))
                label.bind('<Leave>', lambda e, i=icon_label, t=text_label, c=color: 
                          self.on_link_leave(i, t))
    
    def on_link_click(self, event):
        """Handle click on navigation link."""
        # Get the URL from the widget that was clicked
        url = event.widget.url
        if url:
            logger.info(f"Navigation link clicked: {url}")
            self.navigate_to(url)
        else:
            logger.error("Navigation link clicked but no URL found")
    
    def on_link_enter(self, icon_label, text_label, color):
        """Handle mouse enter event for navigation links."""
        text_label.configure(fg='#0066cc', font=('Segoe UI', 12, 'bold'))
        # Make the icon slightly larger on hover
        icon_label.configure(font=('Segoe UI', 22))
    
    def on_link_leave(self, icon_label, text_label):
        """Handle mouse leave event for navigation links."""
        text_label.configure(fg='#2c3338', font=('Segoe UI', 12, 'bold'))
        # Return icon to normal size
        icon_label.configure(font=('Segoe UI', 20))
    
    def navigate_to(self, url):
        """Navigate to a URL."""
        if hasattr(self, 'driver') and self.driver:
            logger.info(f"Navigating to: {url}")
            try:
                # Use JavaScript for more reliable navigation in same tab
                self.driver.execute_script(f"window.location.href = '{url}';")
                # Make sure our control panel stays on top
                self.root.after(100, lambda: self.root.attributes('-topmost', True))
            except Exception as e:
                logger.error(f"Navigation error with JavaScript: {e}")
                try:
                    # Fallback to driver.get() method
                    self.driver.get(url)
                except Exception as e2:
                    logger.error(f"Navigation error with driver.get(): {e2}")
                    # Try to restart browser with the URL
                    self.current_url = url
                    self.cleanup_browser()
                    self.start_browser_with_url(url)
        else:
            logger.warning("Cannot navigate: no WebDriver")
            # Try to restart browser with the URL
            self.current_url = url
            self.start_browser_with_url(url)
    
    def start_browser(self):
        """Start Firefox in kiosk mode using Selenium WebDriver."""
        try:
            logger.info("Initializing Firefox with Selenium WebDriver")
            
            # First ensure all Firefox processes are killed
            self.kill_all_firefox_processes()
            
            # Create a Firefox options object
            options = Options()
            options.add_argument('-kiosk')
            options.add_argument('-private')
            options.add_argument('-no-remote')
            options.add_argument('-chrome')  # Hide UI completely - important!
            options.add_argument('-new-tab') # Force new links to open in existing tab
            
            # Core preferences for browser behavior
            options.set_preference("browser.shell.checkDefaultBrowser", False)
            options.set_preference("browser.sessionstore.resume_from_crash", False)
            options.set_preference("browser.sessionstore.max_resumed_crashes", -1)
            options.set_preference("browser.startup.page", 1)
            options.set_preference("browser.startup.homepage", self.homepage)
            options.set_preference("browser.startup.homepage_override.mstone", "ignore")
            options.set_preference("browser.newtabpage.enabled", False)
            
            # Critical UI hiding preferences
            options.set_preference("browser.fullscreen.autohide", False)
            options.set_preference("browser.tabs.forceHide", True)
            options.set_preference("browser.tabs.warnOnClose", False)
            options.set_preference("browser.tabs.warnOnCloseOtherTabs", False)
            options.set_preference("browser.toolbars.bookmarks.visibility", "never")
            options.set_preference("dom.disable_window_move_resize", True)
            options.set_preference("dom.disable_window_flip", True)
            options.set_preference("dom.disable_beforeunload", True)
            options.set_preference("toolkit.legacyUserProfileCustomizations.stylesheets", True)
            options.set_preference("browser.startup.couldRestoreSession.count", -1)
            options.set_preference("browser.disableResetPrompt", True)
            options.set_preference("browser.aboutwelcome.enabled", False)
            
            # Extreme UI hiding preferences
            options.set_preference("browser.tabs.drawInTitlebar", False)
            options.set_preference("browser.chrome.toolbar_style", 0)
            options.set_preference("browser.chrome.site_icons", False)
            options.set_preference("browser.urlbar.trimURLs", True)
            options.set_preference("browser.urlbar.hideGoButton", True)
            options.set_preference("browser.uidensity", 1)
            options.set_preference("browser.ui.zoom.force100", True)
            options.set_preference("browser.uiCustomization.state", '{"placements":{"widget-overflow-fixed-list":[],"nav-bar":[],"toolbar-menubar":["menubar-items"],"TabsToolbar":["tabbrowser-tabs","new-tab-button","alltabs-button"],"PersonalToolbar":["import-button","personal-bookmarks"]},"seen":[],"dirtyAreaCache":[],"currentVersion":16,"newElementCount":4}')
            
            # Address bar specific preferences
            options.set_preference("browser.urlbar.autoFill", False)
            options.set_preference("browser.urlbar.showSearchSuggestionsFirst", False)
            options.set_preference("browser.urlbar.openViewOnFocus", False)
            options.set_preference("browser.urlbar.update1", False)
            options.set_preference("browser.urlbar.update1.interventions", False)
            options.set_preference("browser.urlbar.update1.searchTips", False)
            options.set_preference("browser.urlbar.suggest.searches", False)
            options.set_preference("browser.urlbar.suggest.bookmark", False)
            options.set_preference("browser.urlbar.suggest.history", False)
            options.set_preference("browser.urlbar.suggest.openpage", False)
            options.set_preference("browser.urlbar.suggest.topsites", False)
            
            # Advanced UI control preferences
            options.set_preference("browser.fullscreen.autohide", False)
            options.set_preference("browser.fullscreen.hideChromeUI", True)
            options.set_preference("browser.fullscreen.lockChromeUI", True)
            options.set_preference("browser.display.show_chrome_on_hover", False)
            options.set_preference("general.autoScroll", False)
            
            # Firefox 90+ specific preferences
            options.set_preference("browser.compactmode.show", False)
            options.set_preference("browser.toolbars.keyboard.enabled", False)
            options.set_preference("ui.key.menuAccessKeyFocuses", False)
            options.set_preference("ui.key.menuAccessKey", 0)
            
            # Firefox 115+ specific preferences for address bar hiding
            options.set_preference("browser.contentblocking.features.enabled", False)
            options.set_preference("browser.contentblocking.enabled", False)
            options.set_preference("browser.pagethumbnails.capturing_disabled", True)
            options.set_preference("browser.engagement.navigation-bar.enabled", False)
            options.set_preference("browser.engagement.navigation-bar.display", "none")
            options.set_preference("browser.prefer_color_scheme", 0)
            
            # Force links to open in same tab, not new windows
            options.set_preference("browser.link.open_newwindow", 1)  # 1 = open in the current tab
            options.set_preference("browser.link.open_newwindow.restriction", 0)
            options.set_preference("browser.link.open_newwindow.override.external", 1)
            options.set_preference("browser.link.open_external", 1)  # Same tab
            options.set_preference("browser.search.openintab", False)  # Search results in same tab
            
            # Create a unique profile name
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            profile_name = f"kiosk_profile_{timestamp}"
            
            # Create a Firefox profile
            logger.info(f"Creating Firefox profile: {profile_name}")
            firefox_profile_path = os.path.join(os.environ.get('LOCALAPPDATA'), 'Temp', 'KioskProfiles', profile_name)
            os.makedirs(firefox_profile_path, exist_ok=True)
            
            # Create chrome directory and userChrome.css
            chrome_dir = os.path.join(firefox_profile_path, "chrome")
            os.makedirs(chrome_dir, exist_ok=True)
            
            # Create userChrome.css with the most aggressive approach possible
            with open(os.path.join(chrome_dir, "userChrome.css"), "w") as f:
                # Namespace declarations
                f.write('@namespace url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");\n')
                f.write('@namespace html url("http://www.w3.org/1999/xhtml");\n\n')
                
                # Completely hide Firefox UI with !important flags
                f.write(':root { --hide-nav-bar: true !important; }\n\n')
                
                # Combined selector with multiple properties for nav bar elements
                f.write('/* Ultimate nav bar hiding */\n')
                f.write('#nav-bar, #PersonalToolbar, #TabsToolbar, #titlebar, #navigator-toolbox,\n')
                f.write('#urlbar-container, #urlbar, #page-action-buttons, #identity-box,\n')
                f.write('.urlbar-input-container, #back-button, #forward-button,\n')
                f.write('#tracking-protection-icon-container, #PanelUI-button, #customizableui-special-spring1,\n')
                f.write('#customizableui-special-spring2, .urlbar-history-dropmarker {\n')
                f.write('  visibility: collapse !important;\n')
                f.write('  display: none !important;\n')
                f.write('  -moz-appearance: none !important;\n')
                f.write('  height: 0 !important;\n')
                f.write('  min-height: 0 !important;\n')
                f.write('  max-height: 0 !important;\n')
                f.write('  width: 0 !important;\n')
                f.write('  min-width: 0 !important;\n')
                f.write('  max-width: 0 !important;\n')
                f.write('  overflow: hidden !important;\n')
                f.write('  position: fixed !important;\n')
                f.write('  opacity: 0 !important;\n')
                f.write('  z-index: -999 !important;\n')
                f.write('  pointer-events: none !important;\n')
                f.write('  margin-top: -500px !important;\n')
                f.write('  transform: translateY(-500px) !important;\n')
                f.write('  clip: rect(0px, 0px, 0px, 0px) !important;\n')
                f.write('}\n\n')
                
                # Firefox 115+ specific hiding
                f.write('/* Firefox 115+ specific hiding */\n')
                f.write(':root[titlebarempty="true"] #navigator-toolbox,\n')
                f.write(':root[titlepreface="true"] #navigator-toolbox,\n')
                f.write(':root[titlemodifier="true"] #navigator-toolbox {\n')
                f.write('  visibility: collapse !important;\n')
                f.write('  height: 0 !important;\n')
                f.write('  overflow-y: hidden !important;\n')
                f.write('  position: fixed !important;\n')
                f.write('  z-index: -999 !important;\n')
                f.write('}\n\n')
                
                # Add forced full height for content area
                f.write('/* Ensure content takes full height */\n')
                f.write('browser, browser *, #browser, #content-deck, #content, .browserStack, browser {\n')
                f.write('  margin-top: 0 !important;\n')
                f.write('  padding-top: 0 !important;\n')
                f.write('  max-height: 100vh !important;\n')
                f.write('  height: 100vh !important;\n')
                f.write('  border-top: 0 !important;\n')
                f.write('}\n\n')
                
                # Add specific CSS to handle unique window configurations
                f.write('/* Additional overrides for any UI that might appear */\n')
                f.write('@-moz-document url(chrome://browser/content/browser.xhtml) {\n')
                f.write('  #main-window[chromehidden*="toolbar"] #navigator-toolbox { display: none !important; }\n')
                f.write('  #toolbar-menubar { height: 0 !important; visibility: collapse !important; }\n')
                f.write('  #browser-panel { margin-top: 0 !important; }\n')
                f.write('}\n')
            
            # Create userContent.css
            with open(os.path.join(chrome_dir, "userContent.css"), "w") as f:
                f.write('@-moz-document url("about:blank"), url-prefix("about:"), url-prefix("chrome:"), url-prefix("resource:") {\n')
                f.write('  body, html { background-color: white !important; }\n')
                f.write('  * { overflow: hidden !important; }\n')
                f.write('}\n')
                
                # Add rule to ensure links open in same window
                f.write('@-moz-document url-prefix("") {\n')
                f.write('  a[target="_blank"] { target: "_self" !important; }\n')
                f.write('}\n')
            
            # Create user.js with direct preference overrides
            with open(os.path.join(firefox_profile_path, "user.js"), "w") as f:
                # Basic UI preferences
                f.write('user_pref("browser.tabs.firefox-view", false);\n')
                f.write('user_pref("browser.tabs.drawInTitlebar", false);\n')
                f.write('user_pref("browser.display.focus_ring_on_anything", false);\n')
                f.write('user_pref("browser.display.focus_ring_width", 0);\n')
                f.write('user_pref("browser.display.show_chrome_on_hover", false);\n')
                f.write('user_pref("browser.chromeURL", "");\n')
                
                # Aggressive fullscreen control
                f.write('user_pref("browser.fullscreen.autohide", false);\n')
                f.write('user_pref("browser.fullscreen.hideChromeUI", true);\n')
                f.write('user_pref("browser.fullscreen.lockChromeUI", true);\n')
                
                # Custom XUL settings
                f.write('user_pref("dom.xul.disable", false);\n')
                f.write('user_pref("xpinstall.signatures.required", false);\n')
                
                # Navbar specific settings  
                f.write('user_pref("browser.touchbar.enabled", false);\n')
                f.write('user_pref("browser.tabs.inTitlebar", 0);\n')
                f.write('user_pref("browser.showMenuButton", false);\n')
                
                # Toolbar hiding
                f.write('user_pref("browser.toolbars.legacy.enabled", false);\n')
                f.write('user_pref("browser.toolbars.navbar.enabled", false);\n')
                f.write('user_pref("browser.default.toolbars.navbar.enabled", false);\n')
            
            # Set up Firefox binary path
            firefox_path = self.config.get("firefox_path", "C:\\Program Files\\Mozilla Firefox\\firefox.exe")
            options.binary_location = firefox_path
            
            # Create a service for Firefox driver
            service = Service()
            
            # Create WebDriver with options
            logger.info("Creating WebDriver instance")
            self.driver = webdriver.Firefox(
                service=service,
                options=options
            )
            
            # Store the profile directory for cleanup
            self.firefox_profile_path = firefox_profile_path
            
            # Navigate to homepage
            logger.info(f"Navigating to: {self.homepage}")
            self.driver.get(self.homepage)
            
            # Set a timer to make our control panel come to the front
            self.root.after(3000, self.bring_control_to_front)
            
            # Try to hide address bar with JavaScript after page loads
            self.root.after(5000, self.apply_javascript_fixes)
            
            # Apply additional fixes to hide UI after browser is fully initialized
            self.root.after(8000, self.apply_additional_browser_fixes)
            
            logger.info("Firefox WebDriver started successfully")
            
        except Exception as e:
            logger.error(f"WebDriver start error: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.show_error(f"Failed to start browser: {e}")
    
    def apply_javascript_fixes(self):
        """Apply additional fixes using JavaScript after page load."""
        try:
            if hasattr(self, 'driver') and self.driver:
                logger.info("Applying JavaScript fixes")
                # Execute JavaScript to hide address bar and modify link behavior
                self.driver.execute_script("""
                    // Hide UI elements
                    var style = document.createElement('style');
                    style.textContent = `
                        /* Hide Firefox UI */
                        #navigator-toolbox, #titlebar, #nav-bar, 
                        #PersonalToolbar, #TabsToolbar, #urlbar-container, 
                        #urlbar, #identity-box, .urlbar-input-container, 
                        #back-button, #forward-button, #page-action-buttons,
                        #tracking-protection-icon-container, #PanelUI-button,
                        .urlbar-history-dropmarker { 
                            display: none !important;
                            visibility: hidden !important;
                            opacity: 0 !important;
                            height: 0 !important;
                            width: 0 !important;
                            padding: 0 !important;
                            margin: 0 !important;
                            overflow: hidden !important;
                            position: fixed !important;
                            z-index: -9999 !important;
                            top: -9999px !important;
                            pointer-events: none !important;
                        }
                        
                        /* Fix content positioning */
                        body { 
                            margin-top: 0 !important;
                            padding-top: 0 !important;
                        }
                    `;
                    document.head.appendChild(style);
                    
                    // Try to directly access Firefox chrome context
                    try {
                        if (window.browsingContext && window.browsingContext.topChromeWindow) {
                            let chromeWin = window.browsingContext.topChromeWindow;
                            let chromeDoc = chromeWin.document;
                            
                            // Hide UI elements in chrome document
                            let navBar = chromeDoc.getElementById('nav-bar');
                            if (navBar) navBar.style.display = 'none';
                            
                            let urlBar = chromeDoc.getElementById('urlbar');
                            if (urlBar) urlBar.style.display = 'none';
                            
                            let navigatorToolbox = chromeDoc.getElementById('navigator-toolbox');
                            if (navigatorToolbox) navigatorToolbox.style.display = 'none';
                        }
                    } catch(e) { console.log('Chrome access error: ' + e); }
                    
                    // Override link behavior to open in same tab
                    document.addEventListener('click', function(e) {
                        // Find if we clicked on a link or a child of a link
                        let linkEl = e.target.closest('a');
                        if (linkEl && linkEl.target === '_blank') {
                            e.preventDefault();
                            e.stopPropagation();
                            linkEl.target = '_self';
                            window.location.href = linkEl.href;
                        }
                    }, true);
                    
                    // Try window-level CSS vars that might control UI
                    try {
                        document.documentElement.style.setProperty('--chrome-visibility', 'hidden', 'important');
                        document.documentElement.style.setProperty('--toolbar-height', '0', 'important');
                        document.documentElement.style.setProperty('--toolbar-start-end-padding', '0', 'important');
                    } catch(e) { console.log('CSS var error: ' + e); }
                    
                    // Enable fullscreen
                    try {
                        if (document.documentElement.requestFullscreen) {
                            document.documentElement.requestFullscreen();
                        } else if (document.documentElement.mozRequestFullScreen) {
                            document.documentElement.mozRequestFullScreen();
                        } else if (document.documentElement.webkitRequestFullscreen) {
                            document.documentElement.webkitRequestFullscreen();
                        }
                    } catch(e) { console.log('Fullscreen error: ' + e); }
                """)
                logger.info("JavaScript fixes applied")
        except Exception as e:
            logger.error(f"Error applying JavaScript fixes: {e}")
    
    def apply_additional_browser_fixes(self):
        """Apply additional browser fixes after browser has fully initialized."""
        try:
            if hasattr(self, 'driver') and self.driver:
                logger.info("Applying additional browser fixes")
                
                # Execute Firefox-specific JavaScript for UI hiding
                self.driver.execute_script("""
                    // Create and execute a Firefox chrome script to hide UI
                    try {
                        // Add style directly to the XUL document
                        let chromeWin = window.browsingContext.topChromeWindow;
                        let doc = chromeWin.document;
                        
                        // Create style element for chrome document
                        let style = doc.createElement('style');
                        style.innerHTML = `
                            #navigator-toolbox { display: none !important; }
                            #titlebar { display: none !important; }
                            #nav-bar { display: none !important; }
                        `;
                        doc.head.appendChild(style);
                        
                        // Try to trigger UI refresh
                        chromeWin.UpdateAppearance();
                    } catch(e) { console.log('Chrome script error: ' + e); }
                """)
                
                # Try sending F11 key to toggle full screen
                try:
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    # Create action chain for F11 key
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.F11)
                    actions.perform()
                    
                    logger.info("Sent F11 key to enforce fullscreen")
                except Exception as e:
                    logger.error(f"Error sending F11 key: {e}")
                
                logger.info("Additional browser fixes applied")
        except Exception as e:
            logger.error(f"Error applying additional browser fixes: {e}")
    
    def bring_control_to_front(self):
        """Bring the control panel to the front."""
        logger.info("Bringing control panel to front")
        
        try:
            # Raise the control panel window
            self.root.attributes('-topmost', True)
            self.root.update()
            
            # Avoid excessive checking - only scan once every 5 seconds
            if hasattr(self, '_last_check_time'):
                current_time = time.time()
                if current_time - self._last_check_time < 5:
                    # Schedule next check but with longer delay
                    self.root.after(3000, self.bring_control_to_front)
                    return
            
            # Update check time
            self._last_check_time = time.time()
            
            # Get Firefox window handle if we have a driver
            if hasattr(self, 'driver') and self.driver:
                try:
                    # Find Firefox window
                    def callback(hwnd, extra):
                        """Callback for EnumWindows to find Firefox window."""
                        if win32gui.IsWindowVisible(hwnd):
                            title = win32gui.GetWindowText(hwnd)
                            if "Mozilla Firefox" in title or "Firefox" in title:
                                logger.info(f"Found Firefox window: '{title}'")
                                
                                # Get our control panel height and position
                                control_height = self.root.winfo_height()
                                screen_width = self.root.winfo_screenwidth()
                                screen_height = self.root.winfo_screenheight()
                                
                                # Remove window decorations and disable resizing
                                style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                                new_style = style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME | 
                                                    win32con.WS_MINIMIZE | win32con.WS_MAXIMIZE | 
                                                    win32con.WS_SYSMENU | win32con.WS_MINIMIZEBOX | 
                                                    win32con.WS_MAXIMIZEBOX)
                                win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
                                
                                # Remove all extended window styles
                                ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                                new_ex_style = ex_style & ~(win32con.WS_EX_DLGMODALFRAME | 
                                                        win32con.WS_EX_CLIENTEDGE | 
                                                        win32con.WS_EX_STATICEDGE | 
                                                        win32con.WS_EX_WINDOWEDGE)
                                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)
                                
                                # Position the Firefox window below our control panel
                                win32gui.SetWindowPos(
                                    hwnd, 
                                    win32con.HWND_NOTOPMOST,  # Place below our top-most control panel
                                    0,  # X position
                                    control_height,  # Y position (below control panel)
                                    screen_width,  # Width
                                    screen_height - control_height,  # Height (screen minus control panel)
                                    win32con.SWP_FRAMECHANGED  # Apply the frame changes
                                )
                                
                                # Store the window handle 
                                self.firefox_hwnd = hwnd
                                
                                # Use additional native API to hide title bar
                                try:
                                    # Try to set the Firefox window to borderless
                                    import ctypes
                                    user32 = ctypes.windll.user32
                                    
                                    # Define constants for the SetWindowCompositionAttribute function
                                    DWMWA_CAPTION_BUTTON_BOUNDS = 5
                                    DWMWA_CAPTION_COLOR = 35
                                    DWMWA_VISIBLE_FRAME_BORDER_THICKNESS = 37
                                    
                                    # Try to remove the caption area using DWM API
                                    dwmapi = ctypes.windll.dwmapi
                                    
                                    # Try to set caption button bounds to zero
                                    rect = ctypes.wintypes.RECT(0, 0, 0, 0)
                                    dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_BUTTON_BOUNDS, 
                                                                ctypes.byref(rect), ctypes.sizeof(rect))
                                    
                                    # Set invisible frame border thickness
                                    thickness = ctypes.c_int(0)
                                    dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_VISIBLE_FRAME_BORDER_THICKNESS, 
                                                                ctypes.byref(thickness), ctypes.sizeof(thickness))
                                    
                                    logger.info("Applied additional title bar hiding via DWM API")
                                except Exception as e:
                                    logger.error(f"Error applying DWM fixes: {e}")
                                
                                return True
                        return True
                    
                    # Enumerate windows to find Firefox
                    win32gui.EnumWindows(callback, None)
                    
                except Exception as e:
                    logger.error(f"Error handling Firefox window: {e}")
            
            # Set a timer to check less frequently (5 seconds)
            self.root.after(5000, self.bring_control_to_front)
            
        except Exception as e:
            logger.error(f"Error bringing control panel to front: {e}")
            # Retry but with delay
            self.root.after(5000, self.bring_control_to_front)
    
    def handle_blank_page_issue(self, hwnd):
        """Handle case where Firefox loads a blank page"""
        try:
            # Check if we already tried to fix this window
            window_id = str(hwnd)
            if hasattr(self, '_fixed_windows') and window_id in self._fixed_windows:
                return
            
            # Initialize the tracking set if it doesn't exist
            if not hasattr(self, '_fixed_windows'):
                self._fixed_windows = set()
            
            # Mark this window as fixed
            self._fixed_windows.add(window_id)
            
            # Get the current URL by stimulating keyboard shortcut (Ctrl+L then Esc)
            # This won't display the URL but might help Firefox focus on the content
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.5)
            
            # Send keys to Firefox window to refresh (F5)
            win32api.keybd_event(0x74, 0, 0, 0)  # F5 down
            time.sleep(0.1)
            win32api.keybd_event(0x74, 0, win32con.KEYEVENTF_KEYUP, 0)  # F5 up
            
            # Wait a moment
            time.sleep(0.5)
            
            # Retry loading homepage by creating a JavaScript file and executing it
            js_file = os.path.join(self.firefox_profile_path, "navigate.js")
            with open(js_file, "w") as f:
                f.write(f'window.location.href = "{self.homepage}";')
            
            # Run Firefox with remote debugging to execute the script
            firefox_path = self.config.get("firefox_path", "C:\\Program Files\\Mozilla Firefox\\firefox.exe")
            subprocess.Popen([
                firefox_path,
                "-remote-debugging-port", "9222",
                "-P", os.path.basename(self.firefox_profile_path),
                "-chrome", f"javascript:window.location.href='{self.homepage}'"
            ], shell=True)
            
            logger.info("Attempted to fix blank page issue")
            
            # Ensure our control panel stays on top
            self.root.after(100, lambda: self.root.attributes('-topmost', True))
        
        except Exception as e:
            logger.error(f"Error fixing blank page: {e}")
    
    def keep_ui_on_top(self):
        """Periodic check to ensure UI stays on top and Firefox window is positioned correctly."""
        try:
            # Ensure control panel is on top
            self.root.attributes('-topmost', True)
            self.root.update()
            
            # Check if Firefox window still exists and is positioned correctly
            if hasattr(self, 'firefox_hwnd') and win32gui.IsWindow(self.firefox_hwnd):
                # Make sure Firefox is still positioned correctly
                control_height = self.root.winfo_height()
                screen_width = self.root.winfo_screenwidth()
                screen_height = self.root.winfo_screenheight()
                
                # Get current window position
                rect = win32gui.GetWindowRect(self.firefox_hwnd)
                if rect[1] != control_height:
                    # Reposition the Firefox window if it's moved
                    win32gui.SetWindowPos(
                        self.firefox_hwnd, 
                        win32con.HWND_NOTOPMOST,
                        0, control_height, 
                        screen_width, screen_height - control_height,
                        win32con.SWP_FRAMECHANGED
                    )
            
            # Check again in 1 second
            self.root.after(1000, self.keep_ui_on_top)
        except Exception as e:
            logger.error(f"Error in keep_ui_on_top: {e}")
    
    def go_back(self):
        """Go back in browser history."""
        logger.info("Go back requested")
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.execute_script("window.history.back();")
                logger.info("Executed history.back() via JavaScript")
                # Make sure our control panel stays on top
                self.root.after(100, lambda: self.root.attributes('-topmost', True))
            except Exception as e:
                logger.error(f"Error going back via JavaScript: {e}")
                try:
                    # Fallback to WebDriver back() method
                    self.driver.back()
                    logger.info("Used WebDriver back() method")
                except Exception as e2:
                    logger.error(f"Error with WebDriver back(): {e2}")
        
    def go_home(self):
        """Go to homepage."""
        logger.info("Go home requested")
        if hasattr(self, 'driver') and self.driver:
            try:
                # Use direct JavaScript navigation for more reliable behavior
                self.driver.execute_script(f"window.location.href = '{self.homepage}';")
                logger.info(f"Navigated to homepage via JavaScript: {self.homepage}")
                # Make sure our control panel stays on top
                self.root.after(100, lambda: self.root.attributes('-topmost', True))
            except Exception as e:
                logger.error(f"Error navigating to homepage via JavaScript: {e}")
                # Fallback to navigate_to method
                self.navigate_to(self.homepage)
    
    def show_exit_dialog(self):
        """Show exit confirmation dialog with password protection."""
        logger.info("Exit dialog requested")
        
        # Create a toplevel window for the exit dialog
        exit_dialog = tk.Toplevel(self.root)
        exit_dialog.title("Exit Kiosk Mode")
        exit_dialog.attributes('-topmost', True)
        
        # Position in center of screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = 300
        height = 150
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        exit_dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Store the hook state for reinstallation
        hook_was_installed = False
        # Ensure this dialog can receive keyboard input
        # Temporarily uninstall keyboard hook
        if hasattr(self, 'keyboard_hook') and self.keyboard_hook.hooked:
            logger.info("Temporarily disabling keyboard hook for password entry")
            hook_was_installed = True
            self.keyboard_hook.uninstall_hook()
        
        # Add password label and entry
        tk.Label(exit_dialog, text="Enter admin password to exit:", font=('Segoe UI', 10)).pack(pady=10)
        password_var = tk.StringVar()
        password_entry = tk.Entry(exit_dialog, textvariable=password_var, show="*", font=('Segoe UI', 10))
        password_entry.pack(pady=5, padx=20, fill=tk.X)
        
        # Store refresh timer IDs to cancel during exit dialog
        self.active_refresh_timers = []
        if hasattr(self, 'security_check_timer'):
            self.active_refresh_timers.append(self.security_check_timer)
        
        # Cancel any pending refresh operations
        for timer_id in self.active_refresh_timers:
            self.root.after_cancel(timer_id)
        
        # Functions for the buttons
        def check():
            entered_password = password_var.get()
            admin_password = self.admin_password
            if entered_password == admin_password:
                logger.info("Admin password accepted, exiting kiosk mode")
                exit_dialog.destroy()
                self.cleanup()
            else:
                logger.warning(f"Invalid password attempt: {entered_password}")
                messagebox.showerror("Error", "Incorrect password", parent=exit_dialog)
        
        def cancel():
            logger.info("Exit dialog cancelled")
            exit_dialog.destroy()
            # Reset the exit dialog flag
            self._exit_dialog_showing = False
            # Reinstall keyboard hook only if it was previously installed
            if hook_was_installed:
                logger.info("Re-enabling keyboard hook")
                # Create a new hook instance instead of reinstalling the old one
                self.keyboard_hook = KeyboardHook()
                self.keyboard_hook.set_exit_callback(self.trigger_exit_dialog)
                self.keyboard_hook.install_hook()
            
            # Restart the security checks
            self.security_check_timer = self.root.after(5000, self.perform_security_checks)
        
        # Add buttons
        button_frame = tk.Frame(exit_dialog)
        button_frame.pack(pady=15)
        tk.Button(button_frame, text="OK", command=check, font=('Segoe UI', 9)).pack(side=tk.LEFT, padx=10)
        tk.Button(button_frame, text="Cancel", command=cancel, font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        # Handle dialog destruction
        exit_dialog.protocol("WM_DELETE_WINDOW", cancel)
        
        # Bind Enter key to check function
        exit_dialog.bind('<Return>', lambda e: check())
        
        # Make exit dialog modal and set focus
        exit_dialog.transient(self.root)
        exit_dialog.grab_set()
        password_entry.focus_force()
        
        # Set a fixed width and prevent resizing
        exit_dialog.resizable(False, False)
        
        # Keep dialog on top and prevent any refresh operations
        def maintain_focus():
            if not exit_dialog.winfo_exists():
                return
            exit_dialog.attributes('-topmost', True)
            exit_dialog.focus_force()
            password_entry.focus_force()
            exit_dialog.after(100, maintain_focus)
        
        # Start the focus maintenance
        maintain_focus()
        
        # Add a physical emergency exit (Alt+F4) on the dialog
        def handle_alt_f4(event):
            logger.info("Alt+F4 emergency exit triggered")
            # Restore taskbar
            if hasattr(self, 'taskbar_hwnd') and self.taskbar_hwnd:
                try:
                    win32gui.ShowWindow(self.taskbar_hwnd, win32con.SW_SHOW)
                except:
                    pass
            # Force exit
            os._exit(0)
        
        # Bind Alt+F4 for emergency exit
        exit_dialog.bind('<Alt-F4>', handle_alt_f4)
    
    def cleanup_browser(self):
        """Close the browser."""
        try:
            if hasattr(self, 'driver') and self.driver:
                logger.info("Closing WebDriver")
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.error(f"Error quitting WebDriver: {e}")
                self.driver = None
            
            # Kill any remaining Firefox processes
            self.kill_all_firefox_processes()
            
            # Try to clean up the profile directory
            if hasattr(self, 'firefox_profile_path') and os.path.exists(self.firefox_profile_path):
                try:
                    import shutil
                    logger.info(f"Cleaning up profile directory: {self.firefox_profile_path}")
                    shutil.rmtree(self.firefox_profile_path, ignore_errors=True)
                except Exception as e:
                    logger.error(f"Error cleaning up profile directory: {e}")
                
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def kill_all_firefox_processes(self):
        """Kill all Firefox processes."""
        try:
            import psutil
            import time
            from subprocess import run
            import os
            
            logger.info("Killing all Firefox processes")
            
            # 1. First try taskkill with /T for tree
            try:
                logger.info("Using taskkill /T to terminate Firefox and all child processes")
                run("taskkill /F /T /IM firefox.exe", shell=True)
                time.sleep(2)  # Give processes time to terminate
            except Exception as e:
                logger.error(f"Taskkill error: {e}")
            
            # 2. Kill parent processes first (more aggressive)
            for proc in psutil.process_iter(['pid', 'name', 'ppid']):
                try:
                    if 'firefox' in proc.info['name'].lower():
                        # Check if this is a parent process
                        is_parent = True
                        for other_proc in psutil.process_iter(['pid', 'ppid']):
                            if other_proc.info.get('ppid') == proc.info['pid']:
                                is_parent = False
                                break
                        
                        if is_parent:
                            logger.info(f"Killing parent Firefox process: {proc.info['pid']}")
                            p = psutil.Process(proc.info['pid'])
                            p.kill()  # More aggressive than terminate
                except Exception as e:
                    logger.error(f"Error killing parent process: {e}")
            
            time.sleep(1)
            
            # 3. Then kill any remaining Firefox processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'firefox' in proc.info['name'].lower():
                        logger.info(f"Killing Firefox process: {proc.info['pid']}")
                        p = psutil.Process(proc.info['pid'])
                        p.kill()  # Using kill instead of terminate
                except Exception as e:
                    logger.error(f"Error killing process: {e}")
            
            time.sleep(1)
            
            # 4. Kill by using Windows Management Instrumentation Command-line
            try:
                logger.info("Using WMIC to terminate Firefox")
                run("wmic process where name='firefox.exe' delete", shell=True)
                time.sleep(1)
            except Exception as e:
                logger.error(f"WMIC error: {e}")
            
            # 5. Clear Firefox lock files
            self.clear_firefox_lock_files()
            
            # 6. Look for and close Firefox dialogs
            self.close_firefox_dialogs()
                
        except Exception as e:
            logger.error(f"Error killing Firefox processes: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def clear_firefox_lock_files(self):
        """Clear Firefox lock files to prevent profile in use errors."""
        try:
            import glob
            import time
            
            logger.info("Removing Firefox lock files")
            
            # Check temp directories
            for temp_dir in [os.environ.get('TEMP'), os.environ.get('TMP')]:
                if temp_dir and os.path.exists(temp_dir):
                    # Find mozilla folders in temp
                    mozilla_dirs = []
                    for root, dirs, files in os.walk(temp_dir):
                        if 'mozilla' in root.lower():
                            mozilla_dirs.append(root)
                    
                    # Look for lock files in these dirs
                    for mozilla_dir in mozilla_dirs:
                        for lock_file in glob.glob(os.path.join(mozilla_dir, "*.lock")):
                            try:
                                logger.info(f"Removing lock file: {lock_file}")
                                os.remove(lock_file)
                            except Exception as e:
                                logger.error(f"Error removing lock file: {e}")
            
            # Check user profile
            appdata = os.environ.get('APPDATA')
            if appdata:
                mozilla_dir = os.path.join(appdata, 'Mozilla')
                if os.path.exists(mozilla_dir):
                    # Find all profiles.ini files
                    for profiles_ini in glob.glob(os.path.join(mozilla_dir, '**/profiles.ini'), recursive=True):
                        try:
                            logger.info(f"Removing profiles.ini: {profiles_ini}")
                            os.rename(profiles_ini, profiles_ini + '.bak')
                        except Exception as e:
                            logger.error(f"Error backing up profiles.ini: {e}")
                    
                    # Find all lock files
                    for lock_file in glob.glob(os.path.join(mozilla_dir, '**/*.lock'), recursive=True):
                        try:
                            logger.info(f"Removing lock file: {lock_file}")
                            os.remove(lock_file)
                        except Exception as e:
                            logger.error(f"Error removing lock file: {e}")
                    
                    # Find all parent.lock files
                    for lock_file in glob.glob(os.path.join(mozilla_dir, '**/parent.lock'), recursive=True):
                        try:
                            logger.info(f"Removing parent.lock: {lock_file}")
                            os.remove(lock_file)
                        except Exception as e:
                            logger.error(f"Error removing parent.lock: {e}")
            
        except Exception as e:
            logger.error(f"Error clearing Firefox lock files: {e}")
            import traceback
            logger.error(traceback.format_exc())

    def close_firefox_dialogs(self):
        """Find and close Firefox dialog windows."""
        try:
            import win32gui
            import win32con
            
            logger.info("Looking for Firefox dialog windows")
            
            def enum_windows_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Firefox" in title and ("Mode" in title or "Safe Mode" in title or "Troubleshoot" in title):
                        logger.info(f"Found Firefox dialog: '{title}'")
                        
                        # First try to click the "Open" button if it exists
                        try:
                            # Find child windows (buttons)
                            def find_button(child_hwnd, _):
                                button_text = win32gui.GetWindowText(child_hwnd)
                                if button_text == "Open":
                                    logger.info(f"Clicking 'Open' button in dialog")
                                    win32gui.SendMessage(child_hwnd, win32con.BM_CLICK, 0, 0)
                                    return False
                                return True
                            
                            win32gui.EnumChildWindows(hwnd, find_button, None)
                        except Exception as e:
                            logger.error(f"Error clicking button: {e}")
                        
                        # If that doesn't work, try to close the dialog
                        try:
                            logger.info(f"Closing Firefox dialog window")
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        except Exception as e:
                            logger.error(f"Error closing dialog: {e}")
                return True
            
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception as e:
            logger.error(f"Error handling Firefox dialogs: {e}")

    def start_browser_with_url(self, url):
        """Start Firefox with a specific URL using Selenium WebDriver."""
        try:
            logger.info(f"Initializing Firefox WebDriver with URL: {url}")
            
            # First ensure all Firefox processes are killed
            self.kill_all_firefox_processes()
            
            # Create a Firefox options object
            options = Options()
            options.add_argument('-kiosk')
            options.add_argument('-private')
            options.add_argument('-no-remote')
            options.set_preference("browser.shell.checkDefaultBrowser", False)
            options.set_preference("browser.sessionstore.resume_from_crash", False)
            options.set_preference("browser.sessionstore.max_resumed_crashes", -1)
            options.set_preference("browser.startup.page", 1)
            options.set_preference("browser.startup.homepage", url)
            options.set_preference("browser.startup.homepage_override.mstone", "ignore")
            options.set_preference("browser.newtabpage.enabled", False)
            options.set_preference("browser.fullscreen.autohide", False)
            options.set_preference("browser.tabs.forceHide", True)
            options.set_preference("browser.tabs.warnOnClose", False)
            options.set_preference("browser.tabs.warnOnCloseOtherTabs", False)
            options.set_preference("browser.toolbars.bookmarks.visibility", "never")
            options.set_preference("dom.disable_window_move_resize", True)
            options.set_preference("dom.disable_window_flip", True)
            options.set_preference("dom.disable_beforeunload", True)
            options.set_preference("toolkit.legacyUserProfileCustomizations.stylesheets", True)
            options.set_preference("browser.startup.couldRestoreSession.count", -1)
            options.set_preference("browser.disableResetPrompt", True)
            options.set_preference("browser.aboutwelcome.enabled", False)
            # Additional preferences to hide UI elements
            options.set_preference("browser.tabs.drawInTitlebar", False)
            options.set_preference("browser.chrome.toolbar_style", 0)
            options.set_preference("browser.chrome.site_icons", False)
            options.set_preference("browser.urlbar.trimURLs", True)
            options.set_preference("browser.urlbar.hideGoButton", True)
            options.set_preference("browser.uidensity", 1)
            options.set_preference("browser.ui.zoom.force100", True)
            
            # Create a unique profile name
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            profile_name = f"kiosk_profile_{timestamp}"
            
            # Create a Firefox profile
            logger.info(f"Creating Firefox profile: {profile_name}")
            firefox_profile_path = os.path.join(os.environ.get('LOCALAPPDATA'), 'Temp', 'KioskProfiles', profile_name)
            os.makedirs(firefox_profile_path, exist_ok=True)
            
            # Create chrome directory and userChrome.css
            chrome_dir = os.path.join(firefox_profile_path, "chrome")
            os.makedirs(chrome_dir, exist_ok=True)
            
            # Create userChrome.css to hide UI elements
            with open(os.path.join(chrome_dir, "userChrome.css"), "w") as f:
                f.write('@namespace url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");\n')
                f.write('@namespace html url("http://www.w3.org/1999/xhtml");\n')
                
                # Completely hide Firefox UI with !important flags
                f.write(':root { --hide-nav-bar: true !important; }\n\n')
                
                # Combined selector with multiple properties for nav bar elements
                f.write('/* Ultimate nav bar hiding */\n')
                f.write('#nav-bar, #PersonalToolbar, #TabsToolbar, #titlebar, #navigator-toolbox,\n')
                f.write('#urlbar-container, #urlbar, #page-action-buttons, #identity-box,\n')
                f.write('.urlbar-input-container, #back-button, #forward-button,\n')
                f.write('#tracking-protection-icon-container, #PanelUI-button, #customizableui-special-spring1,\n')
                f.write('#customizableui-special-spring2, .urlbar-history-dropmarker {\n')
                f.write('  visibility: collapse !important;\n')
                f.write('  display: none !important;\n')
                f.write('  -moz-appearance: none !important;\n')
                f.write('  height: 0 !important;\n')
                f.write('  min-height: 0 !important;\n')
                f.write('  max-height: 0 !important;\n')
                f.write('  width: 0 !important;\n')
                f.write('  min-width: 0 !important;\n')
                f.write('  max-width: 0 !important;\n')
                f.write('  overflow: hidden !important;\n')
                f.write('  position: fixed !important;\n')
                f.write('  opacity: 0 !important;\n')
                f.write('  z-index: -999 !important;\n')
                f.write('  pointer-events: none !important;\n')
                f.write('  margin-top: -500px !important;\n')
                f.write('  transform: translateY(-500px) !important;\n')
                f.write('  clip: rect(0px, 0px, 0px, 0px) !important;\n')
                f.write('}\n\n')
                
                # Firefox 115+ specific hiding
                f.write('/* Firefox 115+ specific hiding */\n')
                f.write(':root[titlebarempty="true"] #navigator-toolbox,\n')
                f.write(':root[titlepreface="true"] #navigator-toolbox,\n')
                f.write(':root[titlemodifier="true"] #navigator-toolbox {\n')
                f.write('  visibility: collapse !important;\n')
                f.write('  height: 0 !important;\n')
                f.write('  overflow-y: hidden !important;\n')
                f.write('  position: fixed !important;\n')
                f.write('  z-index: -999 !important;\n')
                f.write('}\n\n')
                
                # Add forced full height for content area
                f.write('/* Ensure content takes full height */\n')
                f.write('browser, browser *, #browser, #content-deck, #content, .browserStack, browser {\n')
                f.write('  margin-top: 0 !important;\n')
                f.write('  padding-top: 0 !important;\n')
                f.write('  max-height: 100vh !important;\n')
                f.write('  height: 100vh !important;\n')
                f.write('  border-top: 0 !important;\n')
                f.write('}\n\n')
                
                # Add specific CSS to handle unique window configurations
                f.write('/* Additional overrides for any UI that might appear */\n')
                f.write('@-moz-document url(chrome://browser/content/browser.xhtml) {\n')
                f.write('  #main-window[chromehidden*="toolbar"] #navigator-toolbox { display: none !important; }\n')
                f.write('  #toolbar-menubar { height: 0 !important; visibility: collapse !important; }\n')
                f.write('  #browser-panel { margin-top: 0 !important; }\n')
                f.write('}\n')
            
            # Create userContent.css
            with open(os.path.join(chrome_dir, "userContent.css"), "w") as f:
                f.write('@-moz-document url("about:blank"), url-prefix("about:"), url-prefix("chrome:"), url-prefix("resource:") {\n')
                f.write('  body, html { background-color: white !important; }\n')
                f.write('  * { overflow: hidden !important; }\n')
                f.write('}\n')
                
                # Add rule to ensure links open in same window
                f.write('@-moz-document url-prefix("") {\n')
                f.write('  a[target="_blank"] { target: "_self" !important; }\n')
                f.write('}\n')
            
            # Create user.js with direct preference overrides
            with open(os.path.join(firefox_profile_path, "user.js"), "w") as f:
                f.write('user_pref("browser.tabs.firefox-view", false);\n')
                f.write('user_pref("browser.tabs.drawInTitlebar", false);\n')
                f.write('user_pref("browser.display.focus_ring_on_anything", false);\n')
                f.write('user_pref("browser.display.focus_ring_width", 0);\n')
                f.write('user_pref("browser.display.show_chrome_on_hover", false);\n')
                f.write('user_pref("browser.chromeURL", "");\n')
                
                # Aggressive fullscreen control
                f.write('user_pref("browser.fullscreen.autohide", false);\n')
                f.write('user_pref("browser.fullscreen.hideChromeUI", true);\n')
                f.write('user_pref("browser.fullscreen.lockChromeUI", true);\n')
                
                # Custom XUL settings
                f.write('user_pref("dom.xul.disable", false);\n')
                f.write('user_pref("xpinstall.signatures.required", false);\n')
                
                # Navbar specific settings  
                f.write('user_pref("browser.touchbar.enabled", false);\n')
                f.write('user_pref("browser.tabs.inTitlebar", 0);\n')
                f.write('user_pref("browser.showMenuButton", false);\n')
                
                # Toolbar hiding
                f.write('user_pref("browser.toolbars.legacy.enabled", false);\n')
                f.write('user_pref("browser.toolbars.navbar.enabled", false);\n')
                f.write('user_pref("browser.default.toolbars.navbar.enabled", false);\n')
            
            # Set up Firefox binary path
            firefox_path = self.config.get("firefox_path", "C:\\Program Files\\Mozilla Firefox\\firefox.exe")
            options.binary_location = firefox_path
            
            # Create a service for Firefox driver
            service = Service()
            
            # Create WebDriver with options
            logger.info("Creating WebDriver instance")
            self.driver = webdriver.Firefox(
                service=service,
                options=options
            )
            
            # Store the profile directory for cleanup
            self.firefox_profile_path = firefox_profile_path
            
            # Navigate to homepage
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Set a timer to make our control panel come to the front
            self.root.after(3000, self.bring_control_to_front)
            
            # Try to hide address bar with JavaScript after page loads
            self.root.after(5000, self.apply_javascript_fixes)
            
            logger.info("Firefox WebDriver started successfully with URL")
            
        except Exception as e:
            logger.error(f"WebDriver start error with URL: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.show_error(f"Failed to start browser with URL: {e}")
    
    def perform_security_checks(self):
        """Periodically check system security and window states."""
        try:
            # Make sure no Firefox UI elements have appeared
            if hasattr(self, 'firefox_hwnd') and win32gui.IsWindow(self.firefox_hwnd):
                # Check window styles to ensure kiosk mode is maintained
                style = win32gui.GetWindowLong(self.firefox_hwnd, win32con.GWL_STYLE)
                if style & (win32con.WS_THICKFRAME | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX):
                    # Window has gained resizing capabilities, fix it
                    logger.warning("Firefox window style changed, resetting...")
                    new_style = style & ~(win32con.WS_THICKFRAME | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX)
                    win32gui.SetWindowLong(self.firefox_hwnd, win32con.GWL_STYLE, new_style)
                    
                    # Also remove caption (title bar)
                    ex_style = win32gui.GetWindowLong(self.firefox_hwnd, win32con.GWL_EXSTYLE)
                    new_ex_style = ex_style & ~(win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_CLIENTEDGE | win32con.WS_EX_STATICEDGE)
                    win32gui.SetWindowLong(self.firefox_hwnd, win32con.GWL_EXSTYLE, new_ex_style)
                    
                    # Reapply window position and size
                    control_height = self.root.winfo_height()
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    win32gui.SetWindowPos(
                        self.firefox_hwnd, 
                        win32con.HWND_NOTOPMOST,
                        0, control_height, 
                        screen_width, screen_height - control_height,
                        win32con.SWP_FRAMECHANGED
                    )
            
            # Check for any Firefox dialog windows that need to be handled
            self.close_firefox_dialogs()
            
            # Limit security checks to run less frequently to avoid interrupting exit dialogs
            self.security_check_timer = self.root.after(5000, self.perform_security_checks)
        except Exception as e:
            logger.error(f"Error in security checks: {e}")
            # Continue checking even if there was an error
            self.security_check_timer = self.root.after(5000, self.perform_security_checks)
    
    def handle_multiple_firefox_windows(self):
        """Find and close extra Firefox windows, keeping only one."""
        try:
            import win32gui
            import win32con
            
            # Store all Firefox windows
            firefox_windows = []
            
            def enum_windows_callback(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Mozilla Firefox" in title or "Firefox" in title:
                        # Skip dialog windows
                        if "Mode" not in title and "Safe Mode" not in title and "Troubleshoot" not in title:
                            firefox_windows.append((hwnd, title))
                return True
            
            win32gui.EnumWindows(enum_windows_callback, None)
            
            # If we have more than one Firefox window
            if len(firefox_windows) > 1:
                logger.warning(f"Found {len(firefox_windows)} Firefox windows - closing extras")
                
                # Keep the first one (our main window), close others
                main_window = firefox_windows[0][0]
                
                for hwnd, title in firefox_windows[1:]:
                    try:
                        logger.info(f"Closing extra Firefox window: '{title}'")
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    except Exception as e:
                        logger.error(f"Error closing window: {e}")
                        
                # Make sure our main window is properly set
                self.firefox_hwnd = main_window
        
        except Exception as e:
            logger.error(f"Error handling multiple Firefox windows: {e}")
    
    def cleanup(self):
        """Clean up all resources and exit."""
        try:
            logger.info("Performing final cleanup...")
            
            # Unregister global hotkey
            try:
                hwnd = int(self.root.winfo_id())
                ctypes.windll.user32.UnregisterHotKey(hwnd, 1)
                logger.info("Unregistered global hotkey")
            except Exception as e:
                logger.error(f"Error unregistering hotkey: {e}")
            
            # Unbind all keyboard shortcuts
            try:
                self.root.unbind_all('<Alt-KeyPress-x>')
                self.root.unbind_all('<Alt-KeyPress-X>')
                self.root.unbind_all('<Alt-x>')
            except Exception as e:
                logger.error(f"Error unbinding shortcuts: {e}")
            
            # Uninstall keyboard hook
            if hasattr(self, 'keyboard_hook'):
                self.keyboard_hook.uninstall_hook()
            
            # Clean up browser
            self.cleanup_browser()
            
            # Restore taskbar if we have a reference to it
            if hasattr(self, 'taskbar_hwnd') and self.taskbar_hwnd:
                try:
                    win32gui.ShowWindow(self.taskbar_hwnd, win32con.SW_SHOW)
                    logger.info("Taskbar restored")
                except Exception as e:
                    logger.error(f"Error restoring taskbar: {e}")
            
            # Log the exit and destroy the root window
            logger.info("Exiting kiosk application")
            self.root.destroy()
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Error in final cleanup: {e}")
            # Force exit in case of errors
            sys.exit(1)
    
    def show_error(self, message):
        """Show error message."""
        tk.messagebox.showerror("Error", message)

def is_admin():
    """Check for admin rights."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    # Request admin rights if needed
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return
    
    app = KioskApp()
    app.root.mainloop()

if __name__ == "__main__":
    main() 