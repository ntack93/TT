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
    
    def __init__(self, data_dir: str = "data") -> None:
        """Initialize persistence manager.
        
        Args:
            data_dir: Directory for data storage
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.data_dir / "messages").mkdir(exist_ok=True)
        (self.data_dir / "links").mkdir(exist_ok=True)
        
    def get_users(self) -> List[str]:
        """Get list of users with chat history."""
        users = set()
        
        # Check messages directory
        msg_path = self.data_dir / "messages"
        for f in msg_path.glob("*.json"):
            users.add(f.stem)
            
        # Check links directory
        links_path = self.data_dir / "links"
        for f in links_path.glob("*.json"):
            users.add(f.stem)
            
        return sorted(users)
        
    def load_messages(self, username: str) -> List[Dict[str, str]]:
        """Load messages for a user."""
        try:
            path = self.data_dir / "messages" / f"{username}.json"
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading messages: {e}")
        return []
        
    def load_links(self, username: str) -> List[Dict[str, str]]:
        """Load links shared by a user."""
        try:
            path = self.data_dir / "links" / f"{username}.json"
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading links: {e}")
        return []
        
    def add_message(self, username: str, message: Dict[str, str]) -> None:
        """Add a message to user's history."""
        messages = self.load_messages(username)
        messages.append(message)
        
        path = self.data_dir / "messages" / f"{username}.json"
        with open(path, 'w') as f:
            json.dump(messages, f)
            
    def add_link(self, username: str, link: Dict[str, str]) -> None:
        """Add a shared link to user's history."""
        links = self.load_links(username)
        links.append(link)
        
        path = self.data_dir / "links" / f"{username}.json"
        with open(path, 'w') as f:
            json.dump(links, f)
            
    def clear_user_data(self, username: str) -> None:
        """Clear all data for a user."""
        # Remove message history
        msg_path = self.data_dir / "messages" / f"{username}.json"
        if msg_path.exists():
            msg_path.unlink()
            
        # Remove links history    
        links_path = self.data_dir / "links" / f"{username}.json"
        if links_path.exists():
            links_path.unlink()
            
    def export_logs(self, filename: str) -> None:
        """Export all chat logs to a file."""
        data = {
            'messages': {},
            'links': {}
        }
        
        # Export messages
        for user in self.get_users():
            data['messages'][user] = self.load_messages(user)
            data['links'][user] = self.load_links(user)
            
        with open(filename, 'w') as f:
            json.dump(data, f)
            
    def import_logs(self, filename: str) -> None:
        """Import chat logs from a file."""
        with open(filename) as f:
            data = json.load(f)
            
        # Handle old format
        if isinstance(data, dict) and not ('messages' in data or 'links' in data):
            # Assume old format where data is directly username -> messages
            for user, messages in data.items():
                current = self.load_messages(user)
                current.extend(messages)
                
                path = self.data_dir / "messages" / f"{user}.json"
                with open(path, 'w') as f:
                    json.dump(current, f)
            return
            
        # Handle new format with messages/links separation
        if 'messages' in data:
            for user, messages in data['messages'].items():
                current = self.load_messages(user)
                current.extend(messages)
                
                path = self.data_dir / "messages" / f"{user}.json"
                with open(path, 'w') as f:
                    json.dump(current, f)
                
        if 'links' in data:
            for user, links in data['links'].items():
                current = self.load_links(user)
                current.extend(links)
                
                path = self.data_dir / "links" / f"{user}.json"
                with open(path, 'w') as f:
                    json.dump(current, f)

    def load_json(self, filename: str, default: Any = None) -> Dict[str, Any]:
        """Load JSON data from a file in the data directory.
        
        Args:
            filename: Name of the JSON file without path
            default: Default value if file doesn't exist or error occurs
            
        Returns:
            Loaded JSON data as dictionary
        """
        try:
            path = self.data_dir / filename
            if path.exists():
                with open(path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {filename}: {e}")
        return default if default is not None else {}
        
    def save_json(self, filename: str, data: Dict[str, Any]) -> None:
        """Save data as JSON to a file in the data directory.
        
        Args:
            filename: Name of the JSON file without path
            data: Data to save
        """
        try:
            path = self.data_dir / filename
            with open(path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving {filename}: {e}")
