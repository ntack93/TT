from typing import Dict, Any, List, Tuple, Optional
import tkinter as tk
import re

class ANSIParser:
    """Parser for ANSI escape sequences and color codes."""
    
    def __init__(self) -> None:
        """Initialize the ANSI parser."""
        self.color_map = {
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'yellow',
            '34': '#3399FF',  # Light blue instead of dark blue
            '35': 'magenta',
            '36': 'cyan',
            '37': 'white',
            '90': 'grey',
            '91': 'bright_red',
            '92': 'bright_green',
            '93': 'bright_yellow',
            '94': 'bright_blue',
            '95': 'bright_magenta',
            '96': 'bright_cyan',
            '97': 'bright_white'
        }
        
        self.ansi_pattern = re.compile(r'\x1b\[(.*?)m')
        self.sgr_codes: Dict[str, str] = {
            '0': 'reset',
            '1': 'bold',
            '4': 'underline',
            '5': 'blink',
            '7': 'reverse',
            '8': 'concealed'
        }
        self.color_codes: Dict[str, str] = {
            '30': 'black', '31': 'red',     '32': 'green',  '33': 'yellow',
            '34': 'blue',  '35': 'magenta', '36': 'cyan',   '37': 'white',
            '90': 'gray',  '91': 'brightred', '92': 'brightgreen', '93': 'brightyellow',
            '94': 'brightblue', '95': 'brightmagenta', '96': 'brightcyan', '97': 'brightwhite'
        }

    def configure_tags(self, text_widget: tk.Text) -> None:
        """Configure text widget tags for ANSI colors.
        
        Args:
            text_widget: Tkinter Text widget to configure
        """
        text_widget.tag_configure("normal", foreground="white")
        
        for code, color in self.color_map.items():
            if color.startswith('bright_'):
                base_color = color.split('_')[1]
                text_widget.tag_configure(color, foreground=base_color)
            else:
                text_widget.tag_configure(color, foreground=color)

    def insert_with_tags(self, text_widget: tk.Text, text: str) -> None:
        """Insert text with appropriate ANSI color tags.
        
        Args:
            text_widget: Tkinter Text widget
            text: Text to insert with ANSI codes
        """
        last_end = 0
        current_tag = "normal"
        
        for match in self.ansi_pattern.finditer(text):
            start, end = match.span()
            
            # Insert text before the ANSI code
            if start > last_end:
                segment = text[last_end:start]
                text_widget.insert(tk.END, segment, current_tag)
            
            # Process the ANSI code
            codes = match.group(1).split(';')
            if '0' in codes:
                current_tag = "normal"
                codes.remove('0')
            
            # Apply any remaining color codes
            for code in codes:
                if code in self.color_map:
                    current_tag = self.color_map[code]
                    
            last_end = end
        
        # Insert any remaining text
        if last_end < len(text):
            text_widget.insert(tk.END, text[last_end:], current_tag)

    def strip_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from text.
        
        Args:
            text: Text containing ANSI codes
            
        Returns:
            Clean text without ANSI codes
        """
        return self.ansi_pattern.sub('', text)

    def parse(self, text: str) -> List[Tuple[str, Dict[str, bool]]]:
        """Parse text with ANSI sequences into segments with attributes.
        
        Args:
            text: Raw text with ANSI sequences
            
        Returns:
            List of (text, attributes) tuples
        """
        segments = []
        current_attrs = {}
        
        # Split on ANSI escape sequences
        parts = re.split('(\x1b\\[[0-9;]*[A-Za-z])', text)
        
        for part in parts:
            if part.startswith('\x1b['):
                # Process ANSI sequence
                self._update_attributes(part, current_attrs)
            elif part:
                # Add text segment with current attributes
                segments.append((part, current_attrs.copy()))
                
        return segments
    
    def _update_attributes(self, sequence: str, attrs: Dict[str, bool]) -> None:
        """Update attributes based on ANSI sequence."""
        if not sequence.endswith('m'):
            return
            
        # Extract codes
        codes = sequence[2:-1].split(';')
        
        if '0' in codes:
            # Reset all attributes
            attrs.clear()
            return
            
        for code in codes:
            if code in self.sgr_codes:
                attrs[self.sgr_codes[code]] = True
            elif code in self.color_codes:
                attrs['foreground'] = self.color_codes[code]
            elif code.startswith('4') and code[1:] in self.color_codes:
                attrs['background'] = self.color_codes[code[1:]]
