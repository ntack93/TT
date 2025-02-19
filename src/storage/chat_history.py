from typing import Dict, List, Set
import json
from pathlib import Path
from datetime import datetime

class ChatHistoryManager:
    """Manages chat history and member tracking."""
    
    def __init__(self, data_dir: Path) -> None:
        """Initialize chat history manager.
        
        Args:
            data_dir: Directory for storing chat data
        """
        self.data_dir = data_dir
        self.chatlog_file = data_dir / "chatlog.json"
        self.members_file = data_dir / "chat_members.json"
        self.last_seen_file = data_dir / "last_seen.json"

    def save_message(self, sender: str, message: str, timestamp: Optional[datetime] = None) -> None:
        """Save a chat message.
        
        Args:
            sender: Message sender
            message: Message content
            timestamp: Message timestamp (default: current time)
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        chatlog = self.load_chatlog()
        if sender not in chatlog:
            chatlog[sender] = []
            
        formatted_msg = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {message}"
        chatlog[sender].append(formatted_msg)
        
        # Trim if necessary
        if self._get_size(chatlog) > 1024 * 1024 * 1024:  # 1GB
            self._trim_chatlog(chatlog)
            
        self._save_json(self.chatlog_file, chatlog)

    def update_last_seen(self, members: Set[str]) -> None:
        """Update last seen timestamps for members.
        
        Args:
            members: Set of currently active members
        """
        last_seen = self.load_last_seen()
        timestamp = int(datetime.now().timestamp())
        
        for member in members:
            last_seen[member.lower()] = timestamp
            
        self._save_json(self.last_seen_file, last_seen)

    def save_members(self, members: Set[str]) -> None:
        """Save current chat members.
        
        Args:
            members: Set of active members
        """
        self._save_json(self.members_file, list(members))

    def load_chatlog(self) -> Dict[str, List[str]]:
        """Load chat history."""
        return self._load_json(self.chatlog_file, {})

    def load_last_seen(self) -> Dict[str, int]:
        """Load last seen timestamps."""
        return self._load_json(self.last_seen_file, {})

    def load_members(self) -> Set[str]:
        """Load chat members."""
        return set(self._load_json(self.members_file, []))

    def _save_json(self, file: Path, data: Any) -> None:
        """Save data to JSON file."""
        with open(file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_json(self, file: Path, default: Any) -> Any:
        """Load data from JSON file."""
        try:
            if file.exists():
                with open(file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading {file.name}: {e}")
        return default

    def _get_size(self, data: Any) -> int:
        """Get size of data in bytes."""
        return len(json.dumps(data).encode('utf-8'))

    def _trim_chatlog(self, chatlog: Dict[str, List[str]]) -> None:
        """Trim chatlog to stay under size limit."""
        while self._get_size(chatlog) > 1024 * 1024 * 1024:  # 1GB
            for messages in chatlog.values():
                if messages:
                    messages.pop(0)  # Remove oldest message
