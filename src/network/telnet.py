import asyncio
import telnetlib3
from typing import Callable, Optional, Any
from dataclasses import dataclass
from .keep_alive import KeepAliveManager

@dataclass
class TelnetConfig:
    """Configuration for telnet connection."""
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
        self.keep_alive = KeepAliveManager(self)
        
        # Create event loop in a separate thread
        self.loop = asyncio.new_event_loop()
        
        # Start loop in a new thread
        import threading
        self.loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.loop_thread.start()

    def _run_event_loop(self) -> None:
        """Run the event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def connect(self, config: TelnetConfig) -> None:
        """Connect to telnet server."""
        try:
            self.reader, self.writer = await telnetlib3.open_connection(
                host=config.host,
                port=config.port,
                term=config.term_type,
                encoding='cp437',  # Force CP437 encoding
                force_binary=True,
                connect_minwait=0.05,
                encoding_errors='replace',
                cols=config.cols,
                rows=config.rows
            )
            
            # Enhanced terminal negotiation
            self.writer.iac(telnetlib3.WILL, telnetlib3.TTYPE)
            self.writer.iac(telnetlib3.WILL, telnetlib3.NAWS)
            self.writer.iac(telnetlib3.WILL, telnetlib3.NEW_ENVIRON)
            self.writer.iac(telnetlib3.DO, telnetlib3.ECHO)
            self.writer.iac(telnetlib3.WILL, telnetlib3.SGA)
            self.writer.iac(telnetlib3.WILL, telnetlib3.BINARY)
            self.writer.iac(telnetlib3.DO, telnetlib3.BINARY)
            await self.writer.drain()

            self.connected = True
            asyncio.create_task(self.start_reading())
            
        except Exception as e:
            self.connected = False
            raise e

    async def disconnect(self) -> None:
        """Disconnect from telnet server."""
        if self.writer:
            try:
                self.writer.close()
                try:
                    await self.writer.wait_closed()
                except (AttributeError, Exception):
                    # Some StreamWriter implementations might not have wait_closed
                    await asyncio.sleep(0.1)  # Give time for the connection to close
            except Exception as e:
                print(f"Error during disconnect: {e}")
        
        self.connected = False
        self.reader = None
        self.writer = None

    async def send(self, data: str) -> None:
        """Send data to telnet server."""
        if self.writer and not self.writer.is_closing():
            try:
                # Ensure we have a string
                if not isinstance(data, str):
                    data = str(data)

                # Add newline if not present
                if not data.endswith('\r\n'):
                    data += '\r\n'
                    
                # Write the data directly (telnetlib3 handles encoding)
                self.writer.write(data)
                await self.writer.drain()
            except Exception as e:
                print(f"Error sending data: {e}")

    def send_sync(self, data: str) -> None:
        """Synchronous wrapper for send method."""
        if self.connected:
            # Ensure we have a string
            if not isinstance(data, str):
                data = str(data)
                
            future = asyncio.run_coroutine_threadsafe(self.send(data), self.loop)
            try:
                # Wait for the send to complete with timeout
                future.result(timeout=1.0)
            except Exception as e:
                print(f"Error in send_sync: {e}")

    async def start_reading(self) -> None:
        """Start reading data from the connection."""
        try:
            while self.connected and self.reader:
                try:
                    data = await self.reader.read(4096)
                    if not data:
                        break
                        
                    # Ensure proper CP437 decoding
                    if isinstance(data, bytes):
                        text = data.decode('cp437', errors='replace')
                    else:
                        text = data
                        
                    self.loop.call_soon_threadsafe(self.data_callback, text)
                        
                except Exception as e:
                    print(f"Error reading from connection: {e}")
                    if not self.connected:
                        break
                    continue
                    
        except Exception as e:
            print(f"Error in reading loop: {e}")
        finally:
            self.connected = False

    def start_keep_alive(self, interval: int) -> None:
        """Start the keep-alive mechanism."""
        self.keep_alive.interval = interval
        asyncio.run_coroutine_threadsafe(self.keep_alive.start(), self.loop)

    def stop_keep_alive(self) -> None:
        """Stop the keep-alive mechanism."""
        asyncio.run_coroutine_threadsafe(self.keep_alive.stop(), self.loop)

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        if self.loop_thread.is_alive():
            self.loop_thread.join(timeout=1.0)
