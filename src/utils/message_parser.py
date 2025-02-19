from typing import Optional, Tuple, List
import re
from dataclasses import dataclass
from datetime import datetime

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
        # Pattern for directed messages
        self.directed_pattern = re.compile(
            r'^From\s+(\S+)\s+\((whispered|to)\s*(?:to\s+(\S+))?\):\s*(.+)$',
            re.IGNORECASE
        )
        
        # Pattern for normal messages
        self.normal_pattern = re.compile(
            r'^From\s+(\S+)(?:@[\w.]+)?(?:\s+\([^)]+\))?\s*:\s*(.+)$',
            re.IGNORECASE
        )
        
        # Pattern for system messages
        self.system_pattern = re.compile(
            r'^\*\*\*\s+(.+)\s+\*\*\*$'
        )
        
        # Pattern for URLs
        self.url_pattern = re.compile(
            r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)'
        )

    def parse(self, text: str) -> ParsedMessage:
        """Parse a message into its components.
        
        Args:
            text: Raw message text
            
        Returns:
            ParsedMessage object
        """
        timestamp = datetime.now()
        
        # Try directed message pattern first
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
            
        # Try normal message pattern
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
            
        # Check for system message
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
            
        # Default to treating as raw text
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
        
        # Clean and normalize URLs
        cleaned_urls = []
        for url in urls:
            # Remove trailing punctuation
            url = re.sub(r'[.,;:]+$', '', url)
            
            # Add http:// to www. urls
            if url.startswith('www.'):
                url = 'http://' + url
                
            cleaned_urls.append(url)
            
        return cleaned_urls
