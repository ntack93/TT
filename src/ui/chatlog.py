from typing import Dict, List, Optional, Any
import tkinter as tk
from tkinter import ttk, messagebox
import re
from datetime import datetime

class ChatlogManager:
    """Manages chat logging and display functionality."""
    
    def __init__(self, master: tk.Tk, persistence: Any, parser: Any) -> None:
        """Initialize chatlog manager.
        
        Args:
            master: Root window
            persistence: Persistence manager instance
            parser: Message parser instance
        """
        self.master = master
        self.persistence = persistence
        self.parser = parser
        self.chatlog_window = None
        
    def show_chatlog_window(self) -> None:
        """Display the chatlog window."""
        if self.chatlog_window and self.chatlog_window.winfo_exists():
            self.chatlog_window.lift()
            return
            
        self.chatlog_window = tk.Toplevel(self.master)
        self.chatlog_window.title("Chat History")
        self.chatlog_window.geometry("800x600")
        
        # Create paned window
        paned = ttk.PanedWindow(self.chatlog_window, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        # Users list
        users_frame = ttk.Frame(paned)
        ttk.Label(users_frame, text="Users").pack()
        self.users_list = tk.Listbox(users_frame)
        self.users_list.pack(fill=tk.BOTH, expand=True)
        paned.add(users_frame)
        
        # Messages display
        msg_frame = ttk.Frame(paned)
        ttk.Label(msg_frame, text="Messages").pack()
        self.msg_display = tk.Text(msg_frame, wrap=tk.WORD)
        self.msg_display.pack(fill=tk.BOTH, expand=True)
        paned.add(msg_frame)
        
        # Load users and bind selection
        self.load_users()
        self.users_list.bind('<<ListboxSelect>>', self.on_user_select)
        
        # Control buttons
        btn_frame = ttk.Frame(self.chatlog_window)
        btn_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(btn_frame, text="Clear History",
                  command=self.clear_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Close",
                  command=self.chatlog_window.destroy).pack(side=tk.RIGHT, padx=5)
                  
    def load_users(self) -> None:
        """Load user list from chat history."""
        chatlog = self.persistence.load_chatlog()
        self.users_list.delete(0, tk.END)
        for username in sorted(chatlog.keys()):
            self.users_list.insert(tk.END, username)
            
    def on_user_select(self, event: Optional[tk.Event] = None) -> None:
        """Handle user selection in listbox."""
        selection = self.users_list.curselection()
        if not selection:
            return
            
        username = self.users_list.get(selection[0])
        self.display_user_messages(username)
        
    def display_user_messages(self, username: str) -> None:
        """Display messages for selected user."""
        chatlog = self.persistence.load_chatlog()
        messages = chatlog.get(username, [])
        
        self.msg_display.config(state=tk.NORMAL)
        self.msg_display.delete(1.0, tk.END)
        
        for msg in messages:
            self.msg_display.insert(tk.END, f"{msg}\n")
            
        self.msg_display.config(state=tk.DISABLED)
        
    def clear_history(self) -> None:
        """Clear chat history for selected user."""
        selection = self.users_list.curselection()
        if not selection:
            return
            
        username = self.users_list.get(selection[0])
        if messagebox.askyesno("Confirm Clear",
                              f"Clear history for {username}?"):
            chatlog = self.persistence.load_chatlog()
            if username in chatlog:
                del chatlog[username]
                self.persistence.save_chatlog(chatlog)
                self.load_users()
                self.msg_display.config(state=tk.NORMAL)
                self.msg_display.delete(1.0, tk.END)
                self.msg_display.config(state=tk.DISABLED)
                
    def process_message(self, message: Any) -> None:
        """Process and store a new message.
        
        Args:
            message: Parsed message object
        """
        if not message.sender:
            return
            
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        formatted_msg = f"{timestamp} {message.raw_text}"
        
        chatlog = self.persistence.load_chatlog()
        if message.sender not in chatlog:
            chatlog[message.sender] = []
            
        chatlog[message.sender].append(formatted_msg)
        self.persistence.save_chatlog(chatlog)
        
        # Update window if open
        if (self.chatlog_window and 
            self.chatlog_window.winfo_exists() and
            self.users_list.curselection()):
            selected = self.users_list.get(self.users_list.curselection()[0])
            if selected == message.sender:
                self.display_user_messages(message.sender)
