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
import ctypes.wintypes
from ctypes import CFUNCTYPE, POINTER, c_int, c_void_p, byref, Structure, c_long, WINFUNCTYPE

# Windows API constants for key blocking
WH_KEYBOARD_LL = 13
WH_MSGFILTER = -1  # System-wide message filter for Alt+Tab blocking
MSGF_DIALOGBOX = 0
MSGF_MENU = 2 
MSGF_NEXTWINDOW = 1  # Alt+Tab window switching
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
VK_X = 0x58  # Virtual key code for 'X'
VK_TAB = 0x09  # Virtual key code for 'Tab'
VK_MENU = 0x12  # Virtual key code for 'Alt'
VK_D = 0x44    # Virtual key code for 'D'

# List of virtual key codes to block
BLOCKED_KEYS = [
    0x09,  # TAB (Alt+Tab, Ctrl+Tab)
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
    0x52,  # R key (Win+R)
    0x45,  # E key (Win+E)
    0x44,  # D key (Win+D, Alt+D)
    0x4C,  # L key (Win+L)
    0x41,  # A key (Ctrl+A)
    0x53,  # S key (Ctrl+S)
    0x20,  # SPACE (Win+Space)
    0x24,  # HOME (Win+Home)
    0x50,  # P key (Win+P)
    0x49,  # I key (Win+I for settings)
    0x51,  # Q key (Alt+F4 alternative)
    0x26,  # UP ARROW
    0x28,  # DOWN ARROW
    0x25,  # LEFT ARROW
    0x27,  # RIGHT ARROW
]

# Keys to allow only with Alt pressed (for Alt+X to work)
ALLOW_WITH_ALT = [VK_X]  # ONLY allow Alt+X

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

class KeyboardBlocker:
    """Ultra-aggressive keyboard blocker for kiosk mode."""
    
    def __init__(self):
        """Initialize the keyboard blocker with aggressive blocking strategies."""
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.is_blocking = False
        
        # Store the hooks
        self.hook_ids = []
        self.threads = []
        
        # For tracking key states
        self.alt_pressed = False
        self.emergency_exit_keys = {}  # Track emergency exit key sequence
        
        # Logging
        self.logger = logging.getLogger('firefox_kiosk.KeyBlocker')
    
    def start_blocking(self):
        """Start ultra-aggressive keyboard blocking."""
        if self.is_blocking:
            return
            
        self.logger.info("Starting ULTRA-AGGRESSIVE keyboard blocker")
        
        # Try all methods to ensure comprehensive blocking
        self.install_system_hook()
        self.block_win_key()
        self.lock_workstation()
        self.start_alt_release_thread()
        
        # NUCLEAR OPTION: Direct Alt+Tab blocker at the lowest possible level
        self.start_nuclear_alt_tab_blocker()
        
        # Mark as started
        self.is_blocking = True
    
    def start_nuclear_alt_tab_blocker(self):
        """Implement a nuclear Alt+Tab blocker using direct Windows API techniques."""
        try:
            import threading
            
            def nuclear_alt_tab_blocker():
                """This function monitors and blocks Alt+Tab at the system level."""
                # Constants for Shell_TrayWnd handling
                SPI_SETFOREGROUNDLOCKTIMEOUT = 0x2000
                SPIF_SENDCHANGE = 0x2
                
                # Attempt to prevent Alt+Tab task switcher from appearing
                try:
                    # Disable Alt+Tab at system level by setting foreground lock timeout to max
                    ctypes.windll.user32.SystemParametersInfoW(
                        SPI_SETFOREGROUNDLOCKTIMEOUT, 0, 0, SPIF_SENDCHANGE
                    )
                    self.logger.info("Set foreground lock timeout to disable Alt+Tab")
                except Exception as e:
                    self.logger.error(f"Error setting foreground lock timeout: {e}")
                
                # Try to find and disable task switcher window
                def kill_task_switcher():
                    try:
                        # Look for the Alt+Tab window
                        task_switcher_hwnd = None
                        
                        # These are known class names for task switcher windows
                        task_switcher_classes = [
                            "MultitaskingViewFrame",  # Windows 10/11 task switcher
                            "XamlExplorerHostIslandWindow",  # Another potential class
                            "ForegroundStaging",  # Windows 11 switcher
                            "TaskSwitcherWnd",  # Older Windows
                            "TaskSwitchWindow"  # Older Windows
                        ]
                        
                        def find_task_switcher(hwnd, _):
                            try:
                                nonlocal task_switcher_hwnd
                                if not task_switcher_hwnd and win32gui.IsWindowVisible(hwnd):
                                    try:
                                        class_name = win32gui.GetClassName(hwnd)
                                        for switcher_class in task_switcher_classes:
                                            if switcher_class in class_name:
                                                task_switcher_hwnd = hwnd
                                                return False
                                    except:
                                        pass
                                return True
                            except:
                                return True
                        
                        try:
                            win32gui.EnumWindows(find_task_switcher, None)
                        except:
                            pass
                        
                        # If found, try to close it
                        if task_switcher_hwnd:
                            self.logger.info(f"Found task switcher window: {task_switcher_hwnd}")
                            try:
                                # Try multiple methods to kill the window
                                win32gui.SendMessage(task_switcher_hwnd, win32con.WM_CLOSE, 0, 0)
                                win32gui.PostMessage(task_switcher_hwnd, win32con.WM_CLOSE, 0, 0)
                                ctypes.windll.user32.EndTask(task_switcher_hwnd, False, True)
                            except:
                                pass
                    except Exception as e:
                        self.logger.debug(f"Error in kill_task_switcher: {e}")
                
                # Main loop to continuously monitor and block Alt+Tab
                while self.is_blocking:
                    try:
                        # Monitor for Alt+Tab combo
                        alt_down = ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000 != 0
                        tab_down = ctypes.windll.user32.GetAsyncKeyState(0x09) & 0x8000 != 0
                        
                        # If Alt and Tab are both down, it's an Alt+Tab attempt
                        if alt_down and tab_down:
                            self.logger.info("NUCLEAR: Detected Alt+Tab attempt")
                            
                            # Force release of Alt and Tab keys
                            try:
                                # Release Alt
                                win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
                                ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
                                
                                # Release Tab
                                win32api.keybd_event(0x09, 0, win32con.KEYEVENTF_KEYUP, 0)
                                ctypes.windll.user32.keybd_event(0x09, 0, 2, 0)
                            except:
                                pass
                            
                            # Try to kill any task switcher window
                            kill_task_switcher()
                            
                            # Force focus to a Firefox window if found
                            try:
                                hwnd = win32gui.FindWindow("MozillaWindowClass", None)
                                if not hwnd:
                                    hwnd = win32gui.FindWindow(None, "Mozilla Firefox")
                                
                                if hwnd:
                                    self.logger.info(f"Forcing focus to Firefox window: {hwnd}")
                                    win32gui.SetForegroundWindow(hwnd)
                                    ctypes.windll.user32.BringWindowToTop(hwnd)
                            except:
                                pass
                        
                        # If just Alt is down, monitor for potential Alt+Tab
                        elif alt_down:
                            # Try to preemptively release Alt to prevent Alt+Tab
                            try:
                                win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
                            except:
                                pass
                    except Exception as e:
                        self.logger.debug(f"Error in nuclear Alt+Tab blocker: {e}")
                    
                    # Run at high frequency for better response
                    time.sleep(0.01)  # 10ms for faster response
            
            # Start the nuclear Alt+Tab blocker in a background thread
            self.nuclear_thread = threading.Thread(target=nuclear_alt_tab_blocker, daemon=True)
            self.nuclear_thread.start()
            self.logger.info("Started NUCLEAR Alt+Tab blocker")
            
        except Exception as e:
            self.logger.error(f"Error starting nuclear Alt+Tab blocker: {e}")
    
    def install_system_hook(self):
        """Install a comprehensive low-level keyboard hook that blocks everything."""
        try:
            # Constant definitions for hook
            WH_KEYBOARD_LL = 13
            HC_ACTION = 0
            WM_KEYDOWN = 0x0100
            WM_KEYUP = 0x0101
            WM_SYSKEYDOWN = 0x0104
            WM_SYSKEYUP = 0x0105
            
            # Create a comprehensive list of keys to always block
            BLOCKED_KEYS = {
                0x09: "Tab",           # Tab
                0x1B: "Escape",        # Escape
                0x5B: "Windows Left",  # Left Windows key
                0x5C: "Windows Right", # Right Windows key
                0x73: "F4",            # F4 (for Alt+F4)
                0x70: "F1",            # F1
                0x71: "F2",            # F2
                0x72: "F3",            # F3
                0x74: "F5",            # F5
                0x75: "F6",            # F6
                0x76: "F7",            # F7
                0x77: "F8",            # F8
                0x78: "F9",            # F9
                0x79: "F10",           # F10
                0x7A: "F11",           # F11
                0x7B: "F12",           # F12
            }
            
            # Define low-level keyboard hook callback function
            self.LowLevelKeyboardProc = ctypes.CFUNCTYPE(
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
            )
            
            def keyboard_hook_proc(n_code, w_param, l_param):
                if n_code >= 0:
                    # Get virtual key code
                    vk_code = ctypes.cast(l_param, ctypes.POINTER(ctypes.c_int))[0]
                    
                    # Track Alt key state
                    if vk_code == 0x12:  # Alt key
                        if w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN:
                            self.alt_pressed = True
                            # Force Alt key to appear released
                            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
                            self.logger.info("Detected Alt press - forcing release")
                            return 1
                        elif w_param == WM_KEYUP or w_param == WM_SYSKEYUP:
                            self.alt_pressed = False
                    
                    # CRITICAL: Handle Alt+Tab and other Alt-sequences specially
                    if w_param == WM_SYSKEYDOWN:  # This specifically captures Alt+key combinations
                        self.logger.info(f"Blocked system key combination: {vk_code}")
                        return 1  # Block ALL system key combinations (Alt+anything)
                    
                    # Allow Alt+X (exit key)
                    if self.alt_pressed and vk_code == 0x58:  # X key
                        self.logger.info("Allowing Alt+X for exit")
                        return self.user32.CallNextHookEx(0, n_code, w_param, l_param)
                    
                    # Block Alt+Tab specifically
                    if self.alt_pressed and vk_code == 0x09:  # Tab key
                        self.logger.info("Blocked Alt+Tab via keyboard hook")
                        return 1
                    
                    # Block any Alt combination
                    if self.alt_pressed:
                        self.logger.info(f"Blocked Alt key combination with key code: {vk_code}")
                        return 1
                    
                    # Block system keys
                    if vk_code in BLOCKED_KEYS:
                        self.logger.info(f"Blocked system key: {BLOCKED_KEYS[vk_code]}")
                        return 1
                
                # Pass all other keys
                return self.user32.CallNextHookEx(0, n_code, w_param, l_param)
            
            # Create the callback function and save a reference
            self.keyboard_callback = self.LowLevelKeyboardProc(keyboard_hook_proc)
            
            # Install the hook
            hook_id = self.user32.SetWindowsHookExA(
                WH_KEYBOARD_LL,  # Low-level keyboard hook
                self.keyboard_callback,
                self.kernel32.GetModuleHandleW(None),
                0  # Global hook
            )
            
            if hook_id:
                self.hook_ids.append(hook_id)
                self.logger.info("Installed ULTRA-AGGRESSIVE keyboard hook")
            else:
                self.logger.error("Failed to install keyboard hook")
            
            # SUPER-CRITICAL ALT+TAB KILLER: Add a special system-wide Alt+Tab interceptor
            # Create a callback specifically for Alt+Tab
            self.AltTabInterceptorProc = ctypes.CFUNCTYPE(
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
            )
            
            def alt_tab_interceptor(n_code, w_param, l_param):
                """Specifically designed to block Alt+Tab and only Alt+Tab."""
                if n_code >= 0:
                    # Get the key code
                    vk_code = ctypes.cast(l_param, ctypes.POINTER(ctypes.c_int))[0]
                    
                    # Check for Alt key state using GetAsyncKeyState
                    alt_down = ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000 != 0
                    
                    # If this is a system key event or Tab with Alt down
                    if w_param == WM_SYSKEYDOWN or (alt_down and vk_code == 0x09):
                        # If it's Tab key and Alt is down, it's Alt+Tab
                        if vk_code == 0x09:  # Tab key
                            self.logger.info("CRITICAL: Blocked Alt+Tab via special interceptor")
                            # Force Alt key to appear released to prevent Alt+Tab from working
                            try:
                                ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
                                win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
                            except:
                                pass
                            return 1  # Block the key
                
                # Allow all other keys
                return self.user32.CallNextHookEx(0, n_code, w_param, l_param)
            
            # Create the callback and save a reference
            self.alt_tab_callback = self.AltTabInterceptorProc(alt_tab_interceptor)
            
            # Install a second hook specifically for Alt+Tab
            alt_tab_hook_id = self.user32.SetWindowsHookExA(
                WH_KEYBOARD_LL,  # Low-level keyboard hook
                self.alt_tab_callback,
                self.kernel32.GetModuleHandleW(None),
                0  # Global hook
            )
            
            if alt_tab_hook_id:
                self.hook_ids.append(alt_tab_hook_id)
                self.logger.info("Installed CRITICAL Alt+Tab interceptor hook")
            else:
                self.logger.error("Failed to install Alt+Tab interceptor hook")
                
            # Start a message processing thread to ensure hook works
            self.start_message_thread()
            
            # Register Alt+Tab specifically using RegisterHotKey for maximum coverage
            try:
                # Try to register Alt+Tab as a hotkey
                result = self.user32.RegisterHotKey(
                    None,  # No window handle (global)
                    100,   # ID
                    0x0001,  # MOD_ALT
                    0x09   # VK_TAB
                )
                if result:
                    self.logger.info("Registered Alt+Tab as global hotkey for blocking")
            except Exception as e:
                self.logger.error(f"Error registering Alt+Tab hotkey: {e}")
            
        except Exception as e:
            self.logger.error(f"Error setting up keyboard hook: {e}")
    
    def start_message_thread(self):
        """Start a thread to process messages for the hook."""
        try:
            import threading
            
            def msg_loop():
                msg = wintypes.MSG()
                while self.is_blocking:
                    # Process any waiting messages (required for hooks to work)
                    if self.user32.PeekMessageW(byref(msg), None, 0, 0, 1):  # PM_REMOVE = 1
                        self.user32.TranslateMessage(byref(msg))
                        self.user32.DispatchMessageW(byref(msg))
                    time.sleep(0.01)  # Prevent high CPU usage
            
            thread = threading.Thread(target=msg_loop, daemon=True)
            thread.start()
            self.threads.append(thread)
            self.logger.info("Started message processing thread")
        except Exception as e:
            self.logger.error(f"Error starting message thread: {e}")
    
    def start_alt_release_thread(self):
        """Start a thread that continuously ensures Alt key is released."""
        try:
            import threading
            
            def release_alt_key():
                while self.is_blocking:
                    try:
                        # Check if Alt key is down
                        if ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000:
                            # Force Alt key to appear released
                            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)  # KEYEVENTF_KEYUP = 2
                            self.logger.info("Force-released Alt key")
                    except:
                        pass
                    time.sleep(0.05)  # Check frequently (50ms)
            
            thread = threading.Thread(target=release_alt_key, daemon=True)
            thread.start()
            self.threads.append(thread)
            self.logger.info("Started Alt key release thread")
        except Exception as e:
            self.logger.error(f"Error starting Alt release thread: {e}")
    
    def block_win_key(self):
        """Block Windows keys using various methods."""
        try:
            # Try to disable Windows key via registry
            import winreg
            
            # Disable Windows key
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                                  r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer")
            winreg.SetValueEx(key, "NoWinKeys", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            
            # Try keyboard layout method
            layout_id = self.user32.GetKeyboardLayout(0)
            # Block the Windows key by setting a null handler
            result = self.user32.RegisterHotKey(None, 200, 0x4000, 0x5B)  # Win key
            
            self.logger.info("Applied Windows key blocking methods")
        except Exception as e:
            self.logger.error(f"Error blocking Win key: {e}")
    
    def lock_workstation(self):
        """Lock workstation to current app."""
        try:
            # Attempt to lock window switching
            self.user32.LockSetForegroundWindow(2)  # LSFW_LOCK = 2
            
            # Force our window to stay on top and be always active
            hwnd = self.user32.GetForegroundWindow()
            if hwnd:
                # Set window to be always on top
                style = self.user32.GetWindowLongA(hwnd, -20)  # GWL_EXSTYLE
                self.user32.SetWindowLongA(hwnd, -20, style | 0x00000008)  # WS_EX_TOPMOST
                
                # Prevent window from losing focus
                self.user32.EnableWindow(hwnd, 1)
                
                self.logger.info("Applied foreground window locking")
        except Exception as e:
            self.logger.error(f"Error locking workstation: {e}")
    
    def stop_blocking(self):
        """Stop all keyboard blocking."""
        if not self.is_blocking:
            return
        
        self.logger.info("Stopping keyboard blocker")
        self.is_blocking = False
        
        # Unhook all hooks
        for hook_id in self.hook_ids:
            try:
                self.user32.UnhookWindowsHookEx(hook_id)
            except Exception as e:
                self.logger.error(f"Error unhooking: {e}")
        
        # Unregister Windows key block
        try:
            self.user32.UnregisterHotKey(None, 200)
        except:
            pass
        
        # Unlock foreground window
        try:
            self.user32.LockSetForegroundWindow(0)  # LSFW_UNLOCK
        except:
            pass
        
        # Restore registry settings
        try:
            import winreg
            
            # Restore Windows keys
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", 
                                0, winreg.KEY_SET_VALUE)
            try:
                winreg.DeleteValue(key, "NoWinKeys")
            except:
                pass
            winreg.CloseKey(key)
        except:
            pass
        
        # Clear references
        self.hook_ids = []
    
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
        
        # Track key states for combo detection
        self.alt_pressed = False
        self.ctrl_pressed = False
        self.win_pressed = False
        self.tab_pressed = False
        self.d_pressed = False
        
        # Add a message-only window to process hotkey messages
        class WNDCLASS(ctypes.Structure):
            _fields_ = [
                ("style", ctypes.c_uint),
                ("lpfnWndProc", ctypes.c_void_p),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", ctypes.c_void_p),
                ("hIcon", ctypes.c_void_p),
                ("hCursor", ctypes.c_void_p),
                ("hbrBackground", ctypes.c_void_p),
                ("lpszMenuName", ctypes.c_void_p),
                ("lpszClassName", ctypes.c_wchar_p)
            ]
        
        # Define window procedure callback
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == win32con.WM_HOTKEY:
                hotkey_id = wparam
                if hotkey_id == 100:  # Alt+Tab
                    logger.info("Alt+Tab blocked by hotkey handler")
                    return 1
                elif hotkey_id == 101:  # Alt+D
                    logger.info("Alt+D blocked by hotkey handler")
                    return 1
            return self.user32.DefWindowProcW(hwnd, msg, wparam, lparam)
        
        # Create message-only window for hotkey processing
        try:
            # Define window procedure type
            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, 
                                         ctypes.c_uint, ctypes.c_void_p)
            self.wnd_proc_callback = WNDPROC(wnd_proc)
            
            # Register window class
            wnd_class = WNDCLASS()
            wnd_class.lpfnWndProc = self.wnd_proc_callback
            wnd_class.lpszClassName = "KioskHotkeyHandler"
            
            # Register the class
            if not self.user32.RegisterClassW(ctypes.byref(wnd_class)):
                logger.error("Failed to register window class")
            
            # Create the message-only window
            self.msg_hwnd = self.user32.CreateWindowExW(
                0, "KioskHotkeyHandler", "Kiosk Message Handler",
                0, 0, 0, 0, 0, 
                self.user32.HWND_MESSAGE, 0, 0, 0
            )
            
            if self.msg_hwnd:
                logger.info("Created message-only window for hotkey handling")
                
                # Start a thread to process messages
                import threading
                def msg_loop():
                    msg = ctypes.wintypes.MSG()
                    while self.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
                        self.user32.TranslateMessage(ctypes.byref(msg))
                        self.user32.DispatchMessageW(ctypes.byref(msg))
                
                self.msg_thread = threading.Thread(target=msg_loop, daemon=True)
                self.msg_thread.start()
                logger.info("Message processing thread started")
        except Exception as e:
            logger.error(f"Error setting up message window: {e}")
    
    def set_exit_callback(self, callback):
        """Set callback for exit key combination."""
        self.exit_callback = callback
    
    def keyboard_hook_proc(self, n_code, w_param, l_param):
        """Ultra-aggressive keyboard hook using key state tracking for better combo detection."""
        if n_code >= 0:
            # Get the virtual key code
            vk_code = ctypes.cast(l_param, ctypes.POINTER(ctypes.c_int))[0]
            
            # Track key states for combos
            if vk_code == 0x12:  # ALT key
                self.alt_pressed = (w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN)
            elif vk_code == 0x11:  # CTRL key
                self.ctrl_pressed = (w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN)
            elif vk_code in [0x5B, 0x5C]:  # Windows keys
                self.win_pressed = (w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN)
            elif vk_code == 0x09:  # TAB key
                self.tab_pressed = (w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN)
            elif vk_code == 0x44:  # D key
                self.d_pressed = (w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN)
            
            # ULTRA CRITICAL: Block Alt+Tab specifically
            if self.alt_pressed and vk_code == 0x09:  # Tab with Alt
                return 1
                
            # ULTRA CRITICAL: Block Alt+D specifically
            if self.alt_pressed and vk_code == 0x44:  # D with Alt
                return 1
            
            # Only allow Alt+X for exit
            if self.alt_pressed and vk_code == VK_X and w_param == WM_KEYDOWN:
                if self.exit_callback:
                    self.exit_callback()
                    return 1
            
            # BLOCK ABSOLUTELY EVERYTHING ELSE
            if vk_code != VK_X:  # Allow X for Alt+X combo
                return 1
        
        # Call the next hook for non-keyboard events
        return self.user32.CallNextHookEx(0, n_code, w_param, l_param)
    
    def install_hook(self):
        """Install the keyboard hook with multiple methods for reliability."""
        if not self.hooked:
            # Try with regular hook first
            self.hook_id = self.user32.SetWindowsHookExA(
                WH_KEYBOARD_LL,
                self.keyboard_callback,
                ctypes.windll.kernel32.GetModuleHandleW(None),
                0
            )
            
            # Install special message filter hook to block Alt+Tab specifically
            # This intercepts the window switching mechanism at a very low level
            self.MsgProc = ctypes.CFUNCTYPE(
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)
            )
            
            def msg_filter_proc(code, wparam, lparam):
                """Special message filter to block Alt+Tab."""
                # Code MSGF_NEXTWINDOW indicates Alt+Tab window switching
                if code == MSGF_NEXTWINDOW:
                    # Block the Alt+Tab operation
                    logger.info("Blocked Alt+Tab via message filter")
                    return 1
                return self.user32.CallNextHookEx(0, code, wparam, lparam)
            
            self.msg_proc_callback = self.MsgProc(msg_filter_proc)
            
            # Install the system-wide message filter
            self.msg_hook_id = self.user32.SetWindowsHookExA(
                WH_MSGFILTER,
                self.msg_proc_callback,
                ctypes.windll.kernel32.GetModuleHandleW(None),
                0
            )
            
            if self.msg_hook_id != 0:
                logger.info("Installed message filter hook for Alt+Tab")
            
            if self.hook_id != 0:
                self.hooked = True
                logger.info("Primary keyboard hook installed successfully")
                
                # CRITICAL: Register raw input devices for ALT and TAB keys specifically
                try:
                    # Define raw input device
                    class RAWINPUTDEVICE(ctypes.Structure):
                        _fields_ = [
                            ("usUsagePage", ctypes.c_ushort),
                            ("usUsage", ctypes.c_ushort),
                            ("dwFlags", ctypes.c_ulong),
                            ("hwndTarget", ctypes.c_void_p)
                        ]
                    
                    # Register for keyboard raw input
                    rid = RAWINPUTDEVICE(
                        0x01,      # UsagePage (Generic Desktop)
                        0x06,      # Usage (Keyboard)
                        0x00,      # Flags
                        None       # Target window
                    )
                    
                    # Register raw input device
                    if ctypes.windll.user32.RegisterRawInputDevices(
                            ctypes.byref(rid),
                            1,
                            ctypes.sizeof(RAWINPUTDEVICE)
                    ):
                        logger.info("Raw input device registered for keyboard")
                except Exception as e:
                    logger.error(f"Error registering raw input: {e}")
                
                # Register for Alt+Tab using another method
                try:
                    # Try to disable Alt+Tab system-wide using registry
                    import winreg
                    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                                        r"Control Panel\Desktop")
                    winreg.SetValueEx(key, "CoolSwitchRows", 0, winreg.REG_SZ, "0")
                    winreg.SetValueEx(key, "CoolSwitchColumns", 0, winreg.REG_SZ, "0")
                    winreg.CloseKey(key)
                    logger.info("Disabled Alt+Tab via registry")
                    
                    # Also try direct API approach for Alt+Tab
                    self.user32.DisableProcessWindowsGhosting()
                    logger.info("Disabled window ghosting for Alt+Tab")
                except Exception as e:
                    logger.error(f"Error modifying registry for Alt+Tab: {e}")
                
                # Set global system-wide hotkey
                try:
                    # Register ALT+TAB as a hotkey to intercept it
                    result = self.user32.RegisterHotKey(
                        None,
                        100,  # ID for Alt+Tab
                        MOD_ALT,
                        VK_TAB  # TAB key
                    )
                    
                    # Register ALT+D as a hotkey to intercept it
                    result2 = self.user32.RegisterHotKey(
                        None,
                        101,  # ID for Alt+D
                        MOD_ALT,
                        VK_D  # D key
                    )
                    
                    if result and result2:
                        logger.info("Registered global hotkeys for Alt+Tab and Alt+D")
                except Exception as e:
                    logger.error(f"Error registering global hotkeys: {e}")
                
                # NUCLEAR: Try to completely disable Alt+Tab by using a more aggressive method
                try:
                    # Attempt to create a foreground lock
                    self.user32.LockSetForegroundWindow(2)  # LSFW_LOCK
                    logger.info("Locked foreground window")
                except Exception as e:
                    logger.error(f"Error locking foreground window: {e}")
                
                return True
            else:
                logger.error("Failed to install keyboard hook")
                return False
        return True
    
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
            
            # Restore Alt+Tab registry settings if we changed them
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                    r"Control Panel\Desktop", 
                                    0, winreg.KEY_SET_VALUE)
                # Remove our custom settings
                winreg.DeleteValue(key, "CoolSwitchRows")
                winreg.DeleteValue(key, "CoolSwitchColumns")
                winreg.CloseKey(key)
                logger.info("Restored Alt+Tab settings in registry")
            except Exception as e:
                # Errors are expected if keys don't exist
                pass
                
            # Unregister hotkeys
            if hasattr(self, 'msg_hwnd') and self.msg_hwnd:
                try:
                    self.user32.UnregisterHotKey(self.msg_hwnd, 100)  # Alt+Tab
                    self.user32.UnregisterHotKey(self.msg_hwnd, 101)  # Alt+D
                    logger.info("Unregistered hotkeys")
                except Exception as e:
                    logger.error(f"Error unregistering hotkeys: {e}")
            
            # Also try unregistering global hotkeys
            try:
                self.user32.UnregisterHotKey(None, 100)  # Alt+Tab
                self.user32.UnregisterHotKey(None, 101)  # Alt+D
                logger.info("Unregistered global hotkeys")
            except Exception as e:
                logger.error(f"Error unregistering global hotkeys: {e}")
            
            # Remove message filter hook if installed
            if hasattr(self, 'msg_hook_id') and self.msg_hook_id:
                try:
                    result = self.user32.UnhookWindowsHookEx(self.msg_hook_id)
                    if result:
                        logger.info("Message filter hook uninstalled")
                    else:
                        logger.error("Failed to uninstall message filter hook")
                except Exception as e:
                    logger.error(f"Error removing message filter hook: {e}")
            
            # Unlock foreground window if we locked it
            try:
                self.user32.LockSetForegroundWindow(0)  # LSFW_UNLOCK
                logger.info("Unlocked foreground window")
            except Exception as e:
                logger.error(f"Error unlocking foreground window: {e}")
            
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
        
        # Position control panel at the top with increased height
        control_height = 80  # Increased from 65 to 80 for better coverage of orange line
        self.root.geometry(f"{screen_width}x{control_height}+0+0")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.configure(bg='#f8f9fa')
        
        # Create navigation section
        control_frame = tk.Frame(self.root, bg='#f8f9fa', height=control_height)
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
        
        # Initialize keyboard blocker
        self.keyboard_blocker = KeyboardBlocker()
        self.keyboard_blocker.start_blocking()
    
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
        """Navigate to the specified URL while maintaining kiosk mode."""
        if not url:
            return
            
        try:
            # Store if we're in a mozilla domain
            was_mozilla = False
            current_url = self.driver.current_url
            if "mozilla" in current_url.lower():
                was_mozilla = True
                
            logger.info(f"Navigating to: {url}")
            
            # Save fullscreen state before navigating
            self.driver.execute_script("""
                window.wasFullscreen = document.fullscreenElement != null;
                
                // Ensure we can navigate properly
                try {
                    // Use direct location changing which is more reliable than history
                    window.location.href = arguments[0];
                } catch(e) {
                    console.error("Navigation error:", e);
                }
            """, url)
            
            # If we were on a mozilla page or going to one, we need extra handling
            if was_mozilla or "mozilla" in url.lower():
                # Schedule fixes with short delay to ensure they run after page loads
                self.root.after(500, self.lock_firefox_window)
                self.root.after(800, self.apply_javascript_fixes)
                self.root.after(1000, self.hide_fullscreen_notification)
                
                # Add a special "ensure navigation worked" check
                self.root.after(1500, self.check_navigation_success, url)
            
            # Set a timer to bring control panel back to front
            self.root.after(1000, self.bring_control_to_front)
            
        except Exception as e:
            logger.error(f"Error in navigate_to: {e}")
            
    def check_navigation_success(self, intended_url):
        """Check if navigation succeeded and fix if needed."""
        try:
            # Get current URL
            current_url = self.driver.current_url
            
            # If we're on mozilla.org and stuck, force return home
            if "mozilla.org" in current_url.lower() or "about:blank" in current_url.lower():
                logger.warning(f"Detected stuck on mozilla site, forcing return to homepage")
                self.go_home()
        except Exception as e:
            logger.error(f"Error checking navigation: {e}")
            
    def go_back(self):
        """Navigate back in browser history with enhanced reliability."""
        try:
            logger.info("Go back requested")
            if hasattr(self, 'driver') and self.driver:
                try:
                    # Use JavaScript for most reliable back navigation with fallback
                    self.driver.execute_script("""
                        // Store current URL in case we need to force reload
                        let currentUrl = window.location.href;
                        let isMozilla = currentUrl.toLowerCase().includes('mozilla');
                        
                        // Try normal history navigation
                        history.back();
                        
                        // Check if navigation succeeded after a short delay
                        setTimeout(function() {
                            if (window.location.href === currentUrl || isMozilla) {
                                // Force navigation to homepage as fallback
                                window.location.href = arguments[0];
                            }
                        }, 500);
                    """, self.homepage)
                    
                    # Schedule our fixes to be reapplied after navigation
                    self.root.after(800, self.apply_javascript_fixes)
                    self.root.after(1000, self.lock_firefox_window)
                    self.root.after(1200, self.hide_fullscreen_notification)
                except Exception as e:
                    logger.error(f"Error in advanced back navigation: {e}")
                    # Force return to homepage as ultimate fallback
                    self.go_home()
        except Exception as e:
            logger.error(f"Error in go_back: {e}")
            
    def go_home(self):
        """Navigate to the homepage with enhanced reliability."""
        try:
            logger.info("Go home requested")
            if hasattr(self, 'driver') and self.driver:
                try:
                    # Use JavaScript for direct navigation
                    self.driver.execute_script("""
                        // Direct location change is most reliable
                        window.location.href = arguments[0];
                    """, self.homepage)
                    logger.info(f"Navigated to homepage via JavaScript: {self.homepage}")
                    
                    # Schedule our fixes to be reapplied after navigation
                    self.root.after(800, self.apply_javascript_fixes)
                    self.root.after(1000, self.lock_firefox_window)
                    self.root.after(1200, self.hide_fullscreen_notification)
                except Exception as e:
                    logger.error(f"Error in JavaScript homepage navigation: {e}")
                    try:
                        # Fallback to Selenium get
                        self.driver.get(self.homepage)
                        logger.info(f"Navigated to homepage via Selenium: {self.homepage}")
                    except Exception as e2:
                        logger.error(f"Error in Selenium homepage navigation: {e2}")
        except Exception as e:
            logger.error(f"Error in go_home: {e}")
    
    def start_browser(self):
        """Start Firefox in kiosk mode using Selenium WebDriver."""
        try:
            logger.info("Initializing Firefox with Selenium WebDriver")
            
            # First ensure all Firefox processes are killed
            self.kill_all_firefox_processes()
            
            # Create a Firefox options object
            options = Options()
            
            # Force TRUE fullscreen mode arguments - these are critical
            options.add_argument('-kiosk')
            options.add_argument('-full-screen')
            options.add_argument('-no-remote')
            options.add_argument('-private')
            options.add_argument('--kiosk')  # Double kiosk mode argument
            
            # Add direct fullscreen F11 argument
            options.add_argument('--start-fullscreen')
            options.add_argument('--start-maximized')
            
            # CRITICAL: Add arguments to directly suppress the chrome and address bar
            options.add_argument('--chrome-frame=0')
            options.add_argument('--disable-features=SiteIsolationForPasswordSites,IsolateOrigins,site-per-process')
            options.add_argument('--no-sandbox')
            options.add_argument('--presentation')
            
            # IMPORTANT: This modification prevents the "false" tab and address bar
            options.add_argument('--app=' + self.homepage)  # App mode removes address bar
            
            # Position window higher to hide the orange line
            offset_y = -50
            
            options.add_argument('--window-size=' + str(self.root.winfo_screenwidth()) + ',' + 
                              str(self.root.winfo_screenheight() - self.root.winfo_height() + abs(offset_y)))
            options.add_argument('--window-position=0,' + str(self.root.winfo_height() + offset_y))
            options.add_argument('--disable-infobars')
            
            # Add Firefox-specific command-line arguments
            options.add_argument('--browser.tabs.drawInTitlebar=false')
            options.add_argument('--browser.tabs.visibility.enabled=false')
            options.add_argument('--browser.display.focus_ring_width=0')
            
            # Set Firefox to auto-fullscreen
            options.set_preference("browser.startup.homepage", self.homepage)
            options.set_preference("browser.fullscreen.autohide", False)
            options.set_preference("browser.fullscreen.enabled", True)
            options.set_preference("browser.fullscreen.locked", True)
            options.set_preference("browser.fullscreen.native.enabled", True)
            options.set_preference("browser.link.open_newwindow", 1)
            options.set_preference("browser.link.open_newwindow.restriction", 0)
            
            # CRITICAL: Fix for the "false" tab/address bar
            options.set_preference("browser.startup.page", 1)
            options.set_preference("browser.startup.homepage_override.mstone", "ignore")
            options.set_preference("startup.homepage_welcome_url", "")
            options.set_preference("startup.homepage_welcome_url.additional", "")
            options.set_preference("startup.homepage_override_url", "")
            
            # CRITICAL: Prevent fullscreen notification
            options.set_preference("full-screen-api.warning.timeout", 0)
            options.set_preference("full-screen-api.warning.delay", 0)
            options.set_preference("full-screen-api.transition-duration.enter", "0 0")
            options.set_preference("full-screen-api.transition-duration.leave", "0 0")
            options.set_preference("full-screen-api.exit-on-deactivate", False)
            options.set_preference("full-screen-api.approval-required", False)
            options.set_preference("full-screen-api.pointer-lock.enabled", False)
            
            # Force true kiosk mode
            options.set_preference("kiosk_mode.enabled", True)
            options.set_preference("browser.chrome.toolbar_tips", False)
            options.set_preference("browser.chrome.toolbar_style", 0)
            options.set_preference("browser.chrome.display_icons", False)
            options.set_preference("kiosk.enabled", True)
            options.set_preference("kiosk.mode", True)
            options.set_preference("browser.kiosk_mode", True)
            
            # CRITICAL: Force browser chrome to be hidden from the beginning
            options.set_preference("browser.fullscreen.hide_chrome", True)
            options.set_preference("kiosk.hide_chrome", True)
            options.set_preference("browser.fullscreen.hideChromeUI", True)
            options.set_preference("browser.fullscreen.autohide", False)
            options.set_preference("browser.fullscreen.lockChromeUI", True)
            
            # CRITICAL: Force a blank chrome URL to prevent the address bar from loading
            options.set_preference("browser.chromeURL", "about:blank")
            
            # CRITICAL: Force a different UI mode to hide address bar
            options.set_preference("browser.uiCustomization.state", """{"placements":{"widget-overflow-fixed-list":[],"nav-bar":[],"TabsToolbar":["tabbrowser-tabs"],"toolbar-menubar":[],"PersonalToolbar":[]}}""")
            options.set_preference("browser.compactmode.show", False)
            options.set_preference("browser.uidensity", 1)
            options.set_preference("browser.theme.toolbar-theme", 0)
            
            # Additional critical preferences to hide the address bar
            options.set_preference("browser.urlbar.trimURLs", True)
            options.set_preference("browser.urlbar.hideGoButton", True)
            options.set_preference("browser.urlbar.maxRichResults", 0)
            options.set_preference("browser.urlbar.autoFill", False)
            options.set_preference("browser.urlbar.showSearchTerms.enabled", False)
            options.set_preference("browser.urlbar.suggest.searches", False)
            options.set_preference("browser.urlbar.suggest.history", False)
            options.set_preference("browser.urlbar.suggest.bookmark", False)
            options.set_preference("browser.urlbar.suggest.openpage", False)
            options.set_preference("browser.urlbar.suggest.topsites", False)
            options.set_preference("browser.urlbar.formatting.enabled", False)
            options.set_preference("browser.toolbars.bookmarks.visibility", "never")
            options.set_preference("browser.tabs.inTitlebar", 0)
            
            # ULTRA-AGGRESSIVE ADDRESS BAR HIDING - More preferences to ensure it stays hidden
            options.set_preference("browser.urlbar.enabled", False)
            options.set_preference("browser.urlbar.visible", False)
            options.set_preference("browser.urlbar.accessibility.tabToSearch.enabled", False)
            options.set_preference("browser.urlbar.autoFill.enabled", False)
            options.set_preference("browser.urlbar.clickSelectsAll", False)
            options.set_preference("browser.urlbar.doubleClickSelectsAll", False)
            options.set_preference("browser.urlbar.richResults.autoFill", False)
            options.set_preference("browser.urlbar.richResults.enabled", False)
            options.set_preference("browser.urlbar.searchEngagementTelemetry.enabled", False)
            options.set_preference("browser.urlbar.searchTips.enabled", False)
            options.set_preference("browser.urlbar.shortcuts.bookmarks", False)
            options.set_preference("browser.urlbar.shortcuts.history", False)
            options.set_preference("browser.urlbar.shortcuts.quickactions", False)
            options.set_preference("browser.urlbar.shortcuts.tabs", False)
            options.set_preference("browser.urlbar.showSearchSuggestionsFirst", False)
            options.set_preference("browser.urlbar.speculativeConnect.enabled", False)
            options.set_preference("browser.urlbar.suggest.bestmatch", False)
            options.set_preference("browser.urlbar.suggest.engines", False)
            options.set_preference("browser.urlbar.suggest.quickactions", False)
            options.set_preference("browser.urlbar.suggest.quicksuggest.nonsponsored", False)
            options.set_preference("browser.urlbar.suggest.quicksuggest.sponsored", False)
            options.set_preference("browser.urlbar.trimURLs", True)
            options.set_preference("browser.urlbar.update1", False)
            options.set_preference("browser.urlbar.update1.interventions", False)
            options.set_preference("browser.urlbar.update1.searchTips", False)
            options.set_preference("browser.urlbar.update2", False)
            options.set_preference("browser.urlbar.view.column", False)
            # Ensure navigation toolbar is hidden
            options.set_preference("browser.toolbars.navbar.enabled", False)
            options.set_preference("browser.navigation-toolbar.enabled", False)
            options.set_preference("browser.toolbars.navigation.enabled", False)
            options.set_preference("browser.ui.toolbar.enabled", False)
            options.set_preference("browser.ui.navbar.enabled", False)
            
            # Additional UI hiding preferences
            options.set_preference("toolkit.legacyUserProfileCustomizations.stylesheets", True)
            options.set_preference("ui.prefersReducedMotion", 1)
            options.set_preference("ui.systemUsesDarkTheme", 0)
            
            # Fix startup flags to prevent windows from starting incorrectly
            options.set_preference("startup.homepage_welcome_url", "")
            options.set_preference("startup.homepage_welcome_url.additional", "")
            options.set_preference("startup.homepage_override_url", "")
            
            # Disable auto-update popups
            options.set_preference("app.update.auto", False)
            options.set_preference("app.update.enabled", False)
            options.set_preference("app.update.silent", True)

            # Create a unique profile name for clean environment
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            profile_name = f"kiosk_profile_{timestamp}"
            
            # Create a Firefox profile
            logger.info(f"Creating Firefox profile: {profile_name}")
            firefox_profile_path = os.path.join(os.environ.get('LOCALAPPDATA'), 'Temp', 'KioskProfiles', profile_name)
            os.makedirs(firefox_profile_path, exist_ok=True)
            
            # Create chrome directory for userChrome.css
            chrome_dir = os.path.join(firefox_profile_path, "chrome")
            os.makedirs(chrome_dir, exist_ok=True)
            
            # Create userChrome.css to hide UI elements - Ensure proper file handling
            userChrome_path = os.path.join(chrome_dir, "userChrome.css")
            with open(userChrome_path, "w") as f:
                f.write('@namespace url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");\n')
                f.write('@namespace html url("http://www.w3.org/1999/xhtml");\n\n')
                
                # NUCLEAR APPROACH - Hide everything in the chrome UI
                f.write('/* FORCE ALL UI ELEMENTS HIDDEN */\n')
                f.write(':root #navigator-toolbox {\n')
                f.write('  visibility: collapse !important;\n')
                f.write('  height: 0 !important;\n')
                f.write('  margin-bottom: -50px !important;\n')
                f.write('  overflow: hidden !important;\n')
                f.write('  transition: none !important;\n')
                f.write('  min-height: 0 !important;\n')
                f.write('  z-index: -1 !important;\n')
                f.write('}\n\n')
                
                # Specific additional targeting for the address bar
                f.write('/* EXTREME ADDRESS BAR DESTRUCTION */\n')
                f.write('#urlbar, #urlbar * { display: none !important; }\n')
                f.write('#nav-bar { display: none !important; }\n\n')
                
                # Basic reflow compensation to ensure page is aligned with top of window
                f.write('/* CONTENT POSITIONING COMPENSATION */\n')
                f.write('#browser { margin-top: 0 !important; }\n')
                f.write('#content-deck { margin-top: 0 !important; }\n')
            
            # Create userContent.css - Separate file operation with its own with statement
            userContent_path = os.path.join(chrome_dir, "userContent.css")
            with open(userContent_path, "w") as f:
                f.write('@-moz-document url("about:blank"), url-prefix("about:"), url-prefix("chrome:"), url-prefix("resource:") {\n')
                f.write('  body, html { background-color: white !important; }\n')
                f.write('  * { overflow: hidden !important; }\n')
                f.write('}\n')
                
                # Add rule to ensure links open in same window
                f.write('@-moz-document url-prefix("") {\n')
                f.write('  a[target="_blank"] { target: "_self" !important; }\n')
                f.write('}\n')
            
            # Create user.js with Firefox preferences
            user_js_path = os.path.join(firefox_profile_path, "user.js")
            with open(user_js_path, "w") as f:
                f.write("""
// Enable userChrome.css loading
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);

// Disable Firefox view tab
user_pref("browser.tabs.firefox-view", false);

// CRITICAL: Disable address bar keyboard shortcuts
user_pref("browser.urlbar.accessibility.tabToSearch.enabled", false);
user_pref("browser.urlbar.eventTelemetry.enabled", false);
user_pref("browser.urlbar.openViewOnFocus", false);
user_pref("browser.urlbar.suggest.searches", false);
user_pref("browser.urlbar.suggest.topsites", false);
user_pref("browser.urlbar.suggest.engines", false);
user_pref("browser.urlbar.suggest.history", false);
user_pref("browser.urlbar.suggest.bookmark", false);
user_pref("browser.urlbar.suggest.tabswitch", false);
user_pref("browser.urlbar.trimURLs", false);
user_pref("browser.urlbar.oneOffSearches", false);

// CRITICAL: Disable all developer tools
user_pref("devtools.accessibility.enabled", false);
user_pref("devtools.application.enabled", false);
user_pref("devtools.command-button-measure.enabled", false);
user_pref("devtools.command-button-paintflashing.enabled", false);
user_pref("devtools.command-button-responsive.enabled", false);
user_pref("devtools.command-button-rulers.enabled", false);
user_pref("devtools.command-button-screenshot.enabled", false);
user_pref("devtools.debugger.enabled", false);
user_pref("devtools.debugger.remote-enabled", false);
user_pref("devtools.dom.enabled", false);
user_pref("devtools.editor.enabled", false);
user_pref("devtools.enabled", false);
user_pref("devtools.inspector.enabled", false);
user_pref("devtools.memory.enabled", false);
user_pref("devtools.netmonitor.enabled", false);
user_pref("devtools.overflow.debugging.enabled", false);
user_pref("devtools.performance.enabled", false);
user_pref("devtools.responsive.enabled", false);
user_pref("devtools.responsive.viewport.enabled", false);
user_pref("devtools.serviceWorkers.testing.enabled", false);
user_pref("devtools.styleeditor.enabled", false);
user_pref("devtools.webconsole.enabled", false);

// CRITICAL: Disable keyboard shortcuts
user_pref("ui.key.menuAccessKeyFocuses", false);
user_pref("ui.key.menuAccessKey", 0);
user_pref("browser.tabs.tabMinWidth", 0);
user_pref("browser.tabs.closeWindowWithLastTab", false);

// Force fullscreen
user_pref("full-screen-api.warning.timeout", 0);
user_pref("full-screen-api.warning.delay", 0);
user_pref("full-screen-api.transition-duration.enter", "0 0");
user_pref("full-screen-api.transition-duration.leave", "0 0");
user_pref("full-screen-api.transition.timeout", 0);
user_pref("full-screen-api.exit-on-deactivate", false);
user_pref("browser.fullscreen.exit-on-escape", false);
user_pref("browser.fullscreen.autohide", false);
""")
            
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
            
            # First activate fullscreen mode before navigating to any site to prevent notifications
            try:
                # Execute JavaScript to force fullscreen immediately
                self.driver.execute_script("""
                    // Force fullscreen mode on startup
                    (function() {
                        // Hide fullscreen notifications
                        var style = document.createElement('style');
                        style.textContent = `
                            #fullscreen-warning, .fullscreen-notification {
                                display: none !important;
                                opacity: 0 !important;
                            }
                        `;
                        document.head.appendChild(style);
                        
                        // Request fullscreen directly
                        try {
                            if (document.documentElement.requestFullscreen) {
                                document.documentElement.requestFullscreen();
                            } else if (document.documentElement.mozRequestFullScreen) {
                                document.documentElement.mozRequestFullScreen();
                            }
                        } catch(e) { console.log("Fullscreen error:", e); }
                    })();
                """)
                logger.info("Applied initial fullscreen")
                
                # Also try using F11 key before navigation
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.key_down(Keys.F11).perform()
                logger.info("Sent F11 key before navigation")
            except Exception as e:
                logger.error(f"Error setting initial fullscreen: {e}")
            
            # Navigate to homepage
            logger.info(f"Navigating to: {self.homepage}")
            self.driver.get(self.homepage)
            
            # Set a timer to make our control panel come to the front
            self.root.after(3000, self.bring_control_to_front)
            
            # Add timer to lock Firefox window using Win32 APIs
            self.root.after(1000, self.lock_firefox_window)
            
            # Try to hide address bar with JavaScript after page loads
            self.root.after(2000, self.apply_javascript_fixes)
            
            # Schedule a specific check for fullscreen notification hiding
            self.root.after(2500, self.hide_fullscreen_notification)
            
            logger.info("Firefox WebDriver started successfully")
            
        except Exception as e:
            logger.error(f"WebDriver start error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
    
    def lock_firefox_window(self):
        """Find and lock the Firefox window in kiosk mode."""
        try:
            logger.info("Locking Firefox window in kiosk mode")
            
            def find_firefox_window(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd).lower()
                    if "firefox" in title or "mozilla" in title:
                        logger.info(f"Found Firefox window to lock: {hwnd}, Title: {title}")
                        
                        # Store reference to the window
                        self.firefox_hwnd = hwnd
                        
                        # Remove ALL window decoration and controls
                        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
                        # Keep only minimal style needed for the window to function
                        new_style = style & ~(win32con.WS_CAPTION | win32con.WS_THICKFRAME |
                                           win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX |
                                           win32con.WS_SYSMENU)
                        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new_style)
                        
                        # Remove extended styles that could allow interaction
                        ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                        new_ex_style = ex_style & ~(win32con.WS_EX_WINDOWEDGE | win32con.WS_EX_CLIENTEDGE |
                                               win32con.WS_EX_STATICEDGE | win32con.WS_EX_DLGMODALFRAME)
                        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, new_ex_style)
                        
                        # Get window position of our control panel
                        control_height = self.root.winfo_height()
                        screen_width = self.root.winfo_screenwidth()
                        screen_height = self.root.winfo_screenheight()
                        
                        # First ensure window is maximized 
                        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
                        
                        # Position window directly under control panel, filling the screen
                        # MOVE UP: Position window significantly higher to hide orange line
                        # Using a large negative offset to move upward
                        y_offset = -50  # Negative value moves window up, increased to -50
                        
                        win32gui.SetWindowPos(
                            hwnd,
                            win32con.HWND_TOP,  # Stay on top of z-order
                            0,                  # Left position
                            control_height + y_offset,  # Top position (below control panel, shifted up)
                            screen_width,       # Width (fill screen width)
                            screen_height - control_height + abs(y_offset),  # Increase height to compensate
                            win32con.SWP_FRAMECHANGED  # Force frame update with new styles
                        )
                        
                        # Double-check maximization using alternate API
                        ctypes.windll.user32.ShowWindowAsync(hwnd, win32con.SW_MAXIMIZE)
                        
                        # Record successful locking
                        logger.info(f"Successfully locked Firefox window {hwnd} in kiosk mode")
                        return False  # Stop enumeration after first Firefox window
                return True
            
            # Find and lock the Firefox window
            win32gui.EnumWindows(find_firefox_window, None)
            
            # Schedule a security check to make sure the window stays locked
            self.root.after(1000, self.perform_security_checks)
            
        except Exception as e:
            logger.error(f"Error locking Firefox window: {e}")
            # Try fallback approaches and continue security checks anyway
            self.root.after(1000, self.perform_security_checks)
    
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
                    new_style = style & ~(win32con.WS_THICKFRAME | win32con.WS_MINIMIZEBOX | win32con.WS_MAXIMIZEBOX | win32con.WS_SYSMENU)
                    win32gui.SetWindowLong(self.firefox_hwnd, win32con.GWL_STYLE, new_style)
                    
                    # Also remove caption (title bar)
                    ex_style = win32gui.GetWindowLong(self.firefox_hwnd, win32con.GWL_EXSTYLE)
                    new_ex_style = ex_style & ~(win32con.WS_EX_DLGMODALFRAME | win32con.WS_EX_CLIENTEDGE | win32con.WS_EX_STATICEDGE | win32con.WS_EX_WINDOWEDGE)
                    win32gui.SetWindowLong(self.firefox_hwnd, win32con.GWL_EXSTYLE, new_ex_style)
                    
                    # Reapply window position and size
                    control_height = self.root.winfo_height()
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    
                    # Make sure window is maximized first
                    win32gui.ShowWindow(self.firefox_hwnd, win32con.SW_MAXIMIZE)
                    
                    # Position window to fill screen below control panel with SWP_FRAMECHANGED
                    # Apply the same Y offset as in lock_firefox_window
                    y_offset = -50  # Same offset as defined above, increased to -50
                    
                    win32gui.SetWindowPos(
                        self.firefox_hwnd, 
                        win32con.HWND_TOP,
                        0, control_height + y_offset, 
                        screen_width, screen_height - control_height + abs(y_offset),
                        win32con.SWP_FRAMECHANGED
                    )
                    
                    # Last resort - force maximized state 
                    ctypes.windll.user32.ShowWindowAsync(self.firefox_hwnd, win32con.SW_MAXIMIZE)
                
                # Check if window position is correct
                left, top, right, bottom = win32gui.GetWindowRect(self.firefox_hwnd)
                control_height = self.root.winfo_height()
                y_offset = -50  # Same offset as defined above, increased to -50
                
                # If window is not positioned correctly, fix it
                if (top != control_height + y_offset or left != 0):
                    logger.warning(f"Firefox window position changed ({left},{top}), resetting...")
                    screen_width = self.root.winfo_screenwidth()
                    screen_height = self.root.winfo_screenheight()
                    
                    # Reset position with SWP_FRAMECHANGED
                    win32gui.SetWindowPos(
                        self.firefox_hwnd, 
                        win32con.HWND_TOP,
                        0, control_height + y_offset, 
                        screen_width, screen_height - control_height + abs(y_offset),
                        win32con.SWP_FRAMECHANGED
                    )
            
            # Check for any Firefox dialog windows that need to be handled
            self.close_firefox_dialogs()
            
            # Check for multiple Firefox windows
            self.handle_multiple_firefox_windows()
            
            # Limit security checks to run less frequently to avoid interrupting exit dialogs
            self.security_check_timer = self.root.after(2000, self.perform_security_checks)
        except Exception as e:
            logger.error(f"Error in security checks: {e}")
            # Continue checking even if there was an error
            self.security_check_timer = self.root.after(5000, self.perform_security_checks)
    
    def handle_multiple_firefox_windows(self):
        """Find and close extra Firefox windows, keeping only one."""
        try:
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
                if hasattr(self, 'firefox_hwnd') and self.firefox_hwnd != main_window:
                    self.firefox_hwnd = main_window
                    # Re-apply kiosk mode to the main window
                    self.root.after(100, self.lock_firefox_window)
        
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
            
            # Stop keyboard blocker
            if hasattr(self, 'keyboard_blocker'):
                self.keyboard_blocker.stop_blocking()
    
    def show_error(self, message):
        """Show error message."""
        tk.messagebox.showerror("Error", message)

    def show_exit_dialog(self):
        """Show exit dialog with password protection."""
        logger.info("Exit dialog requested")
        
        # Create a Toplevel window for the exit dialog
        exit_dialog = tk.Toplevel(self.root)
        exit_dialog.title("Exit Kiosk Mode")
        exit_dialog.geometry("300x150")
        exit_dialog.attributes('-topmost', True)
        
        # Center the dialog
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width - 300) // 2
        y = (screen_height - 150) // 2
        exit_dialog.geometry(f"300x150+{x}+{y}")
        
        # Grab focus - keep the window active and ensure dialog gets all keyboard input
        exit_dialog.grab_set()
        exit_dialog.focus_force()
        
        # Add administrator password field
        tk.Label(exit_dialog, text="Enter Administrator Password:").pack(pady=(20, 5))
        
        password_entry = tk.Entry(exit_dialog, show="*")
        password_entry.pack(pady=5)
        
        # Add message area for incorrect password
        message_label = tk.Label(exit_dialog, text="", fg="red")
        message_label.pack(pady=5)
        
        def verify_password():
            """Verify the entered password."""
            entered_password = password_entry.get()
            if entered_password == self.admin_password:
                logger.info("Admin password accepted, exiting kiosk mode")
                exit_dialog.grab_release()  # Release grab before destroying
                exit_dialog.destroy()
                self._exit_dialog_showing = False
                self.cleanup()
            else:
                logger.warning(f"Invalid password attempt: {entered_password}")
                message_label.config(text="Invalid password. Please try again.")
                password_entry.delete(0, tk.END)
                password_entry.focus_set()
        
        def cancel_exit():
            """Cancel the exit dialog."""
            logger.info("Exit dialog cancelled")
            exit_dialog.grab_release()  # Release grab before destroying
            exit_dialog.destroy()
            self._exit_dialog_showing = False
        
        # Add buttons for exit and cancel
        button_frame = tk.Frame(exit_dialog)
        button_frame.pack(pady=10)
        
        exit_button = tk.Button(button_frame, text="Exit Kiosk", command=verify_password)
        exit_button.pack(side=tk.LEFT, padx=5)
        
        cancel_button = tk.Button(button_frame, text="Cancel", command=cancel_exit)
        cancel_button.pack(side=tk.LEFT, padx=5)
        
        # Bind Enter key to verify_password
        exit_dialog.bind('<Return>', lambda e: verify_password())
        
        # Bind Escape key to cancel_exit
        exit_dialog.bind('<Escape>', lambda e: cancel_exit())
        
        # Override the close button to cancel
        exit_dialog.protocol("WM_DELETE_WINDOW", cancel_exit)
        
        # Handle window close via Alt+F4
        def handle_alt_f4():
            """Emergency exit via Alt+F4."""
            logger.info("Emergency exit requested via Alt+F4")
            # Restore taskbar for emergency exit
            if hasattr(self, 'taskbar_hwnd') and self.taskbar_hwnd:
                win32gui.ShowWindow(self.taskbar_hwnd, win32con.SW_SHOW)
                logger.info("Taskbar restored for emergency exit")
            # Force application exit
            self.root.destroy()
            sys.exit(0)
        
        exit_dialog.bind('<Alt-F4>', lambda e: handle_alt_f4())
        
        # Flag to indicate dialog is showing (to prevent multiple copies)
        self._exit_dialog_showing = True
        
        # Set focus on password entry after everything is set up
        password_entry.focus_set()
        
        # Schedule focus check and reset to ensure dialog keeps focus
        def ensure_focus():
            if exit_dialog.winfo_exists():
                if not password_entry.focus_get():
                    logger.debug("Resetting focus to password entry")
                    password_entry.focus_force()
                exit_dialog.after(100, ensure_focus)
        
        # Start focus check
        exit_dialog.after(100, ensure_focus)
    
    def cleanup_browser(self):
        """Clean up browser resources."""
        try:
            # Close the WebDriver if it exists
            if hasattr(self, 'driver') and self.driver:
                logger.info("Closing WebDriver")
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.error(f"Error closing WebDriver: {e}")
                finally:
                    self.driver = None
            
            # Kill any remaining Firefox processes
            self.kill_all_firefox_processes()
            
            # Clean up profile directory
            if hasattr(self, 'firefox_profile_path') and self.firefox_profile_path:
                try:
                    import shutil
                    if os.path.exists(self.firefox_profile_path):
                        logger.info(f"Cleaning up profile directory: {self.firefox_profile_path}")
                        shutil.rmtree(self.firefox_profile_path, ignore_errors=True)
                except Exception as e:
                    logger.error(f"Error cleaning up profile directory: {e}")
        except Exception as e:
            logger.error(f"Error in browser cleanup: {e}")
    
    def start_browser_with_url(self, url):
        """Start browser with a specific URL."""
        # Store URL for navigation after browser starts
        self.current_url = url
        # Then start browser normally
        self.start_browser()
        # The navigation will be handled by start_browser

    def kill_all_firefox_processes(self):
        """Kill all Firefox processes to ensure clean start."""
        try:
            logger.info("Killing all Firefox processes")
            
            # First try taskkill /T to terminate Firefox and all child processes
            try:
                logger.info("Using taskkill /T to terminate Firefox and all child processes")
                subprocess.run(["taskkill", "/F", "/IM", "firefox.exe", "/T"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL, 
                               shell=True, 
                               timeout=5)
            except Exception as e:
                logger.error(f"Error using taskkill: {e}")
            
            # Then use WMIC as a backup approach
            try:
                logger.info("Using WMIC to terminate Firefox")
                subprocess.run(["wmic", "process", "where", "name='firefox.exe'", "delete"], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL, 
                               shell=True, 
                               timeout=5)
            except Exception as e:
                logger.error(f"Error using WMIC: {e}")
            
            # Directly use psutil to find and kill any remaining Firefox processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'firefox' in proc.info['name'].lower():
                        proc.kill()
                except Exception:
                    pass
            
            # Remove Firefox lock files that might prevent a clean start
            try:
                logger.info("Removing Firefox lock files")
                # Find the Firefox profiles directory
                appdata = os.environ.get('APPDATA')
                if appdata:
                    firefox_dir = os.path.join(appdata, 'Mozilla', 'Firefox')
                    if os.path.exists(firefox_dir):
                        # Look for parent.lock files and remove them
                        for root, dirs, files in os.walk(firefox_dir):
                            for file in files:
                                if file == 'parent.lock' or file == '.parentlock':
                                    try:
                                        lock_path = os.path.join(root, file)
                                        os.remove(lock_path)
                                    except Exception:
                                        pass
                        
                        # Try to backup profiles.ini and possibly restore later
                        profiles_ini = os.path.join(firefox_dir, 'profiles.ini')
                        if os.path.exists(profiles_ini):
                            logger.info(f"Removing profiles.ini: {profiles_ini}")
                            try:
                                # Backup the file first
                                backup_path = profiles_ini + '.bak'
                                import shutil
                                shutil.copy2(profiles_ini, backup_path)
                            except Exception as e:
                                logger.error(f"Error backing up profiles.ini: {e}")
            except Exception as e:
                logger.error(f"Error removing Firefox lock files: {e}")
            
            # Wait a moment to ensure all processes are terminated
            time.sleep(0.1)
            
            # Look for any Firefox dialog windows and close them
            self.close_firefox_dialogs()
            
        except Exception as e:
            logger.error(f"Error killing Firefox processes: {e}")
            
    def close_firefox_dialogs(self):
        """Find and close any Firefox dialog windows."""
        try:
            logger.info("Looking for Firefox dialog windows")
            
            def close_dialog(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    # Look for Firefox-related dialogs
                    if ('Firefox' in title and 
                        ('Crash Reporter' in title or 
                         'Safe Mode' in title or 
                         'already running' in title or
                         'Import' in title or
                         'Settings' in title or
                         'About' in title)):
                        logger.info(f"Closing Firefox dialog: {title}")
                        try:
                            # Send WM_CLOSE message to close the dialog
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                        except Exception as e:
                            logger.error(f"Error closing dialog: {e}")
                return True
            
            # Enumerate all windows and close matching dialogs
            win32gui.EnumWindows(close_dialog, None)
            
        except Exception as e:
            logger.error(f"Error closing Firefox dialogs: {e}")
            
    def bring_control_to_front(self):
        """Bring the control panel to the front of the z-order."""
        try:
            logger.info("Bringing control panel to front")
            self.root.lift()
            self.root.attributes('-topmost', True)
            
            # Now find and manage Firefox window
            def find_firefox_window(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if "Firefox" in title:
                        logger.info(f"Found Firefox window: '{title}'")
                        # Store window handle
                        self.firefox_hwnd = hwnd
                        
                        # Apply DWM (Desktop Window Manager) fixes to hide tab bar
                        try:
                            import ctypes.wintypes
                            # Use DWM API to modify window frame
                            DWMWA_EXCLUDED_FROM_PEEK = 12
                            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                                hwnd,
                                DWMWA_EXCLUDED_FROM_PEEK,
                                ctypes.byref(ctypes.c_bool(True)),
                                ctypes.sizeof(ctypes.c_bool)
                            )
                        except Exception as e:
                            logger.error(f"Error applying DWM fixes: {e}")
                        
                        return False  # Stop enumeration after first Firefox window
                return True
            
            # Find Firefox window
            win32gui.EnumWindows(find_firefox_window, None)
            
        except Exception as e:
            logger.error(f"Error bringing control panel to front: {e}")

    def apply_javascript_fixes(self):
        """Apply JavaScript fixes to hide the address bar and customize Firefox UI."""
        try:
            logger.info("Applying JavaScript fixes")
            
            if hasattr(self, 'driver') and self.driver:
                # First, directly execute script to hide fullscreen notification permanently
                self.driver.execute_script("""
                    (function() {
                        // Create a style to hide fullscreen notification
                        var styleFS = document.createElement('style');
                        styleFS.type = 'text/css';
                        styleFS.id = 'hide-fullscreen-notification';
                        styleFS.textContent = `
                            #fullscreen-warning,
                            #fullscreen-exit-button,
                            .fullscreen-notification {
                                display: none !important;
                                visibility: hidden !important;
                                opacity: 0 !important;
                                height: 0 !important;
                                width: 0 !important;
                                pointer-events: none !important;
                                margin: 0 !important;
                                padding: 0 !important;
                                position: fixed !important;
                                top: -9999px !important;
                                left: -9999px !important;
                                z-index: -9999 !important;
                            }
                        `;
                        (document.head || document.documentElement).appendChild(styleFS);
                    })();
                """)
                
                # Apply page load event interception script to maintain fullscreen
                self.driver.execute_script("""
                    (function() {
                        // Track fullscreen state to maintain it during navigation
                        if (!window.kioskState) {
                            window.kioskState = {
                                wasFullscreen: true,
                                navigationCount: 0
                            };
                        }
                        
                        // Create a fullscreen maintenance function
                        if (!window.maintainFullscreen) {
                            window.maintainFullscreen = function() {
                                // Force fullscreen using all available methods
                                try {
                                    if (document.documentElement.requestFullscreen) {
                                        document.documentElement.requestFullscreen();
                                    } else if (document.documentElement.mozRequestFullScreen) {
                                        document.documentElement.mozRequestFullScreen();
                                    } else if (document.documentElement.webkitRequestFullscreen) {
                                        document.documentElement.webkitRequestFullscreen();
                                    }
                                    window.fullScreen = true;
                                } catch(e) {
                                    console.error("Fullscreen maintenance error:", e);
                                }
                            };
                        }
                        
                        // Listen for page transitions that might affect fullscreen
                        if (!window.loadListenersAttached) {
                            window.loadListenersAttached = true;
                            
                            // Capture navigation events
                            ['pageshow', 'load', 'DOMContentLoaded'].forEach(function(eventName) {
                                window.addEventListener(eventName, function() {
                                    window.kioskState.navigationCount++;
                                    console.log("Navigation event: " + eventName + " (" + window.kioskState.navigationCount + ")");
                                    
                                    // Try to restore fullscreen immediately
                                    window.maintainFullscreen();
                                    
                                    // And again after a delay to catch edge cases
                                    setTimeout(window.maintainFullscreen, 300);
                                });
                            });
                            
                            // Intercept click events on links to preserve fullscreen state
                            document.addEventListener('click', function(e) {
                                var target = e.target;
                                
                                // Find if the clicked element is or contains a link
                                while (target && target.nodeName !== 'A' && target.parentNode) {
                                    target = target.parentNode;
                                }
                                
                                if (target && target.nodeName === 'A') {
                                    // It's a link - update our fullscreen state flag
                                    window.kioskState.wasFullscreen = 
                                        document.fullscreenElement !== null || 
                                        document.mozFullScreenElement !== null ||
                                        document.webkitFullscreenElement !== null ||
                                        window.fullScreen === true;
                                        
                                    console.log("Link clicked, fullscreen state:", window.kioskState.wasFullscreen);
                                }
                            }, true);
                            
                            // Critical: intercept popstate (back/forward navigation)
                            window.addEventListener('popstate', function() {
                                console.log("Popstate event detected");
                                // Force fullscreen after a short delay
                                setTimeout(window.maintainFullscreen, 300);
                                setTimeout(window.maintainFullscreen, 600);
                            });
                        }
                    })();
                """)
                
                # Ultra-aggressive CSS via JavaScript to completely remove the address bar
                self.driver.execute_script("""
                    (function() {
                        // Create a style element specifically for hiding address bar
                        var style = document.createElement('style');
                        style.type = 'text/css';
                        style.id = 'hide-address-bar-style';
                        
                        // FOCUSED ADDRESS BAR HIDING: Ultra-aggressive CSS
                        style.innerHTML = `
                            @namespace url("http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul");
                            
                            /* SPECIFIC ADDRESS BAR TARGETING */
                            #urlbar-container, 
                            #urlbar, 
                            #urlbar-input-container,
                            #urlbar-background, 
                            #identity-box,
                            .urlbar-input-container,
                            #page-action-buttons,
                            #tracking-protection-icon-container,
                            #urlbar-label-box,
                            #identity-icon-box,
                            #identity-icon,
                            #connection-icon,
                            #urlbar-search-button,
                            #star-button-box,
                            #reader-mode-button,
                            #page-action-buttons {
                                display: none !important;
                                visibility: collapse !important;
                                height: 0 !important;
                                min-height: 0 !important;
                                max-height: 0 !important;
                                width: 0 !important;
                                min-width: 0 !important;
                                max-width: 0 !important;
                                opacity: 0 !important;
                                overflow: hidden !important;
                                position: fixed !important;
                                top: -1000px !important;
                                left: -1000px !important;
                                z-index: -9999 !important;
                                pointer-events: none !important;
                                margin: 0 !important;
                                padding: 0 !important;
                                border: 0 !important;
                                clip-path: polygon(0 0, 0 0, 0 0) !important;
                            }
                            
                            /* ADDRESS BAR CONTAINER */
                            #nav-bar {
                                height: 0 !important;
                                min-height: 0 !important;
                                max-height: 0 !important;
                                padding: 0 !important;
                                margin: 0 !important;
                                opacity: 0 !important;
                                position: fixed !important;
                                top: -1000px !important;
                                z-index: -9999 !important;
                                visibility: collapse !important;
                            }
                            
                            /* ENSURE BROWSER CONTENT TAKES FULL HEIGHT */
                            #browser, #appcontent, #content, .browserStack, browser {
                                margin-top: 0 !important;
                                padding-top: 0 !important;
                            }
                        `;
                        
                        // Add style to document
                        (document.head || document.documentElement).appendChild(style);
                        
                        // Direct DOM manipulation for stubborn address bar elements
                        function hideAddressBarElements() {
                            // List of address bar related element IDs to target
                            const elementsToHide = [
                                "urlbar-container", 
                                "urlbar", 
                                "urlbar-input-container",
                                "urlbar-background", 
                                "identity-box",
                                "page-action-buttons",
                                "tracking-protection-icon-container",
                                "urlbar-label-box",
                                "identity-icon-box",
                                "identity-icon",
                                "connection-icon",
                                "urlbar-search-button",
                                "star-button-box",
                                "reader-mode-button",
                                "nav-bar"
                            ];
                            
                            // Apply direct element manipulation
                            elementsToHide.forEach(id => {
                                const element = document.getElementById(id);
                                if (element) {
                                    element.style.display = "none";
                                    element.style.visibility = "collapse";
                                    element.style.opacity = "0";
                                    element.style.height = "0";
                                    element.style.minHeight = "0";
                                    element.style.maxHeight = "0";
                                    element.style.overflow = "hidden";
                                    element.style.position = "fixed";
                                    element.style.top = "-1000px";
                                    element.style.zIndex = "-9999";
                                    
                                    // Most aggressive approach: try to remove from DOM
                                    try {
                                        if (element.parentNode) {
                                            element.parentNode.removeChild(element);
                                        }
                                    } catch(e) {
                                        // Element might be protected from removal
                                    }
                                }
                            });
                        }
                        
                        // Run immediately
                        hideAddressBarElements();
                        
                        // Add interval to persistently hide address bar elements
                        setInterval(hideAddressBarElements, 500);
                    })();
                """)
                
                # Force browser into true fullscreen mode with F11
                try:
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    # Create action chain to press F11 key to force fullscreen
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.F11).perform()
                    logger.info("Sent F11 key to force fullscreen mode")
                except Exception as e:
                    logger.error(f"Error sending F11 key: {e}")
                
                logger.info("JavaScript fixes applied")
                
                # Schedule a follow-up to re-apply fixes
                self.root.after(10000, self.apply_javascript_fixes)
            else:
                logger.warning("Cannot apply JavaScript fixes: WebDriver not initialized")
        except Exception as e:
            logger.error(f"Error applying JavaScript fixes: {e}")
            # Schedule a follow-up with delay
            self.root.after(3000, self.apply_javascript_fixes)
    
    def apply_additional_browser_fixes(self):
        """Apply additional browser fixes for hiding UI elements."""
        try:
            logger.info("Applying additional browser fixes")
            
            # Use Selenium to press F11 for fullscreen
            if hasattr(self, 'driver') and self.driver:
                try:
                    from selenium.webdriver.common.keys import Keys
                    from selenium.webdriver.common.action_chains import ActionChains
                    
                    # Create action chain to press F11
                    actions = ActionChains(self.driver)
                    actions.key_down(Keys.F11).perform()
                    logger.info("Sent F11 key to enforce fullscreen")
                except Exception as e:
                    logger.error(f"Error sending F11 key: {e}")
                
                # Inject additional CSS to hide any UI elements that might have appeared
                script = """
                    (function() {
                        // Ensure the style element exists
                        var style = document.getElementById('kiosk-additional-styles');
                        if (!style) {
                            style = document.createElement('style');
                            style.type = 'text/css';
                            style.id = 'kiosk-additional-styles';
                            (document.head || document.documentElement).appendChild(style);
                        }
                        
                        // Add aggressive CSS to hide all UI
                        style.innerHTML = `
                            /* Hide ALL UI elements */
                            #navigator-toolbox, #nav-bar, #TabsToolbar, #PersonalToolbar, #titlebar,
                            #urlbar-container, #urlbar, #identity-box, .urlbar-input-container,
                            #back-button, #forward-button, #home-button, #PanelUI-button,
                            .tabbrowser-tab, .tabs-newtab-button, #alltabs-button {
                                display: none !important;
                                visibility: collapse !important;
                                height: 0 !important;
                                width: 0 !important;
                                opacity: 0 !important;
                                pointer-events: none !important;
                                max-height: 0 !important;
                                min-height: 0 !important;
                                position: fixed !important;
                                top: -500px !important;
                                z-index: -9999 !important;
                            }
                            
                            /* Ensure content takes full height */
                            #browser, .browserContainer, browser {
                                margin-top: 0 !important;
                                padding-top: 0 !important;
                                height: 100vh !important;
                            }
                        `;
                    })();
                """
                self.driver.execute_script(script)
                
                logger.info("Additional browser fixes applied")
            else:
                logger.warning("Cannot apply additional browser fixes: WebDriver not initialized")
        except Exception as e:
            logger.error(f"Error applying additional browser fixes: {e}")
            # Schedule another attempt
            self.root.after(3000, self.apply_additional_browser_fixes)
    
    def hide_fullscreen_notification(self):
        try:
            # ... existing code ...

            # Replace existing Alt+Tab blocking with a more direct approach
            try:
                import ctypes
                from ctypes import wintypes
                import win32con
                import win32api
                import win32gui

                # Constants for system-wide keyboard blocking
                WH_KEYBOARD_LL = 13
                HC_ACTION = 0
                WM_KEYDOWN = 0x0100
                WM_KEYUP = 0x0101
                WM_SYSKEYDOWN = 0x0104
                WM_SYSKEYUP = 0x0105

                # Define virtual key codes
                VK_TAB = 0x09
                VK_ALT = 0x12
                VK_LALT = 0xA4
                VK_RALT = 0xA5
                
                # Create a reference to the hook callback to prevent garbage collection
                self.keyboard_hook_ref = None
                
                # Define the callback function with proper structure
                @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
                def low_level_keyboard_handler(n_code, w_param, l_param):
                    if n_code == HC_ACTION:
                        # Get keyboard state
                        kb_state = (ctypes.c_byte * 256)()
                        ctypes.windll.user32.GetKeyboardState(ctypes.byref(kb_state))
                        
                        # Check if Alt key is down (bit 7 is set when key is down)
                        alt_pressed = (kb_state[VK_ALT] & 0x80) != 0
                        
                        # Extract key information from KBDLLHOOKSTRUCT
                        vk_code = ctypes.cast(l_param, ctypes.POINTER(ctypes.c_ulong))[0]
                        
                        # Debug logging - this helps us track what's happening
                        if w_param in (WM_SYSKEYDOWN, WM_KEYDOWN, WM_SYSKEYUP, WM_KEYUP):
                            event_type = {
                                WM_KEYDOWN: "KEYDOWN",
                                WM_KEYUP: "KEYUP",
                                WM_SYSKEYDOWN: "SYSKEYDOWN",
                                WM_SYSKEYUP: "SYSKEYUP"
                            }.get(w_param, f"Unknown({w_param})")
                            
                            logger.info(f"Key event: {event_type}, vk_code={vk_code}, alt_pressed={alt_pressed}")
                        
                        # Block Alt+Tab specifically
                        if alt_pressed and vk_code == VK_TAB:
                            logger.info("BLOCKED: Alt+Tab detected and blocked")
                            # Force release the Alt key to prevent task switching
                            win32api.keybd_event(VK_ALT, 0, win32con.KEYEVENTF_KEYUP, 0)
                            return 1  # Block this key
                            
                        # Block Alt+Esc (another window switching mechanism)
                        if alt_pressed and vk_code == 0x1B:  # VK_ESCAPE
                            logger.info("BLOCKED: Alt+Escape detected and blocked")
                            return 1
                            
                        # Block WindowsKey+Tab (another window switching mechanism)
                        if (kb_state[0x5B] & 0x80) != 0 and vk_code == VK_TAB:  # 0x5B = VK_LWIN
                            logger.info("BLOCKED: Win+Tab detected and blocked")
                            return 1
                            
                        # Block Alt+Tab before it can be processed
                        if w_param == WM_SYSKEYDOWN and vk_code == VK_TAB:
                            logger.info("BLOCKED: Alt+Tab at system key level")
                            return 1
                        
                        # Block standalone Windows key
                        if vk_code in (0x5B, 0x5C) and w_param == WM_KEYDOWN:  # VK_LWIN, VK_RWIN
                            logger.info("BLOCKED: Windows key")
                            return 1
                            
                    # Pass to next hook
                    return ctypes.windll.user32.CallNextHookEx(None, n_code, w_param, l_param)
                
                # Store reference to prevent garbage collection
                self.keyboard_hook_ref = low_level_keyboard_handler
                
                # Install the hook
                self.hook_handle = ctypes.windll.user32.SetWindowsHookExW(
                    WH_KEYBOARD_LL,
                    self.keyboard_hook_ref,
                    ctypes.windll.kernel32.GetModuleHandleW(None),
                    0
                )
                
                if self.hook_handle:
                    logger.info("Successfully installed system-wide keyboard hook")
                else:
                    error = ctypes.windll.kernel32.GetLastError()
                    logger.error(f"Failed to install keyboard hook, error code: {error}")
                    
                # Set the foreground window to consistently be our Firefox window
                def lock_foreground_window():
                    while True:
                        try:
                            # Find our Firefox window
                            firefox_hwnd = None
                            # Fix: Properly handle error-prone EnumWindows
                            def find_firefox(hwnd, _):
                                try:
                                    nonlocal firefox_hwnd
                                    # Skip invisible windows to prevent errors
                                    if not win32gui.IsWindowVisible(hwnd):
                                        return True
                                    # GetWindowText can fail, handle exceptions
                                    try:
                                        text = win32gui.GetWindowText(hwnd)
                                        if "Firefox" in text:
                                            firefox_hwnd = hwnd
                                            return False
                                    except:
                                        # Skip problematic windows
                                        pass
                                    return True
                                except:
                                    # Suppress any errors in callback
                                    return True
                            
                            # Try to safely enumerate windows with proper error handling
                            try:
                                win32gui.EnumWindows(find_firefox, None)
                            except Exception as e:
                                logger.debug(f"EnumWindows failed, trying alternative method: {e}")
                                # If EnumWindows fails, try direct approach
                                hwnd = win32gui.GetForegroundWindow()
                                try:
                                    text = win32gui.GetWindowText(hwnd)
                                    if "Firefox" in text:
                                        firefox_hwnd = hwnd
                                except:
                                    pass
                            
                            if firefox_hwnd:
                                # Check if Firefox window isn't already the foreground
                                if win32gui.GetForegroundWindow() != firefox_hwnd:
                                    logger.debug("Forcing Firefox as foreground window")
                                    # Activate our window and keep it on top
                                    try:
                                        win32gui.SetForegroundWindow(firefox_hwnd)
                                    except:
                                        # Alternative method if SetForegroundWindow fails
                                        ctypes.windll.user32.BringWindowToTop(firefox_hwnd)
                                
                                # ULTRA-AGGRESSIVE Alt+Tab blocking - block at system level
                                # Continuously monitor all modifier keys
                                # Monitor Alt key and immediately release it
                                if ctypes.windll.user32.GetAsyncKeyState(0x12) & 0x8000:  # Alt key
                                    # Force Alt key up multiple times to break alt+tab sequence
                                    for _ in range(3):  # Try multiple times
                                        try:
                                            # Use both methods for redundancy
                                            win32api.keybd_event(0x12, 0, win32con.KEYEVENTF_KEYUP, 0)
                                            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
                                        except:
                                            pass
                                    logger.debug("Alt key was down - forced release")
                                    
                                # Check if Tab key is down while Alt might have been pressed
                                if ctypes.windll.user32.GetAsyncKeyState(0x09) & 0x8000:  # Tab key
                                    logger.debug("Tab key was down - might be Alt+Tab attempt")
                                    # Force Tab key up
                                    try:
                                        win32api.keybd_event(0x09, 0, win32con.KEYEVENTF_KEYUP, 0)
                                    except:
                                        pass
                                    
                                    # Force focus back to Firefox window
                                    try:
                                        win32gui.SetForegroundWindow(firefox_hwnd)
                                    except:
                                        try:
                                            ctypes.windll.user32.BringWindowToTop(firefox_hwnd)
                                        except:
                                            pass
                            
                        except Exception as e:
                            # Reduce log spam by using debug level instead of error
                            logger.debug(f"Error in lock_foreground_window: {e}")
                        
                        # Faster check interval for more responsive blocking
                        time.sleep(0.02)  # 20ms check interval for more aggressive blocking
                
                # Start a background thread to ensure Firefox stays in foreground
                import threading
                self.foreground_thread = threading.Thread(target=lock_foreground_window, daemon=True)
                self.foreground_thread.start()
                
                # Create a blocking thread using SetWindowsHookEx to capture Alt+Tab
                def force_keyboard_processing():
                    # Create a message queue to process messages (required for hook to work properly)
                    msg = wintypes.MSG()
                    while True:
                        # Process any pending messages to keep the hook alive
                        if ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, win32con.PM_REMOVE):
                            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
                        time.sleep(0.01)  # Small sleep to reduce CPU usage
                
                # Start message processing thread to ensure hook works properly
                self.msg_thread = threading.Thread(target=force_keyboard_processing, daemon=True)
                self.msg_thread.start()
                
                logger.info("Alt+Tab blocking system fully initialized")
                
            except Exception as e:
                logger.error(f"Error setting up system-wide keyboard hook: {e}")
        
        except Exception as e:
            logger.error(f"Error in hide_fullscreen_notification: {e}")
    
    def go_back(self):
        """Navigate back in browser history with enhanced reliability."""
        try:
            logger.info("Go back requested")
            if hasattr(self, 'driver') and self.driver:
                try:
                    # Use JavaScript for most reliable back navigation with fallback
                    self.driver.execute_script("""
                        // Store current URL in case we need to force reload
                        let currentUrl = window.location.href;
                        let isMozilla = currentUrl.toLowerCase().includes('mozilla');
                        
                        // Try normal history navigation
                        history.back();
                        
                        // Check if navigation succeeded after a short delay
                        setTimeout(function() {
                            if (window.location.href === currentUrl || isMozilla) {
                                // Force navigation to homepage as fallback
                                window.location.href = arguments[0];
                            }
                        }, 500);
                    """, self.homepage)
                    
                    # Schedule our fixes to be reapplied after navigation
                    self.root.after(800, self.apply_javascript_fixes)
                    self.root.after(1000, self.lock_firefox_window)
                    self.root.after(1200, self.hide_fullscreen_notification)
                except Exception as e:
                    logger.error(f"Error in advanced back navigation: {e}")
                    # Force return to homepage as ultimate fallback
                    self.go_home()
        except Exception as e:
            logger.error(f"Error in go_back: {e}")
            
    def go_home(self):
        """Navigate to the homepage with enhanced reliability."""
        try:
            logger.info("Go home requested")
            if hasattr(self, 'driver') and self.driver:
                try:
                    # Use JavaScript for direct navigation
                    self.driver.execute_script("""
                        // Direct location change is most reliable
                        window.location.href = arguments[0];
                    """, self.homepage)
                    logger.info(f"Navigated to homepage via JavaScript: {self.homepage}")
                    
                    # Schedule our fixes to be reapplied after navigation
                    self.root.after(800, self.apply_javascript_fixes)
                    self.root.after(1000, self.lock_firefox_window)
                    self.root.after(1200, self.hide_fullscreen_notification)
                except Exception as e:
                    logger.error(f"Error in JavaScript homepage navigation: {e}")
                    try:
                        # Fallback to Selenium get
                        self.driver.get(self.homepage)
                        logger.info(f"Navigated to homepage via Selenium: {self.homepage}")
                    except Exception as e2:
                        logger.error(f"Error in Selenium homepage navigation: {e2}")
        except Exception as e:
            logger.error(f"Error in go_home: {e}")

def is_admin():
    """Check for admin rights."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    # Check for -y flag to auto-accept dialogs
    auto_accept = "-y" in sys.argv
    
    # If auto-accept is enabled, automatically say yes to any popups
    if auto_accept:
        # Set environment variable to signal selenium to accept any dialogs
        os.environ["SELENIUM_ACCEPT_DIALOGS"] = "true"
        
        # Monkey patch to auto-accept any tkinter dialogs
        original_showinfo = tk.messagebox.showinfo
        original_showerror = tk.messagebox.showerror
        original_showwarning = tk.messagebox.showwarning
        original_askyesno = tk.messagebox.askyesno
        
        tk.messagebox.showinfo = lambda *args, **kwargs: None
        tk.messagebox.showerror = lambda *args, **kwargs: None
        tk.messagebox.showwarning = lambda *args, **kwargs: None
        tk.messagebox.askyesno = lambda *args, **kwargs: True
        
        logger.info("Auto-accept mode enabled via -y flag")
    
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
