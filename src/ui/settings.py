import tkinter as tk
from tkinter import ttk
import json
import os
from typing import Any, Dict, Optional, List
from dataclasses import dataclass
from pathlib import Path

@dataclass
class SettingsConfig:
    """Configuration settings container."""
    font_name: str = "Courier New"
    font_size: int = 10
    logon_automation: bool = False
    auto_login: bool = False
    keep_alive: bool = False
    mud_mode: bool = False
    data_dir: str = "data"
    save_path: Optional[Path] = None

class SettingsManager:
    """Manages application settings and preferences."""
    
    def __init__(self, master: tk.Tk, persistence: Any = None) -> None:
        """Initialize settings manager."""
        self.master = master
        self.persistence = persistence or {}
        
        # Initialize data directory
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Default settings - initialize first
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
        
        # Load settings after defaults are set
        self.config = SettingsConfig()
        self.config.save_path = self.data_dir / "settings.json"
        self.settings = self.load_settings()
        
        # Initialize any missing settings with defaults
        for key, value in self.defaults.items():
            if key not in self.settings:
                self.settings[key] = value
        
        # Save initialized settings
        self.save_settings()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        return self.settings.get(key, default if default is not None else self.defaults.get(key))
    
    def set(self, key: str, value: Any) -> None:
        """Set a setting value by key."""
        self.settings[key] = value
        self.save_settings()  # Save immediately when a setting changes
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        try:
            if self.config.save_path and self.config.save_path.exists():
                with open(self.config.save_path) as f:
                    loaded = json.load(f)
                    # Ensure all defaults are present
                    merged = self.defaults.copy()
                    merged.update(loaded)
                    return merged
        except Exception as e:
            print(f"Error loading settings: {e}")
        return self.defaults.copy()
    
    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            if self.config.save_path:
                self.config.save_path.parent.mkdir(exist_ok=True)
                with open(self.config.save_path, 'w') as f:
                    json.dump(self.settings, f, indent=2)
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
    
    # Delegate missing persistence methods to persistence manager if available
    def get_users(self) -> List[str]:
        """Get list of users with chat history."""
        if hasattr(self.persistence, 'get_users'):
            return self.persistence.get_users()
        return []
        
    def import_logs(self, filename: str) -> None:
        """Import chat logs."""
        if hasattr(self.persistence, 'import_logs'):
            self.persistence.import_logs(filename)
            
    def export_logs(self, filename: str) -> None:
        """Export chat logs."""
        if hasattr(self.persistence, 'export_logs'):
            self.persistence.export_logs(filename)

    def load_messages(self, username: str) -> List[Dict[str, str]]:
        """Delegate to persistence manager's load_messages."""
        if hasattr(self.persistence, 'load_messages'):
            return self.persistence.load_messages(username)
        return []

    def load_links(self, username: str) -> List[Dict[str, str]]:
        """Delegate to persistence manager's load_links."""
        if hasattr(self.persistence, 'load_links'):
            return self.persistence.load_links(username)
        return []

    def add_message(self, username: str, message: Dict[str, str]) -> None:
        """Delegate to persistence manager's add_message."""
        if hasattr(self.persistence, 'add_message'):
            self.persistence.add_message(username, message)

    def add_link(self, username: str, link: Dict[str, str]) -> None:
        """Delegate to persistence manager's add_link."""
        if hasattr(self.persistence, 'add_link'):
            self.persistence.add_link(username, link)

    def clear_user_data(self, username: str) -> None:
        """Delegate to persistence manager's clear_user_data."""
        if hasattr(self.persistence, 'clear_user_data'):
            self.persistence.clear_user_data(username)
