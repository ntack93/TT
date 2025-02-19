from typing import Callable, Optional, Any
import asyncio
import telnetlib3
from dataclasses import dataclass

@dataclass
class TelnetConfig:
    """Configuration settings for telnet connection."""
    host: str
    port: int
    term_type: str = "ansi"
    encoding: str = "cp437"
    cols: int = 136
    rows: int = 50

class TelnetManager:
    """Manages telnet connection and communication."""
    
    def __init__(self, data_callback: Callable[[str], None]) -> None:
        """Initialize telnet manager.
        
        Args:
            data_callback: Callback function for received data
        """
        self.data_callback = data_callback
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected: bool = False
        self.stop_event = asyncio.Event()

    async def connect(self, config: TelnetConfig) -> None:
        """Establish telnet connection.
        
        Args:
            config: Telnet configuration settings
        """
        try:
            self.reader, self.writer = await telnetlib3.open_connection(
                host=config.host,
                port=config.port,
                term=config.term_type,
                encoding=config.encoding,
                cols=config.cols,
                rows=config.rows
            )
            self.connected = True
            await self.start_reading()
            
        except Exception as e:
            await self.data_callback(f"Connection failed: {e}\n")
            raise

    async def start_reading(self) -> None:
        """Start reading data from the connection."""
        try:
            while not self.stop_event.is_set():
                data = await self.reader.read(4096)
                if not data:
                    break
                await self.data_callback(data)
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            await self.data_callback(f"Error reading from server: {e}\n")
        finally:
            await self.disconnect()

    async def send(self, data: str) -> None:
        """Send data through the connection.
        
        Args:
            data: Data to send
        """
        if self.connected and self.writer:
            try:
                self.writer.write(data)
                await self.writer.drain()
            except Exception as e:
                print(f"Error sending data: {e}")

    async def disconnect(self) -> None:
        """Close the telnet connection."""
        self.stop_event.set()
        
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                print(f"Error closing connection: {e}")
            finally:
                self.connected = False
                self.reader = None
                self.writer = None
