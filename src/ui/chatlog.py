import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Dict, Any, Optional
import json
import re
from datetime import datetime
from pathlib import Path

class ChatlogManager:
    """Manages chat history and log viewing."""
    
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
        self.window: Optional[tk.Toplevel] = None
        
        # Component references
        self.user_list: Optional[tk.Listbox] = None
        self.messages_text: Optional[tk.Text] = None
        self.links_text: Optional[tk.Text] = None
        self.paned: Optional[ttk.PanedWindow] = None
        
    def show_window(self) -> None:
        """Display the chatlog window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
            
        self.window = tk.Toplevel(self.master)
        self.window.title("Chat History")
        self.window.geometry("1000x600")
        
        # Create main container
        self.paned = ttk.PanedWindow(self.window, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Users panel
        users_frame = ttk.Frame(self.paned)
        ttk.Label(users_frame, text="Users").pack(anchor=tk.W)
        self.user_list = tk.Listbox(users_frame, exportselection=False)
        self.user_list.pack(fill=tk.BOTH, expand=True)
        self.user_list.bind('<<ListboxSelect>>', self._on_user_select)
        self.paned.add(users_frame, weight=1)
        
        # Messages panel
        messages_frame = ttk.Frame(self.paned)
        ttk.Label(messages_frame, text="Messages").pack(anchor=tk.W)
        self.messages_text = tk.Text(messages_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.messages_text.pack(fill=tk.BOTH, expand=True)
        self.paned.add(messages_frame, weight=3)
        
        # Links panel
        links_frame = ttk.Frame(self.paned)
        ttk.Label(links_frame, text="Shared Links").pack(anchor=tk.W)
        self.links_text = tk.Text(links_frame, wrap=tk.WORD, state=tk.DISABLED)
        self.links_text.pack(fill=tk.BOTH, expand=True)
        self.paned.add(links_frame, weight=1)
        
        # Toolbar
        toolbar = ttk.Frame(self.window)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Clear Selected", command=self._clear_selected).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Export", command=self._export_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Import", command=self._import_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Close", command=self.window.destroy).pack(side=tk.RIGHT, padx=2)
        
        # Load data
        self.refresh_users()
        
    def _on_user_select(self, event: Optional[tk.Event] = None) -> None:
        """Handle user selection."""
        selection = self.user_list.curselection()
        if not selection:
            return
            
        username = self.user_list.get(selection[0])
        self._show_user_messages(username)
        self._show_user_links(username)
        
    def _show_user_messages(self, username: str) -> None:
        """Display messages for selected user."""
        messages = self.persistence.load_messages(username)
        
        self.messages_text.configure(state=tk.NORMAL)
        self.messages_text.delete(1.0, tk.END)
        
        for msg in messages:
            timestamp = msg.get('timestamp', '')
            text = msg.get('text', '')
            self.messages_text.insert(tk.END, f"[{timestamp}] {text}\n")
            
        self.messages_text.configure(state=tk.DISABLED)
        
    def _show_user_links(self, username: str) -> None:
        """Display links shared by selected user."""
        links = self.persistence.load_links(username)
        
        self.links_text.configure(state=tk.NORMAL)
        self.links_text.delete(1.0, tk.END)
        
        for link in links:
            timestamp = link.get('timestamp', '')
            url = link.get('url', '')
            self.links_text.insert(tk.END, f"[{timestamp}] {url}\n")
            
        self.links_text.configure(state=tk.DISABLED)
        
    def add_message(self, username: str, text: str) -> None:
        """Add a new message to the logs.
        
        Args:
            username: Sender's username
            text: Message text
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Store message
        self.persistence.add_message(username, {
            'timestamp': timestamp,
            'text': text
        })
        
        # Extract any links
        urls = re.findall(r'https?://\S+', text)
        for url in urls:
            self.persistence.add_link(username, {
                'timestamp': timestamp,
                'url': url
            })
            
        # Refresh if window is open
        if self.window and self.window.winfo_exists():
            self.refresh_users()
            
    def _clear_selected(self) -> None:
        """Clear history for selected user."""
        selection = self.user_list.curselection()
        if not selection:
            return
            
        username = self.user_list.get(selection[0])
        if messagebox.askyesno(
            "Clear History",
            f"Clear all history for {username}?"
        ):
            self.persistence.clear_user_data(username)
            self.refresh_users()
            
    def _export_logs(self) -> None:
        """Export chat logs to file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        if filename:
            self.persistence.export_logs(filename)
            
    def _import_logs(self) -> None:
        """Import chat logs from file."""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if filename and messagebox.askyesno(
            "Import Logs",
            "This will merge imported logs with existing ones. Continue?"
        ):
            self.persistence.import_logs(filename)
            self.refresh_users()
            
    def refresh_users(self) -> None:
        """Refresh the users list."""
        if not self.user_list:
            return
            
        users = self.persistence.get_users()
        
        self.user_list.delete(0, tk.END)
        for user in sorted(users):
            self.user_list.insert(tk.END, user)

    def process_message(self, message: Dict[str, Any]) -> None:
        """Process an incoming message for chat logging.
        
        Args:
            message: Parsed message dictionary containing sender, text, etc.
        """
        if not message:
            return
            
        # Extract message components
        sender = message.get('sender', 'Unknown')
        text = message.get('text', '')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Add message to chat history
        if sender and text:
            self.add_message(sender, text)
            
        # Process any URLs in the message
        if text:
            self.parse_and_store_hyperlinks(text, sender)
