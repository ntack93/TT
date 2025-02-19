from typing import List, Any
import tkinter as tk
from tkinter import ttk, messagebox

class FavoritesManager:
    """Manages favorite BBS addresses and connections."""
    
    def __init__(self, master: tk.Tk, persistence: Any, terminal: Any) -> None:
        """Initialize favorites manager.
        
        Args:
            master: Root window
            persistence: Persistence manager instance
            terminal: Terminal UI instance
        """
        self.master = master
        self.persistence = persistence
        self.terminal = terminal
        self.favorites_window = None
        self.favorites = self.load_favorites()

    def show_window(self) -> None:
        """Display the favorites management window."""
        if self.favorites_window and self.favorites_window.winfo_exists():
            self.favorites_window.lift()
            return

        self.favorites_window = tk.Toplevel(self.master)
        self.favorites_window.title("Favorite BBS Addresses")
        self.favorites_window.grab_set()
        
        # Create listbox for favorites
        self.listbox = tk.Listbox(self.favorites_window, width=50)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Populate listbox
        for addr in self.favorites:
            self.listbox.insert(tk.END, addr)
            
        # Add new favorite
        input_frame = ttk.Frame(self.favorites_window)
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.new_addr = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.new_addr).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(input_frame, text="Add", command=self.add_favorite).pack(side=tk.RIGHT)
        
        # Control buttons
        btn_frame = ttk.Frame(self.favorites_window)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Remove", command=self.remove_favorite).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Connect", command=self.connect_to_favorite).pack(side=tk.RIGHT)

    def add_favorite(self) -> None:
        """Add a new favorite address."""
        addr = self.new_addr.get().strip()
        if addr and addr not in self.favorites:
            self.favorites.append(addr)
            self.listbox.insert(tk.END, addr)
            self.new_addr.set("")
            self.save_favorites()

    def remove_favorite(self) -> None:
        """Remove selected favorite address."""
        selection = self.listbox.curselection()
        if not selection:
            return
            
        addr = self.listbox.get(selection[0])
        if messagebox.askyesno("Confirm Remove", f"Remove {addr}?"):
            self.favorites.remove(addr)
            self.listbox.delete(selection[0])
            self.save_favorites()

    def connect_to_favorite(self) -> None:
        """Connect to selected favorite address."""
        selection = self.listbox.curselection()
        if not selection:
            return
            
        addr = self.listbox.get(selection[0])
        # Update terminal host and connect
        host, *port = addr.split(":")
        self.terminal.host.set(host)
        if port:
            self.terminal.port.set(int(port[0]))
        self.terminal.connect()

    def load_favorites(self) -> List[str]:
        """Load favorites from persistence."""
        return self.persistence.load_json('favorites.json', [])

    def save_favorites(self) -> None:
        """Save favorites to persistence."""
        self.persistence.save_json(self.favorites, 'favorites.json')
