import asyncio
from typing import Optional, Any

class KeepAliveManager:
    """Manages keep-alive functionality for telnet connections."""
    
    def __init__(self, telnet: Any) -> None:
        """Initialize keep-alive manager.
        
        Args:
            telnet: TelnetManager instance
        """
        self.telnet = telnet
        self.task: Optional[asyncio.Task] = None
        self.stop_event = asyncio.Event()
        self.interval = 60  # Seconds between keep-alive messages

    async def start(self) -> None:
        """Start sending keep-alive messages."""
        self.stop_event.clear()
        self.task = asyncio.create_task(self._keep_alive_loop())

    async def stop(self) -> None:
        """Stop sending keep-alive messages."""
        if self.task:
            self.stop_event.set()
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None

    async def _keep_alive_loop(self) -> None:
        """Main keep-alive message loop."""
        while not self.stop_event.is_set():
            try:
                await self.telnet.send("\r\n")
                await asyncio.sleep(self.interval)
            except Exception as e:
                print(f"Keep-alive error: {e}")
                break
