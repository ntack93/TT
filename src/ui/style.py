from typing import Dict, Any
from tkinter import ttk

class StyleManager:
    """Manages application-wide styles and themes."""
    
    def __init__(self) -> None:
        self.style = ttk.Style()
        self.style.theme_use('default')
        
        # Define color schemes
        self.colors = {
            'primary': {
                'normal': '#28a745',    # Green
                'pressed': '#218838'
            },
            'danger': {
                'normal': '#dc3545',    # Red
                'pressed': '#c82333'
            },
            'action': {
                'wave': '#17a2b8',      # Blue
                'smile': '#ffc107',     # Yellow
                'dance': '#e83e8c',     # Pink
                'bow': '#6f42c1'        # Purple
            },
            'utility': {
                'chatlog': '#007bff',   # Blue
                'favorites': '#fd7e14',  # Orange
                'settings': '#6c757d',   # Gray
                'triggers': '#20c997'    # Teal
            }
        }
        
        self.configure_styles()
        
    def configure_styles(self) -> None:
        """Configure all button and widget styles."""
        # Configure connection buttons
        self._configure_button_style('Connect', self.colors['primary'])
        self._configure_button_style('Disconnect', self.colors['danger'])
        
        # Configure action buttons
        for action, color in self.colors['action'].items():
            self._configure_button_style(
                action.capitalize(),
                {'normal': color, 'pressed': color},
                fg='black' if action == 'smile' else 'white'
            )
            
        # Configure utility buttons
        for util, color in self.colors['utility'].items():
            self._configure_button_style(
                util.capitalize(),
                {'normal': color, 'pressed': color}
            )
            
    def _configure_button_style(
        self,
        name: str,
        colors: Dict[str, str],
        fg: str = 'white'
    ) -> None:
        """Configure a custom button style.
        
        Args:
            name: Style name
            colors: Color scheme dictionary
            fg: Foreground color
        """
        style_name = f"{name}.TButton"
        self.style.configure(
            style_name,
            foreground=fg,
            background=colors['normal'],
            bordercolor=colors['normal'],
            darkcolor=colors['normal'],
            lightcolor=colors['normal'],
            font=("Arial", 9, "bold"),
            relief="raised",
            padding=(10, 5)
        )
        
        self.style.map(
            style_name,
            foreground=[("pressed", fg), ("active", fg)],
            background=[("pressed", colors['pressed']), ("active", colors['normal'])],
            bordercolor=[("pressed", colors['pressed']), ("active", colors['normal'])],
            relief=[("pressed", "sunken"), ("active", "raised")]
        )
