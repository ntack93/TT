from typing import Dict, Any, Optional
import tkinter as tk
from tkinter import ttk
import json
from pathlib import Path

class PanelManager:
    """Manages panel layouts and sizes."""
    
    def __init__(self, master: tk.Tk, config_path: Path) -> None:
        """Initialize panel manager.
        
        Args:
            master: Root window
            config_path: Path to configuration directory
        """
        self.master = master
        self.config_file = config_path / "panel_sizes.json"
        self.panels: Dict[str, ttk.Frame] = {}
        self.paned_windows: Dict[str, ttk.PanedWindow] = {}
        
    def create_panel(
        self,
        name: str,
        parent: Any,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> ttk.Frame:
        """Create a new panel.
        
        Args:
            name: Panel identifier
            parent: Parent widget
            width: Optional width
            height: Optional height
            
        Returns:
            Created panel frame
        """
        panel = ttk.Frame(parent)
        if width:
            panel.configure(width=width)
        if height:
            panel.configure(height=height)
        panel.pack_propagate(False)
        
        self.panels[name] = panel
        return panel
        
    def create_paned_window(
        self,
        name: str,
        parent: Any,
        orient: str = tk.HORIZONTAL
    ) -> ttk.PanedWindow:
        """Create a new paned window container.
        
        Args:
            name: Paned window identifier
            parent: Parent widget
            orient: Orientation ('horizontal' or 'vertical')
            
        Returns:
            Created paned window
        """
        paned = ttk.PanedWindow(parent, orient=orient)
        self.paned_windows[name] = paned
        return paned
        
    def load_sizes(self) -> Dict[str, int]:
        """Load saved panel sizes.
        
        Returns:
            Dictionary of panel sizes
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading panel sizes: {e}")
        return {}
        
    def save_sizes(self) -> None:
        """Save current panel sizes."""
        sizes = {}
        
        # Get sizes from paned windows
        for name, paned in self.paned_windows.items():
            sash_positions = []
            try:
                for i in range(paned.count() - 1):
                    sash_positions.append(paned.sash_coord(i)[0])
                sizes[name] = sash_positions
            except Exception:
                continue
                
        # Get sizes from fixed-size panels
        for name, panel in self.panels.items():
            try:
                sizes[f"{name}_width"] = panel.winfo_width()
                sizes[f"{name}_height"] = panel.winfo_height()
            except Exception:
                continue
                
        try:
            with open(self.config_file, 'w') as f:
                json.dump(sizes, f)
        except Exception as e:
            print(f"Error saving panel sizes: {e}")
            
    def restore_sizes(self) -> None:
        """Restore saved panel sizes."""
        sizes = self.load_sizes()
        
        # Restore paned window sash positions
        for name, paned in self.paned_windows.items():
            if name in sizes:
                positions = sizes[name]
                try:
                    for i, pos in enumerate(positions):
                        paned.sashpos(i, pos)
                except Exception:
                    continue
                    
        # Restore fixed panel sizes
        for name, panel in self.panels.items():
            width_key = f"{name}_width"
            height_key = f"{name}_height"
            
            if width_key in sizes:
                panel.configure(width=sizes[width_key])
            if height_key in sizes:
                panel.configure(height=sizes[height_key])
