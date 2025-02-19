import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

from ..utils.ansi import ANSIParser
from ..network.telnet import TelnetManager
from .settings import SettingsManager
from ..utils.message_parser import MessageParser


class TerminalUI:
    """Main terminal interface component."""
    
    def __init__(self, master: tk.Tk, settings: Any, telnet: Any, parser: Any) -> None:
        self.master = master
        self.settings = settings
        self.telnet = telnet
        self.parser = parser
        
        # Create main container
        self.container = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.container.pack(fill=tk.BOTH, expand=True)
        
        # Create main frame
        self.main_frame = ttk.Frame(self.container)
        self.main_frame.columnconfigure(0, weight=1)
        self.container.add(self.main_frame, weight=1)
        
        # Create output display
        self.output_frame = ttk.LabelFrame(self.main_frame, text="BBS Output")
        self.output_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.output_frame.columnconfigure(0, weight=1)
        self.output_frame.rowconfigure(0, weight=1)
        
        self.display = tk.Text(
            self.output_frame,
            wrap=tk.WORD,
            bg="black",
            fg="white",
            font=("Courier New", 10)
        )
        self.display.grid(row=0, column=0, sticky="nsew")
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.output_frame, command=self.display.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.display.configure(yscrollcommand=scrollbar.set)
        
        # Create input area
        input_frame = ttk.Frame(self.main_frame)
        input_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        input_frame.columnconfigure(1, weight=1)
        
        self.input_var = tk.StringVar()
        self.input = ttk.Entry(input_frame, textvariable=self.input_var)
        self.input.grid(row=0, column=1, sticky="ew")
        self.input.bind("<Return>", self.send_message)
        
        # Create basic controls
        controls = ttk.Frame(self.main_frame)
        controls.grid(row=2, column=0, sticky="ew", padx=5, pady=5)
        
        self.connect_button = ttk.Button(
            controls, 
            text="Connect",
            command=self.toggle_connection
        )
        self.connect_button.pack(side=tk.LEFT, padx=5)
        
        self.connected = False
        
    def append_text(self, text: str) -> None:
        """Add text to the terminal display."""
        self.display.configure(state=tk.NORMAL)
        self.display.insert(tk.END, text)
        self.display.see(tk.END)
        self.display.configure(state=tk.DISABLED)
        
    def toggle_connection(self) -> None:
        """Toggle connection state."""
        if self.connected:
            self.telnet.disconnect()
            self.connect_button.configure(text="Connect")
            self.connected = False
        else:
            self.telnet.connect()
            self.connect_button.configure(text="Disconnect")
            self.connected = True
            
    def send_message(self, event: Optional[tk.Event] = None) -> None:
        """Send message from input field."""
        message = self.input_var.get()
        if message:
            self.telnet.send(message + "\r\n")
            self.input_var.set("")
