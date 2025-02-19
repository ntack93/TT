from typing import Optional
import tkinter as tk
from tkinter import ttk
import asyncio
import threading

from .ui.terminal import TerminalUI
from .ui.settings import SettingsManager
from .ui.favorites import FavoritesManager
from .ui.triggers import TriggerManager
from .ui.chatlog import ChatlogManager
from .network.telnet import TelnetManager
from .storage.persistence import PersistenceManager
from .utils.message_parser import MessageParser


class BBSTerminalApp:
    """Main application orchestrator for the BBS Terminal."""
    
    def __init__(self, master: tk.Tk) -> None:
        """Initialize the BBS Terminal application.
        
        Args:
            master: Root Tkinter window
        """
        self.master = master
        self.master.title("Retro BBS Terminal")

        # Initialize managers and dependencies
        self.persistence = PersistenceManager()
        self.settings = SettingsManager(master, self.persistence)
        self.telnet = TelnetManager(self.handle_incoming_data)
        self.message_parser = MessageParser()
        
        # Initialize UI components with their dependencies
        self.terminal = TerminalUI(
            master,
            self.settings,
            self.telnet,
            self.message_parser
        )
        
        self.favorites = FavoritesManager(
            master,
            self.persistence,
            self.terminal
        )
        
        self.triggers = TriggerManager(
            master,
            self.persistence,
            self.telnet
        )
        
        self.chatlog = ChatlogManager(
            master,
            self.persistence,
            self.message_parser
        )

        # Set up the event loop
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # Set up the message queue
        self.msg_queue = asyncio.Queue()
        
        # Configure cleanup handlers
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Start periodic tasks
        self.start_background_tasks()

    def start_background_tasks(self) -> None:
        """Start periodic background tasks."""
        # Check message queue every 100ms
        self.master.after(100, self.process_message_queue)
        
        # Refresh chat members every 5 seconds
        self.master.after(5000, self.terminal.refresh_chat_members)

    async def handle_incoming_data(self, data: str) -> None:
        """Handle incoming data from telnet connection.
        
        Args:
            data: Raw data received from telnet
        """
        await self.msg_queue.put(data)

    def process_message_queue(self) -> None:
        """Process messages from the queue and update UI."""
        try:
            while True:
                # Get all available messages
                data = self.loop.run_until_complete(
                    self.msg_queue.get_nowait()
                )
                
                # Parse and process the message
                parsed_msg = self.message_parser.parse(data)
                
                # Update UI components
                self.terminal.update_display(parsed_msg)
                self.chatlog.process_message(parsed_msg)
                
                # Check triggers
                self.triggers.check_message(parsed_msg)
                
        except asyncio.QueueEmpty:
            pass
        finally:
            # Schedule next check
            self.master.after(100, self.process_message_queue)

    async def cleanup(self) -> None:
        """Perform cleanup operations before shutdown."""
        try:
            # Cancel all pending tasks
            tasks = [t for t in asyncio.all_tasks(self.loop) 
                    if t is not asyncio.current_task()]
            for task in tasks:
                task.cancel()
                
            # Wait for tasks to complete
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            # Disconnect telnet
            await self.telnet.disconnect()
            
            # Close the event loop
            self.loop.stop()
            self.loop.close()
            
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def on_closing(self) -> None:
        """Handle application shutdown."""
        try:
            # Create new event loop for cleanup
            cleanup_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cleanup_loop)
            
            # Run cleanup with timeout
            cleanup_loop.run_until_complete(
                asyncio.wait_for(self.cleanup(), timeout=5.0)
            )
            cleanup_loop.close()
            
        except (asyncio.TimeoutError, Exception) as e:
            print(f"Error during shutdown: {e}")
            
        finally:
            # Force quit
            try:
                self.master.quit()
            finally:
                self.master.destroy()

    def run(self) -> None:
        """Start the application main loop."""
        self.master.mainloop()
