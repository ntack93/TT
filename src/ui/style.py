from typing import Dict
from tkinter import ttk

class StyleManager:
    """Manages application-wide styles and themes."""
    
    def __init__(self) -> None:
        """Initialize style manager."""
        self.style = ttk.Style()
        self.style.theme_use('default')
        
        # Define theme colors
        self.colors = {
            'primary': {
                'normal': '#28a745',    # Green
                'hover': '#218838',
                'pressed': '#1e7e34'
            },
            'danger': {
                'normal': '#dc3545',    # Red
                'hover': '#c82333',  
                'pressed': '#bd2130'
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
            },
            'text': {
                'normal': '#f8f9fa',    # Light gray
                'dark': '#343a40',      # Dark gray
                'muted': '#6c757d'      # Medium gray
            },
            'bg': {
                'primary': '#ffffff',   # White
                'secondary': '#f8f9fa', # Light gray
                'light': '#ffffff'      # White
            }
        }
        
        self.configure_styles()
        
    def configure_styles(self) -> None:
        """Configure all button and widget styles."""
        # Connection button styles
        self._configure_button_style(
            'Connect', 
            self.colors['primary'],
            font=('Arial', 9, 'bold')
        )
        self._configure_button_style(
            'Disconnect', 
            self.colors['danger'],
            font=('Arial', 9, 'bold')
        )
        
        # Action button styles
        for action, color in self.colors['action'].items():
            self._configure_button_style(
                action.capitalize(),
                {'normal': color, 'hover': color, 'pressed': color},
                fg='black' if action == 'smile' else self.colors['text']['normal']
            )
            
        # Utility button styles  
        for util, color in self.colors['utility'].items():
            self._configure_button_style(
                util.capitalize(),
                {'normal': color, 'hover': color, 'pressed': color}
            )
        
        # Frame styles
        self.style.configure(
            'TFrame',
            background=self.colors['bg']['primary']
        )
        
        # Label styles
        self.style.configure(
            'TLabel',
            foreground=self.colors['text']['dark'],
            background=self.colors['bg']['primary']
        )
        
        # Entry styles
        self.style.configure(
            'TEntry',
            fieldbackground=self.colors['bg']['secondary'],
            foreground=self.colors['text']['dark']
        )
            
    def _configure_button_style(
        self,
        name: str, 
        colors: Dict[str, str],
        font: tuple = ('Arial', 9),
        fg: str = None
    ) -> None:
        """Configure a custom button style.
        
        Args:
            name: Style name
            colors: Color scheme dictionary
            font: Font tuple (family, size)
            fg: Override foreground color
        """
        style_name = f"{name}.TButton"
        fg = fg or self.colors['text']['normal']
        
        # Normal state
        self.style.configure(
            style_name,
            foreground=fg,
            background=colors['normal'],
            bordercolor=colors['normal'],
            font=font,
            relief='raised',
            padding=(10, 5)
        )
        
        # Map colors for different states
        self.style.map(
            style_name,
            foreground=[('pressed', fg), ('active', fg)],
            background=[
                ('pressed', colors['pressed']),
                ('active', colors.get('hover', colors['normal']))
            ],
            bordercolor=[
                ('pressed', colors['pressed']),
                ('active', colors.get('hover', colors['normal']))
            ],
            relief=[('pressed', 'sunken')]
        )
