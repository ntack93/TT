from typing import Dict, Any
import tkinter as tk
from tkinter import ttk
import json
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
    """Manages application settings and configuration."""
    
    def __init__(self, master: tk.Tk, persistence: Any) -> None:
        """Initialize settings manager.
        
        Args:
            master: Root window
            persistence: Persistence manager instance
        """
        self.master = master
        self.persistence = persistence
        self.settings_window = None
        self.config = self.load_settings()
        
    def show_settings_window(self) -> None:
        """Display the settings configuration window."""
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            return
            
        self.settings_window = tk.Toplevel(self.master)
        self.settings_window.title("Settings")
        self.settings_window.grab_set()
        
        # Font settings frame
        font_frame = ttk.LabelFrame(self.settings_window, text="Font Settings")
        font_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Font name
        ttk.Label(font_frame, text="Font:").grid(row=0, column=0, padx=5, pady=5)
        font_var = tk.StringVar(value=self.config.font_name)
        font_entry = ttk.Entry(font_frame, textvariable=font_var)
        font_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Font size
        ttk.Label(font_frame, text="Size:").grid(row=1, column=0, padx=5, pady=5)
        size_var = tk.IntVar(value=self.config.font_size)
        size_entry = ttk.Entry(font_frame, textvariable=size_var)
        size_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Automation frame
        auto_frame = ttk.LabelFrame(self.settings_window, text="Automation")
        auto_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Checkboxes
        logon_var = tk.BooleanVar(value=self.config.logon_automation)
        ttk.Checkbutton(auto_frame, text="Logon Automation", 
                       variable=logon_var).pack(padx=5, pady=2)
        
        auto_login_var = tk.BooleanVar(value=self.config.auto_login)
        ttk.Checkbutton(auto_frame, text="Auto Login", 
                       variable=auto_login_var).pack(padx=5, pady=2)
        
        keep_alive_var = tk.BooleanVar(value=self.config.keep_alive)
        ttk.Checkbutton(auto_frame, text="Keep Alive", 
                       variable=keep_alive_var).pack(padx=5, pady=2)
        
        mud_mode_var = tk.BooleanVar(value=self.config.mud_mode)
        ttk.Checkbutton(auto_frame, text="MUD Mode", 
                       variable=mud_mode_var).pack(padx=5, pady=2)
        
        # Save button
        def save_settings():
            self.config = SettingsConfig(
                font_name=font_var.get(),
                font_size=size_var.get(),
                logon_automation=logon_var.get(),
                auto_login=auto_login_var.get(),
                keep_alive=keep_alive_var.get(),
                mud_mode=mud_mode_var.get()
            )
            self.save_settings()
            self.settings_window.destroy()
            
        ttk.Button(self.settings_window, text="Save", 
                  command=save_settings).pack(pady=10)
                  
    def load_settings(self) -> SettingsConfig:
        """Load settings from persistence."""
        data = self.persistence.load_json('settings.json', {})
        return SettingsConfig(**data)
        
    def save_settings(self) -> None:
        """Save current settings to persistence."""
        self.persistence.save_json(vars(self.config), 'settings.json')
        
    def get_terminal_config(self) -> Dict[str, Any]:
        """Get terminal display configuration.
        
        Returns:
            Dictionary of terminal config settings
        """
        return {
            'font': (self.config.font_name, self.config.font_size),
            'bg': 'black',
            'fg': 'white',
            'insertbackground': 'white'
        }
