from typing import Optional, Tuple, List, Dict, Any
import re
from dataclasses import dataclass
from datetime import datetime
from .ansi import ANSIParser

@dataclass
class ParsedMessage:
    """Container for parsed message data."""
    timestamp: datetime
    sender: Optional[str]
    recipient: Optional[str]
    message_type: str
    content: str
    raw_text: str

class MessageParser:
    """Parser for BBS message formats and patterns."""
    
    def __init__(self) -> None:
        """Initialize message parser patterns."""
        self.ansi = ANSIParser()
        self.directed_pattern = re.compile(
            r'^From\s+(\S+)\s+\((whispered|to)\s*(?:to\s+(\S+))?\):\s*(.+)$',
            re.IGNORECASE
        )
        
        self.normal_pattern = re.compile(
            r'^From\s+(\S+)(?:@[\w.]+)?(?:\s+\([^)]+\))?\s*:\s*(.+)$',
            re.IGNORECASE
        )
        
        self.system_pattern = re.compile(
            r'^\*\*\*\s+(.+)\s+\*\*\*$'
        )
        
        self.url_pattern = re.compile(
            r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)'
        )
        
        self.chat_pattern = re.compile(r'<([^>]+)>\s*(.*)')
        self.private_pattern = re.compile(r'\[([^\]]+)\]\s*(.*)')
        
    def parse(self, text: str) -> ParsedMessage:
        """Parse a message into its components.
        
        Args:
            text: Raw message text
            
        Returns:
            ParsedMessage object
        """
        timestamp = datetime.now()
        
        directed_match = self.directed_pattern.match(text)
        if directed_match:
            sender, msg_type, recipient, content = directed_match.groups()
            return ParsedMessage(
                timestamp=timestamp,
                sender=sender,
                recipient=recipient,
                message_type="directed",
                content=content,
                raw_text=text
            )
            
        normal_match = self.normal_pattern.match(text)
        if normal_match:
            sender, content = normal_match.groups()
            return ParsedMessage(
                timestamp=timestamp,
                sender=sender,
                recipient=None,
                message_type="normal",
                content=content,
                raw_text=text
            )
            
        system_match = self.system_pattern.match(text)
        if system_match:
            return ParsedMessage(
                timestamp=timestamp,
                sender=None,
                recipient=None,
                message_type="system",
                content=system_match.group(1),
                raw_text=text
            )
            
        return ParsedMessage(
            timestamp=timestamp,
            sender=None,
            recipient=None,
            message_type="raw",
            content=text,
            raw_text=text
        )

    def extract_urls(self, text: str) -> List[str]:
        """Extract URLs from text.
        
        Args:
            text: Text to search for URLs
            
        Returns:
            List of found URLs
        """
        urls = self.url_pattern.findall(text)
        
        cleaned_urls = []
        for url in urls:
            url = re.sub(r'[.,;:]+$', '', url)
            
            if url.startswith('www.'):
                url = 'http://' + url
                
            cleaned_urls.append(url)
            
        return cleaned_urls

    def extract_username(self, message: str) -> Optional[str]:
        """Extract username from a message if present."""
        for pattern in [self.chat_pattern, self.private_pattern]:
            match = pattern.match(message)
            if match:
                return match.group(1)
        return None

    def extract_users_from_list(self, text: str) -> set:
        """Extract usernames from a user list message."""
        users = set()
        lines = text.split('\n')
        
        for line in lines:
            clean_line = self.ansi.strip_ansi(line)
            
            if ':' in clean_line:
                user = clean_line.split(':')[0].strip()
                if user:
                    users.add(user)
            elif '|' in clean_line:
                user = clean_line.split('|')[0].strip()
                if user:
                    users.add(user)
                    
        return users
