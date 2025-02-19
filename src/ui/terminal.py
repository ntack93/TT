import tkinter as tk
from tkinter import ttk, messagebox
from typing import Any, Optional, Set, Dict, List
import asyncio
import re
import json
import os
from datetime import datetime
import webbrowser
from PIL import Image, ImageTk
from io import BytesIO
import requests

from ..utils.ansi import ANSIParser
from ..network.telnet import TelnetManager, TelnetConfig  # Add TelnetConfig import
from .settings import SettingsManager
from ..utils.message_parser import MessageParser
from .style import StyleManager
from .chatlog import ChatlogManager  # Add this import line


class TerminalUI:
    """Main terminal interface component."""
    
    def __init__(self, master: tk.Tk, settings: Any, telnet: Any, parser: Any) -> None:
        # Initialize style manager first
        self.style_manager = StyleManager()
        
        self.master = master
        self.settings = settings
        self.telnet = telnet
        self.parser = parser
        self.chat_members: Set[str] = set()
        
        # Initialize ChatlogManager before UI components
        self.chatlog = ChatlogManager(master, settings, parser)
        
        # Load font settings
        saved_font_settings = self.load_font_settings()
        self.font_name = tk.StringVar(value=saved_font_settings.get('font_name', "Courier New"))
        self.font_size = tk.IntVar(value=saved_font_settings.get('font_size', 10))
        self.current_font_settings = {
            'font': (self.font_name.get(), self.font_size.get()),
            'fg': saved_font_settings.get('fg', 'white'),
            'bg': saved_font_settings.get('bg', 'black')
        }
        
        # Create main container with same layout as original
        self.container = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Create the main UI frame on the LEFT
        self.main_frame = ttk.Frame(self.container, name='main_frame')
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=3)
        self.container.add(self.main_frame, weight=1)
        
        # Create the Chatroom Members panel in the MIDDLE
        members_frame = ttk.LabelFrame(self.container, text="Chatroom Members")
        self.members_listbox = tk.Listbox(members_frame, height=20, width=20, exportselection=False)
        self.members_listbox.pack(fill=tk.BOTH, expand=True)
        self.container.add(members_frame, weight=0)
        
        # Create the Actions listbox on the RIGHT
        actions_frame = ttk.LabelFrame(self.container, text="Actions")
        self.actions_listbox = tk.Listbox(actions_frame, height=20, width=20, exportselection=False)
        self.actions_listbox.pack(fill=tk.BOTH, expand=True)
        self.container.add(actions_frame, weight=0)
        
        # Create top frame for controls
        top_frame = ttk.Frame(self.main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Add action buttons
        ttk.Button(top_frame, text="Wave", command=lambda: self.send_action("wave")).grid(row=0, column=0, padx=5)
        ttk.Button(top_frame, text="Smile", command=lambda: self.send_action("smile")).grid(row=0, column=1, padx=5)
        ttk.Button(top_frame, text="Dance", command=lambda: self.send_action("dance")).grid(row=0, column=2, padx=5)
        ttk.Button(top_frame, text="Bow", command=lambda: self.send_action("bow")).grid(row=0, column=3, padx=5)
        
        # Add connection settings after top_frame initialization
        self.conn_frame = ttk.LabelFrame(top_frame, text="Connection Settings")
        self.conn_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        
        # Host/Port inputs
        ttk.Label(self.conn_frame, text="BBS Host:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.host = tk.StringVar(value=settings.get('host', 'bbs.example.com'))
        self.host_entry = ttk.Entry(self.conn_frame, textvariable=self.host, width=30)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        ttk.Label(self.conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        self.port = tk.IntVar(value=settings.get('port', 23))
        self.port_entry = ttk.Entry(self.conn_frame, textvariable=self.port, width=6)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        # Connect button
        self.connect_button = ttk.Button(self.conn_frame, text="Connect", 
                                         command=self.toggle_connection, 
                                         style="Connect.TButton")
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Username/Password frames
        self.username_frame = ttk.LabelFrame(top_frame, text="Username")
        self.username_frame.grid(row=3, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        self.username = tk.StringVar(value=settings.get('username', ''))
        self.username_entry = ttk.Entry(self.username_frame, textvariable=self.username, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.remember_username = tk.BooleanVar(value=settings.get('remember_username', False))
        ttk.Checkbutton(self.username_frame, text="Remember", 
                       variable=self.remember_username).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(self.username_frame, text="Send", 
                  command=self.send_username).pack(side=tk.LEFT, padx=5, pady=5)
        
        self.password_frame = ttk.LabelFrame(top_frame, text="Password")
        self.password_frame.grid(row=4, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        self.password = tk.StringVar(value=settings.get('password', ''))
        self.password_entry = ttk.Entry(self.password_frame, textvariable=self.password, 
                                      width=30, show="*")
        self.password_entry.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.remember_password = tk.BooleanVar(value=settings.get('remember_password', False))
        ttk.Checkbutton(self.password_frame, text="Remember", 
                       variable=self.remember_password).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(self.password_frame, text="Send", 
                  command=self.send_password).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Add utility buttons
        utility_frame = ttk.Frame(self.conn_frame)
        utility_frame.grid(row=0, column=5, columnspan=4, padx=5, pady=5)
        
        ttk.Button(utility_frame, text="Favorites", command=self.show_favorites_window, 
                  style="Favorites.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(utility_frame, text="Settings", command=self.show_settings_window, 
                  style="Settings.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(utility_frame, text="Triggers", command=self.show_triggers_window, 
                  style="Triggers.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(utility_frame, text="Chatlog", 
                  command=self.chatlog.show_window, 
                  style="Chatlog.TButton").pack(side=tk.LEFT, padx=2)
        ttk.Button(utility_frame, text="Change Font",
                  command=self.show_change_font_window,
                  style="Settings.TButton").pack(side=tk.LEFT, padx=2)
        
        # Keep Alive checkbox
        self.keep_alive_enabled = tk.BooleanVar(value=settings.get('keep_alive', False))
        ttk.Checkbutton(utility_frame, text="Keep Alive", 
                       variable=self.keep_alive_enabled, 
                       command=self.toggle_keep_alive).pack(side=tk.LEFT, padx=5)
        
        # Create context menus
        self.create_context_menu(self.host_entry)
        self.create_context_menu(self.username_entry)
        self.create_context_menu(self.password_entry)
        
        # Create terminal output
        self.output_frame = ttk.LabelFrame(self.main_frame, text="BBS Output")
        self.output_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.output_frame.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)

        # Create paned window for output and directed messages
        self.output_paned = ttk.PanedWindow(self.output_frame, orient=tk.VERTICAL)
        self.output_paned.grid(row=0, column=0, sticky="nsew")
        
        # Main terminal display
        terminal_frame = ttk.Frame(self.output_paned)
        self.terminal_display = tk.Text(
            terminal_frame,
            wrap=tk.WORD,
            bg="black",
            fg="white",
            font=("Courier New", 10)
        )
        self.terminal_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar for terminal
        terminal_scroll = ttk.Scrollbar(terminal_frame, command=self.terminal_display.yview)
        terminal_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_display.configure(yscrollcommand=terminal_scroll.set)
        
        # Add terminal frame to paned window
        self.output_paned.add(terminal_frame, weight=3)
        
        # Messages to You frame
        messages_frame = ttk.LabelFrame(self.output_paned, text="Messages to You")
        self.directed_msg_display = tk.Text(
            messages_frame,
            wrap=tk.WORD,
            height=6,
            bg="black",
            fg="white",
            font=("Courier New", 10)
        )
        self.directed_msg_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar for directed messages
        messages_scroll = ttk.Scrollbar(messages_frame, command=self.directed_msg_display.yview)
        messages_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.directed_msg_display.configure(yscrollcommand=messages_scroll.set)
        
        # Add messages frame to paned window
        self.output_paned.add(messages_frame, weight=1)
        
        # Initialize ANSI tags
        self.parser.ansi.configure_tags(self.terminal_display)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.output_frame, command=self.terminal_display.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.terminal_display.configure(yscrollcommand=scrollbar.set)
        
        # Create input area
        input_frame = ttk.LabelFrame(self.main_frame, text="Send Message")
        input_frame.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        input_frame.columnconfigure(0, weight=1)  # Make input field expand horizontally
        self.input_var = tk.StringVar()
        self.input = ttk.Entry(input_frame, textvariable=self.input_var)
        self.input.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.input.bind("<Return>", self.send_message)  # Bind Enter key
        
        # Add Send button
        self.send_button = ttk.Button(input_frame, text="Send", 
                                    command=lambda: self.send_message(None))
        self.send_button.grid(row=0, column=1, padx=5, pady=5)
        
        # Additional instance variables
        self.favorites: List[str] = self.load_favorites()
        self.triggers: List[Dict[str, str]] = self.load_triggers()
        self.preview_window: Optional[tk.Toplevel] = None
        
        # Add checkboxes for visibility
        self.show_connection_settings = tk.BooleanVar(value=True)
        self.show_username = tk.BooleanVar(value=True) 
        self.show_password = tk.BooleanVar(value=True)
        self.show_all = tk.BooleanVar(value=True)
        
        # Additional frames
        self.favorites_window: Optional[tk.Toplevel] = None
        self.triggers_window: Optional[tk.Toplevel] = None
        self.chatlog_window: Optional[tk.Toplevel] = None
        
        # Build additional UI components
        self._build_favorites_ui()
        self._build_triggers_ui()
        self._build_chatlog_ui()
        
        # Load settings
        self.load_settings()
        
    def _build_favorites_ui(self) -> None:
        """Create favorites management UI components."""
        favorites_frame = ttk.LabelFrame(self.container, text="Favorites")
        # ...implement favorites UI based on HTML reference...
        
    def _build_triggers_ui(self) -> None:
        """Create triggers management UI components."""
        triggers_frame = ttk.LabelFrame(self.container, text="Triggers")
        # ...implement triggers UI based on HTML reference...
        
    def _build_chatlog_ui(self) -> None:
        """Create chatlog UI components."""
        chatlog_frame = ttk.LabelFrame(self.container, text="Chatlog")
        # ...implement chatlog UI based on HTML reference...
        
    def load_settings(self) -> None:
        """Load all settings from files."""
        self.load_favorites()
        self.load_triggers()
        self.load_font_settings()
        
    def load_favorites(self) -> List[str]:
        """Load favorites from file."""
        try:
            if os.path.exists("favorites.json"):
                with open("favorites.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading favorites: {e}")
        return []

    def save_favorites(self) -> None:
        """Save favorites to file."""
        try:
            with open("favorites.json", "w") as f:
                json.dump(self.favorites, f)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def load_triggers(self) -> List[Dict[str, str]]:
        """Load triggers from a local file or initialize empty list."""
        try:
            if os.path.exists("triggers.json"):
                with open("triggers.json", "r") as file:
                    return json.load(file)
        except Exception as e:
            print(f"Error loading triggers: {e}")
        return []

    def save_triggers(self) -> None:
        """Save triggers to local file."""
        try:
            with open("triggers.json", "w") as file:
                json.dump(self.triggers, file)
        except Exception as e:
            print(f"Error saving triggers: {e}")

    def load_font_settings(self) -> Dict[str, Any]:
        """Load font settings from a local file or return defaults."""
        try:
            if os.path.exists("font_settings.json"):
                with open("font_settings.json", "r") as file:
                    return json.load(file)
        except Exception as e:
            print(f"Error loading font settings: {e}")
        return {
            'font_name': "Courier New",
            'font_size': 10,
            'fg': 'white',
            'bg': 'black'
        }

    def save_font_settings(self, settings: Dict[str, Any]) -> None:
        """Save font settings to file."""
        try:
            with open("font_settings.json", "w") as file:
                json.dump(settings, file)
        except Exception as e:
            print(f"Error saving font settings: {e}")

    def check_triggers(self, message: str) -> None:
        """Check incoming messages for triggers and send automated response."""
        for trigger in self.triggers:
            if trigger.get('trigger', '').lower() in message.lower():
                response = trigger.get('response', '')
                if response:
                    self.send_custom_message(response)

    def send_custom_message(self, message: str) -> None:
        """Send a custom message (for trigger responses)."""
        if self.telnet:
            self.telnet.send(message + "\r\n")

    def refresh_chat_members(self) -> None:
        """Refresh the chat members display."""
        self.members_listbox.delete(0, tk.END)
        for member in sorted(self.chat_members):
            self.members_listbox.insert(tk.END, member)
        # Schedule next refresh
        self.master.after(5000, self.refresh_chat_members)
        
    def update_chat_members(self, members: Set[str]) -> None:
        """Update the chat members list."""
        self.chat_members = members
        self.refresh_chat_members()
        
    def append_text(self, text: str) -> None:
        """Add text to the terminal display with ANSI processing."""
        self.terminal_display.configure(state=tk.NORMAL)
        self.parser.ansi.insert_with_tags(self.terminal_display, text)
        self.terminal_display.see(tk.END)
        self.terminal_display.configure(state=tk.DISABLED)

    def send_message(self, event: Optional[tk.Event] = None) -> None:
        """Send message from input field."""
        if not self.telnet or not self.telnet.connected:
            return

        message = self.input_var.get().strip()
        self.input_var.set("")  # Clear input field
        
        if message:
            # Ensure proper string formatting
            formatted_message = str(message).strip()
            self.telnet.send_sync(formatted_message)
        else:
            # If empty, just send an Enter keystroke
            self.telnet.send_sync("\r\n")

    def send_action(self, action: str) -> None:
        """Send an action command."""
        if not self.telnet:
            return

        # Get selected member if any
        selected = self.members_listbox.curselection()
        if selected:
            username = self.members_listbox.get(selected[0])
            action = f"{action} {username}"
            
        # Use send_sync instead of send
        self.telnet.send_sync(action + "\r\n")

    def toggle_connection(self) -> None:
        """Toggle the telnet connection on/off."""
        if self.telnet.connected:
            self.disconnect()
            self.connect_button.configure(text="Connect", style="Connect.TButton")
        else:
            self.connect()
            self.connect_button.configure(text="Disconnect", style="Disconnect.TButton")

    def connect(self) -> None:
        """Establish connection to the BBS."""
        host = self.host.get()
        port = self.port.get()
        
        async def start_connection():
            try:
                config = TelnetConfig(
                    host=host,
                    port=port,
                    term_type="ansi",
                    encoding="cp437",
                    cols=136,
                    rows=50
                )
                await self.telnet.connect(config)
                # Update button state in main thread
                self.master.after(0, lambda: self.connect_button.configure(
                    text="Disconnect", 
                    style="Disconnect.TButton"
                ))
                self.append_text(f"Connected to {host}:{port}\n")
            except Exception as e:
                self.append_text(f"Connection failed: {e}\n")
                # Reset button state in main thread
                self.master.after(0, lambda: self.connect_button.configure(
                    text="Connect", 
                    style="Connect.TButton"
                ))

        asyncio.run_coroutine_threadsafe(start_connection(), self.telnet.loop)

    def disconnect(self) -> None:
        """Disconnect from the BBS."""
        if self.telnet:
            async def stop_connection():
                await self.telnet.disconnect()
                self.append_text("Disconnected from BBS.\n")
            
            asyncio.run_coroutine_threadsafe(stop_connection(), self.telnet.loop)
            self.chat_members.clear()
            self.refresh_chat_members()
            
    def send_username(self) -> None:
        """Send the username to the BBS."""
        if self.telnet and self.telnet.connected:
            message = self.username.get() + "\r\n"
            self.telnet.send_sync(message)
            
            # Save credentials immediately when checkbox is checked
            if self.remember_username.get():
                self.settings.set('username', self.username.get())
                self.settings.set('remember_username', True)
                self.settings.save_settings()  # Force save to disk
            
    def send_password(self) -> None:
        """Send the password to the BBS."""
        if self.telnet and self.telnet.connected:
            message = self.password.get() + "\r\n"
            self.telnet.send_sync(message)
            
            # Save credentials immediately when checkbox is checked
            if self.remember_password.get():
                self.settings.set('password', self.password.get())
                self.settings.set('remember_password', True)
                self.settings.save_settings()  # Force save to disk
            
    def clear_credentials(self) -> None:
        """Clear saved username and password."""
        self.settings.set('username', '')
        self.settings.set('password', '')
        self.settings.set('remember_username', False)
        self.settings.set('remember_password', False)
        self.username.set('')
        self.password.set('')
        
    def show_favorites_window(self) -> None:
        """Open a window to manage favorite BBS addresses."""
        if self.favorites_window and self.favorites_window.winfo_exists():
            self.favorites_window.lift()
            self.favorites_window.focus_force()
            return

        self.favorites_window = tk.Toplevel(self.master)
        self.favorites_window.title("Favorite BBS Addresses")
        self.favorites_window.transient(self.master)
        self.favorites_window.grab_set()
        
        # Favorites listbox
        favorites_frame = ttk.Frame(self.favorites_window)
        favorites_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.favorites_listbox = tk.Listbox(favorites_frame, height=10, width=50)
        self.favorites_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.update_favorites_listbox()
        
        # Add new favorite
        add_frame = ttk.Frame(self.favorites_window)
        add_frame.pack(fill=tk.X, padx=5, pady=5)

        self.new_favorite_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_favorite_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_frame, text="Add", command=self.add_favorite).pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(self.favorites_window)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(button_frame, text="Remove", command=self.remove_favorite).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Use Selected", command=self.use_selected_favorite).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.favorites_window.destroy).pack(side=tk.RIGHT, padx=5)
        
    def update_favorites_listbox(self) -> None:
        """Update the favorites listbox with current favorites."""
        if not hasattr(self, 'favorites_listbox'):
            return
        self.favorites_listbox.delete(0, tk.END)
        for favorite in self.favorites:
            self.favorites_listbox.insert(tk.END, favorite)
            
    def add_favorite(self) -> None:
        """Add a new favorite BBS address."""
        new_address = self.new_favorite_var.get().strip()
        if new_address and new_address not in self.favorites:
            self.favorites.append(new_address)
            self.save_favorites()
            self.update_favorites_listbox()
            self.new_favorite_var.set("")
            
    def remove_favorite(self) -> None:
        """Remove the selected favorite address."""
        selection = self.favorites_listbox.curselection()
        if selection:
            index = selection[0]
            address = self.favorites_listbox.get(index)
            self.favorites.remove(address)
            self.save_favorites()
            self.update_favorites_listbox()
            
    def use_selected_favorite(self) -> None:
        """Use the selected favorite address."""
        selection = self.favorites_listbox.curselection()
        if selection:
            address = self.favorites_listbox.get(selection[0])
            if ':' in address:
                host, port = address.split(':')
                self.host.set(host)
                self.port.set(int(port))
            else:
                self.host.set(address)
            self.favorites_window.destroy()

    def show_settings_window(self) -> None:
        """Display settings configuration window."""
        settings_window = tk.Toplevel(self.master)
        settings_window.title("Settings")
        settings_window.grab_set()  # Make window modal
        settings_window.transient(self.master)
        
        # Create frames
        row = 0
        
        # Font settings
        ttk.Label(settings_window, text="Font:").grid(row=row, column=0, padx=5, pady=5)
        font_var = tk.StringVar(value=self.font_name.get())
        font_options = [
            "Courier New", "Consolas", "Terminal", "Fixedsys", "System",
            "Modern DOS 8x16", "Modern DOS 8x8", "Perfect DOS VGA 437",
            "MS Gothic", "SimSun-ExtB", "NSimSun", "Lucida Console",
            "OCR A Extended", "Prestige Elite Std", "Letter Gothic Std",
            "FreeMono", "DejaVu Sans Mono", "Liberation Mono", "IBM Plex Mono",
            "PT Mono", "Share Tech Mono", "VT323", "Press Start 2P", "DOS/V",
            "TerminalVector"
        ]
        ttk.Combobox(settings_window, textvariable=font_var, values=font_options, state="readonly").grid(
            row=row, column=1, padx=5, pady=5)
        row += 1
        
        # Font size
        ttk.Label(settings_window, text="Font Size:").grid(row=row, column=0, padx=5, pady=5)
        size_var = tk.IntVar(value=self.font_size.get())
        ttk.Entry(settings_window, textvariable=size_var, width=5).grid(row=row, column=1, padx=5, pady=5)
        row += 1
        
        # Auto-login settings
        auto_login_var = tk.BooleanVar(value=self.settings.get('auto_login', False))
        ttk.Checkbutton(settings_window, text="Auto Login", 
                       variable=auto_login_var).grid(row=row, column=0, columnspan=2, pady=5)
        row += 1
        
        # Keep alive interval
        ttk.Label(settings_window, text="Keep Alive Interval (s):").grid(row=row, column=0, padx=5, pady=5)
        keep_alive_var = tk.IntVar(value=self.settings.get('keep_alive_interval', 60))
        ttk.Entry(settings_window, textvariable=keep_alive_var, width=5).grid(row=row, column=1, padx=5, pady=5)
        row += 1
        
        # Save button
        def save_settings():
            self.font_name.set(font_var.get())
            self.font_size.set(size_var.get())
            self.settings.set('auto_login', auto_login_var.get())
            self.settings.set('keep_alive_interval', keep_alive_var.get())
            # Update current font settings
            self.current_font_settings = {
                'font': (self.font_name.get(), self.font_size.get()),
                'fg': self.current_font_settings.get('fg', 'white'),
                'bg': self.current_font_settings.get('bg', 'black')
            }
            # Update displays
            self.update_display_font()
            
            # Save to file
            self.save_font_settings(self.current_font_settings)
            settings_window.destroy()
            
        ttk.Button(settings_window, text="Save", command=save_settings).grid(
            row=row, column=0, columnspan=2, pady=10)

    def update_display_font(self) -> None:
        """Update font settings for all text displays."""
        try:
            font_settings = {
                'font': (self.font_name.get(), self.font_size.get())
            }
            self.terminal_display.configure(**font_settings)
            self.members_listbox.configure(**font_settings)
            self.actions_listbox.configure(**font_settings)
        except Exception as e:
            print(f"Error updating display font: {e}")

    def show_triggers_window(self) -> None:
        """Open a window to manage trigger/response pairs."""
        if self.triggers_window and self.triggers_window.winfo_exists():
            self.triggers_window.lift()
            self.triggers_window.focus_force()
            return

        self.triggers_window = tk.Toplevel(self.master)
        self.triggers_window.title("Automation Triggers")
        self.triggers_window.transient(self.master)
        self.triggers_window.grab_set()
        
        # Create main frame
        triggers_frame = ttk.Frame(self.triggers_window, padding="5")
        triggers_frame.pack(fill=tk.BOTH, expand=True)
        
        # Column headers
        ttk.Label(triggers_frame, text="Trigger").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(triggers_frame, text="Response").grid(row=0, column=1, padx=5, pady=5)

        # Create vars for entries
        self.trigger_vars = []
        self.response_vars = []

        # Create 10 rows of trigger/response pairs
        for i in range(10):
            trigger_var = tk.StringVar(value=self.triggers[i]['trigger'] if i < len(self.triggers) else "")
            response_var = tk.StringVar(value=self.triggers[i]['response'] if i < len(self.triggers) else "")
            
            self.trigger_vars.append(trigger_var)
            self.response_vars.append(response_var)
            
            ttk.Entry(triggers_frame, textvariable=trigger_var, width=30).grid(
                row=i+1, column=0, padx=5, pady=2)
            ttk.Entry(triggers_frame, textvariable=response_var, width=40).grid(
                row=i+1, column=1, padx=5, pady=2)
            
        # Buttons at bottom
        button_frame = ttk.Frame(triggers_frame)
        button_frame.grid(row=11, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_trigger_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=self.triggers_window.destroy).pack(side=tk.LEFT, padx=5)

    def save_trigger_changes(self) -> None:
        """Save changes made in the triggers window."""
        self.triggers = []
        for trigger_var, response_var in zip(self.trigger_vars, self.response_vars):
            trigger = trigger_var.get().strip()
            response = response_var.get().strip()
            if trigger or response:  # Only save non-empty pairs
                self.triggers.append({
                    'trigger': trigger,
                    'response': response
                })
        self.save_triggers()
        self.triggers_window.destroy()

    def toggle_keep_alive(self) -> None:
        """Toggle the keep-alive functionality."""
        if self.keep_alive_enabled.get():
            self.start_keep_alive()
            self.settings.set('keep_alive', True)
        else:
            self.stop_keep_alive()
            self.settings.set('keep_alive', False)

    def start_keep_alive(self) -> None:
        """Start the keep-alive task."""
        if self.telnet and self.telnet.connected:
            interval = self.settings.get('keep_alive_interval', 60)
            self.telnet.start_keep_alive(interval)

    def stop_keep_alive(self) -> None:
        """Stop the keep-alive task."""
        if self.telnet:
            self.telnet.stop_keep_alive()

    def create_context_menu(self, widget: tk.Widget) -> None:
        """Create a right-click context menu for text widgets."""
        menu = tk.Menu(widget, tearoff=0)
        
        # Add standard edit operations
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))
        
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
            return "break"  # Prevent default right-click behavior

        # Bind right-click to show menu
        widget.bind("<Button-3>", show_menu)

    def create_members_context_menu(self) -> None:
        """Create a right-click context menu for the members listbox."""
        menu = tk.Menu(self.members_listbox, tearoff=0)
        menu.add_command(label="Send PM", command=self.send_pm_to_selected)
        menu.add_command(label="View Chat History", command=self.view_chat_history)
        menu.add_separator()
        menu.add_command(label="Copy Username", command=self.copy_selected_username)
        
        def show_menu(event):
            if self.members_listbox.curselection():  # Only show if an item is selected
                menu.tk_popup(event.x_root, event.y_root)
            return "break"
        
        self.members_listbox.bind("<Button-3>", show_menu)

    def send_pm_to_selected(self) -> None:
        """Send a private message to the selected user."""
        selection = self.members_listbox.curselection()
        if selection:
            username = self.members_listbox.get(selection[0])
            self.input_var.set(f"/msg {username} ")
            self.input.focus()
            
    def view_chat_history(self) -> None:
        """View chat history for the selected user."""
        selection = self.members_listbox.curselection()
        if selection:
            username = self.members_listbox.get(selection[0])
            self.show_chatlog_window()
            self.select_chatlog_user(username)
            
    def copy_selected_username(self) -> None:
        """Copy the selected username to clipboard."""
        selection = self.members_listbox.curselection()
        if selection:
            username = self.members_listbox.get(selection[0])
            self.master.clipboard_clear()
            self.master.clipboard_append(username)
            
    def define_ansi_tags(self) -> None:
        """Define text tags for ANSI colors and attributes."""
        # Standard colors
        colors = {
            'black': '#000000', 'red': '#AA0000', 'green': '#00AA00',
            'yellow': '#AA5500', 'blue': '#0000AA', 'magenta': '#AA00AA',
            'cyan': '#00AAAA', 'white': '#AAAAAA',
            # Bright colors
            'gray': '#555555', 'brightred': '#FF5555', 'brightgreen': '#55FF55',
            'brightyellow': '#FFFF55', 'brightblue': '#5555FF',
            'brightmagenta': '#FF55FF', 'brightcyan': '#55FFFF',
            'brightwhite': '#FFFFFF'
        }
        
        # Configure color tags
        for name, color in colors.items():
            self.terminal_display.tag_configure(f'fg_{name}', foreground=color)
            self.terminal_display.tag_configure(f'bg_{name}', background=color)
            
        # Configure attribute tags
        self.terminal_display.tag_configure('bold',
            font=(self.font_name.get(), self.font_size.get(), 'bold'))
        self.terminal_display.tag_configure('underline', underline=1)
        self.terminal_display.tag_configure('reverse', background='white',
                                          foreground='black')
        self.terminal_display.tag_configure('blink', background='yellow')

    def parse_ansi_and_insert(self, text: str) -> None:
        """Parse ANSI escape sequences and insert text with appropriate tags."""
        self.terminal_display.configure(state=tk.NORMAL)
        
        # Split on ANSI escape sequences
        parts = re.split('(\x1b\\[[0-9;]*m)', text)
        
        current_tags = set()
        
        for part in parts:
            if part.startswith('\x1b['):
                # Parse ANSI sequence
                codes = part[2:-1].split(';')
                if '0' in codes:
                    current_tags.clear()
                for code in codes:
                    if code in ['1', '4', '7']:  # Bold, Underline, Reverse
                        if code == '1':
                            current_tags.add('bold')
                        elif code == '4':
                            current_tags.add('underline')
                        elif code == '7':
                            current_tags.add('reverse')
                    elif code.startswith(('3', '9')):  # Foreground colors
                        current_tags.add(f'color_{code}')
                    elif code.startswith(('4', '10')):  # Background colors
                        current_tags.add(f'bg_color_{code}')
            else:
                # Insert text with current tags
                if current_tags:
                    self.terminal_display.insert(tk.END, part, tuple(current_tags))
                else:
                    self.terminal_display.insert(tk.END, part)
                    
        self.terminal_display.see(tk.END)
        self.terminal_display.configure(state=tk.DISABLED)

    def show_change_font_window(self) -> None:
        """Open window to change font settings."""
        font_window = tk.Toplevel(self.master)
        font_window.title("Change Font Settings")
        font_window.geometry("800x600")
        font_window.grab_set()
        font_window.attributes('-topmost', True)

        # Store current selections
        self.current_selections = {
            'font': None,
            'size': None,
            'color': None,
            'bg': None
        }

        main_frame = ttk.Frame(font_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Font selection
        font_frame = self._create_font_selection(main_frame)
        font_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        
        # Size selection  
        size_frame = self._create_size_selection(main_frame)
        size_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        
        # Color selection
        color_frame = self._create_color_selection(main_frame)
        color_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        
        # Background selection
        bg_frame = self._create_bg_selection(main_frame)
        bg_frame.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        ttk.Button(button_frame, text="Save", 
                  command=lambda: self._save_font_settings(font_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", 
                  command=font_window.destroy).pack(side=tk.LEFT, padx=5)

        # Set initial selections
        self._set_initial_font_selections()

    def _create_font_selection(self, parent: ttk.Frame) -> ttk.LabelFrame:
        """Create font selection frame."""
        frame = ttk.LabelFrame(parent, text="Font")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.font_listbox = tk.Listbox(frame, exportselection=False)
        self.font_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        scroll = ttk.Scrollbar(frame, command=self.font_listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.font_listbox.configure(yscrollcommand=scroll.set)

        fonts = [
            "Courier New", "Consolas", "Terminal", "Fixedsys", "System",
            "Modern DOS 8x16", "Modern DOS 8x8", "Perfect DOS VGA 437",
            "MS Gothic", "SimSun-ExtB", "NSimSun", "Lucida Console",
            "OCR A Extended", "Prestige Elite Std", "Letter Gothic Std",
            "FreeMono", "DejaVu Sans Mono", "Liberation Mono", "IBM Plex Mono",
            "PT Mono", "Share Tech Mono", "VT323", "Press Start 2P", "DOS/V",
            "TerminalVector"
        ]
        
        for font in fonts:
            self.font_listbox.insert(tk.END, font)
            
        self.font_listbox.bind('<<ListboxSelect>>', 
                              lambda e: self._update_selection(e, 'font'))
        
        return frame

    def _create_size_selection(self, parent: ttk.Frame) -> ttk.LabelFrame:
        """Create size selection frame."""
        frame = ttk.LabelFrame(parent, text="Size")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.size_listbox = tk.Listbox(frame, exportselection=False)
        self.size_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        scroll = ttk.Scrollbar(frame, command=self.size_listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.size_listbox.configure(yscrollcommand=scroll.set)

        sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36]
        for size in sizes:
            self.size_listbox.insert(tk.END, size)
            
        self.size_listbox.bind('<<ListboxSelect>>', 
                              lambda e: self._update_selection(e, 'size'))
        
        return frame

    def _create_color_selection(self, parent: ttk.Frame) -> ttk.LabelFrame:
        """Create color selection frame."""
        frame = ttk.LabelFrame(parent, text="Font Color")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.color_listbox = tk.Listbox(frame, exportselection=False)
        self.color_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        scroll = ttk.Scrollbar(frame, command=self.color_listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.color_listbox.configure(yscrollcommand=scroll.set)

        colors = ["black", "white", "red", "green", "blue", "yellow", 
                 "magenta", "cyan", "gray70", "gray50", "gray30", 
                 "orange", "purple", "brown", "pink"]
                 
        for color in colors:
            self.color_listbox.insert(tk.END, color)
            self.color_listbox.itemconfigure(colors.index(color), {'bg': color})
            
        self.color_listbox.bind('<<ListboxSelect>>', 
                               lambda e: self._update_selection(e, 'color'))
        
        return frame

    def _create_bg_selection(self, parent: ttk.Frame) -> ttk.LabelFrame:
        """Create background selection frame."""
        frame = ttk.LabelFrame(parent, text="Background Color")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.bg_listbox = tk.Listbox(frame, exportselection=False)
        self.bg_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        scroll = ttk.Scrollbar(frame, command=self.bg_listbox.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.bg_listbox.configure(yscrollcommand=scroll.set)

        bg_colors = ["white", "black", "gray90", "gray80", "gray70", 
                    "lightyellow", "lightblue", "lightgreen", 
                    "azure", "ivory", "honeydew", "lavender"]
                    
        for bg in bg_colors:
            self.bg_listbox.insert(tk.END, bg)
            self.bg_listbox.itemconfigure(bg_colors.index(bg), {'bg': bg})
            
        self.bg_listbox.bind('<<ListboxSelect>>', 
                            lambda e: self._update_selection(e, 'bg'))
        
        return frame

    def _update_selection(self, event: tk.Event, category: str) -> None:
        """Update current selection for a category."""
        widget = event.widget
        try:
            selection = widget.get(widget.curselection())
            self.current_selections[category] = selection
        except (tk.TclError, TypeError):
            pass

    def _set_initial_font_selections(self) -> None:
        """Set initial selections in font settings window."""
        try:
            # Get current font settings from chatlog file first
            try:
                with open("chatlog_font_settings.json", "r") as f:
                    saved = json.load(f)
                    current_font = saved.get('font_name', "Courier New")
                    current_size = saved.get('font_size', 10)
                    current_fg = saved.get('fg', 'white')
                    current_bg = saved.get('bg', 'black')
            except (FileNotFoundError, json.JSONDecodeError):
                # If no saved settings, use current terminal display settings
                font_str = self.terminal_display.cget("font")
                if isinstance(font_str, str):
                    # Handle string format like "Courier New 10"
                    parts = font_str.split()
                    current_font = " ".join(parts[:-1])  # Everything except last part
                    current_size = int(parts[-1])  # Last part is size
                else:
                    # Handle tuple format like ("Courier New", 10)
                    current_font, current_size = font_str
                current_fg = self.terminal_display.cget("fg")
                current_bg = self.terminal_display.cget("bg")
            
            # Initialize current selections
            self.current_selections = {
                'font': current_font,
                'size': current_size,
                'color': current_fg,
                'bg': current_bg
            }
            
            # Select current values in listboxes
            for listbox, value in [
                (self.font_listbox, current_font),
                (self.size_listbox, current_size),
                (self.color_listbox, current_fg),
                (self.bg_listbox, current_bg)
            ]:
                try:
                    index = list(map(str, listbox.get(0, tk.END))).index(str(value))
                    listbox.selection_clear(0, tk.END)
                    listbox.selection_set(index)
                    listbox.see(index)
                except ValueError:
                    pass  # Value not in list, skip selection
            
        except Exception as e:
            print(f"Error setting initial font selections: {e}")
            # Use defaults if there's an error
            self.current_selections = {
                'font': "Courier New",
                'size': 10,
                'color': 'white',
                'bg': 'black'
            }

    def _save_font_settings(self, window: tk.Toplevel) -> None:
        """Save and apply font settings."""
        try:
            if not all(self.current_selections.values()):
                messagebox.showerror("Error", "Please select an option from each list")
                return
                
            # Create font settings
            font_settings = {
                'font': (self.current_selections['font'], self.current_selections['size']),
                'fg': self.current_selections['color'],
                'bg': self.current_selections['bg']
            }
            
            # Apply settings to chat UI components
            for widget in (self.members_listbox, self.actions_listbox):
                widget.configure(**font_settings)
            
            # Apply to chatlog UI
            if self.chatlog:
                self.chatlog.update_font_settings(font_settings)
            
            # Store settings
            self.current_font_settings = font_settings
            
            # Save to file
            settings_to_save = {
                'font_name': self.current_selections['font'],
                'font_size': self.current_selections['size'],
                'fg': self.current_selections['color'],
                'bg': self.current_selections['bg']
            }
            
            with open("chatlog_font_settings.json", "w") as f:
                json.dump(settings_to_save, f)
            
            window.destroy()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error applying settings: {str(e)}")


