import winsound
from typing import Optional
import platform

class NotificationManager:
    """Manages sound notifications and alerts."""
    
    def __init__(self) -> None:
        self.enabled = True
        self.platform = platform.system()
        
    def play_message_notification(self) -> None:
        """Play sound for new message notification."""
        if self.enabled and self.platform == 'Windows':
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            
    def play_custom_sound(self, sound_type: str) -> None:
        """Play custom sound notification."""
        if not self.enabled:
            return
            
        if self.platform == 'Windows':
            sound_map = {
                'error': winsound.MB_ICONERROR,
                'warning': winsound.MB_ICONWARNING,
                'info': winsound.MB_ICONINFORMATION
            }
            sound_id = sound_map.get(sound_type, winsound.MB_ICONEXCLAMATION)
            winsound.MessageBeep(sound_id)
