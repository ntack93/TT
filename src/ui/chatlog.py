import tkinter as tk
from tkinter import ttk
from typing import Any, Dict, List, Optional
from datetime import datetime

class ChatlogManager:
    """Manages chat logs and message history."""
    
    def __init__(self, master: tk.Tk, settings: Any, parser: Any) -> None:
        self.master = master
        self.settings = settings
        self.parser = parser
        self.chatlog_window: Optional[tk.Toplevel] = None
        
    def show_chatlog_window(self) -> None:
        """Show the chatlog window."""
        if self.chatlog_window and self.chatlog_window.winfo_exists():
            self.chatlog_window.lift()
            self.chatlog_window.focus_force()
            return
            
        self.chatlog_window = tk.Toplevel(self.master)
        self.chatlog_window.title("Chat History")
        self.chatlog_window.geometry("800x600")
        
        # Create main container
        main_paned = ttk.PanedWindow(self.chatlog_window, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Users list
        users_frame = ttk.LabelFrame(main_paned, text="Users")
        self.users_list = tk.Listbox(users_frame)
        self.users_list.pack(fill=tk.BOTH, expand=True)
        main_paned.add(users_frame)
        
        # Messages area
        messages_frame = ttk.LabelFrame(main_paned, text="Messages")
        self.messages_text = tk.Text(messages_frame, wrap=tk.WORD)
        self.messages_text.pack(fill=tk.BOTH, expand=True)
        main_paned.add(messages_frame)
        
        # Load initial data
        self.load_users()
        
    def load_users(self) -> None:
        """Load users from settings/persistence."""
        self.users_list.delete(0, tk.END)
        for user in self.settings.get_users():
            self.users_list.insert(tk.END, user)
            
    def process_message(self, message: Dict[str, Any]) -> None:
        """Process and store a new message."""
        if not message:
            return
            
        sender = message.get('sender')
        content = message.get('content')
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        
        if sender and content:
            self.settings.add_message(sender, {
                'timestamp': timestamp,
                'content': content
            })
