from typing import Any, Dict, List, Optional, Set
import json
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FontSettings:
    """Font configuration settings."""
    name: str = "Courier New"
    size: int = 10
    color: str = "white"
    background: str = "black"

class PersistenceManager:
    """Manages data persistence for the application."""
    
    def __init__(self, base_path: str = "./data") -> None:
        """Initialize persistence manager.
        
        Args:
            base_path: Base directory for data storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
    def _get_path(self, filename: str) -> Path:
        """Get full path for a file.
        
        Args:
            filename: Name of the file
            
        Returns:
            Path object for the file
        """
        return self.base_path / filename

    def save_json(self, data: Any, filename: str) -> None:
        """Save data as JSON.
        
        Args:
            data: Data to save
            filename: Name of the file
        """
        path = self._get_path(filename)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load_json(self, filename: str, default: Any = None) -> Any:
        """Load data from JSON file.
        
        Args:
            filename: Name of the file
            default: Default value if file doesn't exist
            
        Returns:
            Loaded data or default value
        """
        path = self._get_path(filename)
        try:
            if path.exists():
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
        return default

    def save_font_settings(self, settings: FontSettings) -> None:
        """Save font settings.
        
        Args:
            settings: Font settings to save
        """
        self.save_json({
            'font_name': settings.name,
            'font_size': settings.size,
            'fg': settings.color,
            'bg': settings.background
        }, 'font_settings.json')

    def load_font_settings(self) -> FontSettings:
        """Load font settings.
        
        Returns:
            FontSettings object
        """
        data = self.load_json('font_settings.json', {})
        return FontSettings(
            name=data.get('font_name', "Courier New"),
            size=data.get('font_size', 10),
            color=data.get('fg', 'white'),
            background=data.get('bg', 'black')
        )

    def save_chat_members(self, members: Set[str]) -> None:
        """Save current chat members.
        
        Args:
            members: Set of member names
        """
        self.save_json(list(members), 'chat_members.json')

    def load_chat_members(self) -> Set[str]:
        """Load chat members.
        
        Returns:
            Set of member names
        """
        data = self.load_json('chat_members.json', [])
        return set(data)

    def save_last_seen(self, timestamps: Dict[str, int]) -> None:
        """Save last seen timestamps.
        
        Args:
            timestamps: Dictionary of usernames to timestamps
        """
        self.save_json(timestamps, 'last_seen.json')

    def load_last_seen(self) -> Dict[str, int]:
        """Load last seen timestamps.
        
        Returns:
            Dictionary of usernames to timestamps
        """
        return self.load_json('last_seen.json', {})

    def save_chatlog(self, messages: Dict[str, List[str]]) -> None:
        """Save chat messages.
        
        Args:
            messages: Dictionary of usernames to lists of messages
        """
        self.save_json(messages, 'chatlog.json')

    def load_chatlog(self) -> Dict[str, List[str]]:
        """Load chat messages.
        
        Returns:
            Dictionary of usernames to lists of messages
        """
        return self.load_json('chatlog.json', {})
