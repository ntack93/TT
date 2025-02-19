import json
import os
from typing import Dict, Any, Optional

class Settings:
    """Manages application settings."""
    
    def __init__(self, settings_file: str = "settings.json") -> None:
        self.settings_file = settings_file
        self.settings: Dict[str, Any] = self.load()
        
    def load(self) -> Dict[str, Any]:
        """Load settings from file."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {}
        
    def save(self) -> None:
        """Save settings to file."""
        try:
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")
            
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value."""
        return self.settings.get(key, default)
        
    def set(self, key: str, value: Any) -> None:
        """Set a setting value."""
        self.settings[key] = value
        self.save()
