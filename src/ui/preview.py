import tkinter as tk
from PIL import Image, ImageTk
import requests
from io import BytesIO
from urllib.parse import urlparse
import threading

class PreviewManager:
    """Manages thumbnail and preview windows for links."""
    
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        self.preview_window = None
        self.current_image = None  # Keep reference to prevent garbage collection
        
    def show_thumbnail(self, url: str, x: int, y: int) -> None:
        """Display thumbnail preview at specified coordinates."""
        self.hide_thumbnail()  # Clear any existing preview
        
        self.preview_window = tk.Toplevel(self.master)
        self.preview_window.overrideredirect(True)
        self.preview_window.attributes("-topmost", True)
        self.preview_window.geometry(f"+{x}+{y}")
        
        label = tk.Label(self.preview_window, text="Loading preview...", bg="white")
        label.pack()
        
        # Start fetch in background
        threading.Thread(
            target=self._fetch_preview,
            args=(url, label),
            daemon=True
        ).start()
        
    def hide_thumbnail(self) -> None:
        """Hide the thumbnail preview."""
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None
            self.current_image = None
            
    def _fetch_preview(self, url: str, label: tk.Label) -> None:
        """Fetch and display preview content."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            
            # Handle direct image URLs
            if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                response = requests.get(url, headers=headers, timeout=5)
                self._handle_image_preview(response.content, label)
                return
                
            # Try to get webpage favicon
            parsed_url = urlparse(url)
            favicon_url = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
            
            response = requests.get(favicon_url, headers=headers, timeout=5)
            if response.status_code == 200:
                self._handle_favicon_preview(response.content, label, parsed_url.netloc)
            else:
                self._show_error(label, parsed_url.netloc)
                
        except Exception as e:
            self._show_error(label, str(e))
            
    def _handle_image_preview(self, image_data: bytes, label: tk.Label) -> None:
        """Process and display image preview."""
        try:
            image = Image.open(BytesIO(image_data))
            image.thumbnail((200, 150))
            self.current_image = ImageTk.PhotoImage(image)
            
            self.master.after(0, lambda: self._update_label(
                label, image=self.current_image, text=""
            ))
        except Exception as e:
            self._show_error(label, f"Image error: {e}")
            
    def _handle_favicon_preview(self, image_data: bytes, label: tk.Label, domain: str) -> None:
        """Process and display favicon preview."""
        try:
            image = Image.open(BytesIO(image_data))
            image = image.resize((32, 32), Image.Resampling.LANCZOS)
            self.current_image = ImageTk.PhotoImage(image)
            
            self.master.after(0, lambda: self._update_label(
                label, image=self.current_image, text=domain
            ))
        except Exception:
            self._show_error(label, domain)
            
    def _show_error(self, label: tk.Label, message: str) -> None:
        """Display error message in preview."""
        self.master.after(0, lambda: self._update_label(
            label, text=f"Preview not available\n{message}"
        ))
        
    def _update_label(self, label: tk.Label, **kwargs) -> None:
        """Update label safely from main thread."""
        if self.preview_window and label.winfo_exists():
            label.configure(**kwargs)
