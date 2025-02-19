import tkinter as tk
from tkinter import ttk
import json
import os
from typing import Any, Dict, Optional
from dataclasses import dataclass

@dataclass
class SettingsConfig:
    """Configuration settings container."""
    font_name: str = "Courier New"
    font_size: int = 10
    logon_automation: bool = False
    auto_login: bool = False
    keep_alive: bool = False
    mud_mode: bool = False

class SettingsManager:
    """Manages application settings and preferences."""
    
    def __init__(self, master: tk.Tk, persistence: Any = None) -> None:
        self.master = master
        self.persistence = persistence
        self.settings: Dict[str, Any] = self.load_settings()
        
        # Default settings
        self.defaults = {
            'host': 'bbs.example.com',
            'port': 23,
            'username': '',
            'password': '',
            'remember_username': False,
            'remember_password': False,
            'keep_alive': False,
            'font_name': 'Courier New',
            'font_size': 10,
            'fg_color': 'white',
            'bg_color': 'black',
            'mud_mode': False,
            'auto_login': False
        }
        
        # Initialize any missing settings with defaults
        for key, value in self.defaults.items():
            if key not in self.settings:
                self.settings[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        return self.settings.get(key, default if default is not None else self.defaults.get(key))
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value by key."""
        self.settings[key] = value
        self.save_settings()
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {}
    
    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            with open("settings.json", "w") as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def show_settings_window(self) -> None:
        """Display settings configuration window."""
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Settings")
        settings_window.grab_set()  # Make window modal
        
        # Create settings UI
        row = 0
        
        # Font settings
        ttk.Label(settings_window, text="Font:").grid(row=row, column=0, padx=5, pady=5)
        font_var = tk.StringVar(value=self.get('font_name'))
        ttk.Entry(settings_window, textvariable=font_var).grid(row=row, column=1, padx=5, pady=5)
        row += 1
        
        ttk.Label(settings_window, text="Font Size:").grid(row=row, column=0, padx=5, pady=5)
        size_var = tk.IntVar(value=self.get('font_size'))
        ttk.Entry(settings_window, textvariable=size_var).grid(row=row, column=1, padx=5, pady=5)
        row += 1
        
        # Auto-login settings
        auto_login_var = tk.BooleanVar(value=self.get('auto_login'))
        ttk.Checkbutton(settings_window, text="Auto Login", 
                       variable=auto_login_var).grid(row=row, column=0, columnspan=2, pady=5)
        row += 1
        
        # MUD mode settings
        mud_mode_var = tk.BooleanVar(value=self.get('mud_mode'))
        ttk.Checkbutton(settings_window, text="MUD Mode",
                       variable=mud_mode_var).grid(row=row, column=0, columnspan=2, pady=5)
        row += 1
        
        # Save button
        def save_settings():
            self.set('font_name', font_var.get())
            self.set('font_size', size_var.get())
            self.set('auto_login', auto_login_var.get())
            self.set('mud_mode', mud_mode_var.get())
            settings_window.destroy()
            
        ttk.Button(settings_window, text="Save",
                   command=save_settings).grid(row=row, column=0, columnspan=2, pady=10)
