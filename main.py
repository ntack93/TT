import tkinter as tk
from tkinter import ttk
import threading
import asyncio
import telnetlib3
import time
import queue
import re
import json
import os

###############################################################################
#                         BBS Telnet App (No Chatbot)
###############################################################################

class BBSTerminalApp:
    def __init__(self, master):
        # 1.0️⃣ 🎉 SETUP
        self.master = master
        self.master.title("Retro BBS Terminal")

        # 1.1️⃣ 🎉 CONFIGURABLE VARIABLES
        self.host = tk.StringVar(value="bbs.example.com")
        self.port = tk.IntVar(value=23)

        # Username/password + remembering them
        self.username = tk.StringVar(value=self.load_username())
        self.password = tk.StringVar(value=self.load_password())
        self.remember_username = tk.BooleanVar(value=False)
        self.remember_password = tk.BooleanVar(value=False)

        # MUD mode?
        self.mud_mode = tk.BooleanVar(value=False)

        # Logon automation toggles
        self.logon_automation_enabled = tk.BooleanVar(value=False)
        self.auto_login_enabled = tk.BooleanVar(value=False)

        # A queue to pass incoming telnet data => main thread
        self.msg_queue = queue.Queue()

        # Terminal font
        self.font_name = tk.StringVar(value="Courier New")
        self.font_size = tk.IntVar(value=10)

        # Terminal mode (ANSI or something else)
        self.terminal_mode = tk.StringVar(value="ANSI")

        # Telnet references
        self.reader = None
        self.writer = None
        self.stop_event = threading.Event()  # signals background thread to stop
        self.connected = False

        # Buffer for partial lines
        self.partial_line = ""

        # Keep-Alive
        self.keep_alive_stop_event = threading.Event()
        self.keep_alive_task = None
        self.keep_alive_enabled = tk.BooleanVar(value=False)

        # Our own event loop for asyncio
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        # Favorites
        self.favorites = self.load_favorites()
        self.favorites_window = None

        # Triggers
        self.triggers = self.load_triggers()
        self.triggers_window = None
        self.chatlog_window = None

        self.last_message_info = None  # will hold (sender, recipient) of the last parsed message

        # Chat members
        self.chat_members = self.load_chat_members_file()
        self.last_seen = self.load_last_seen_file()

        self.user_list_buffer = []
        self.collecting_users = False

        # 1.2️⃣ 🎉 BUILD UI
        self.build_ui()

        # Periodically check for incoming telnet data
        self.master.after(100, self.process_incoming_messages)

        # Start the periodic task to refresh chat members
        self.master.after(5000, self.refresh_chat_members)

    def build_ui(self):
        """Creates all the frames and widgets for the UI."""
        # Create a container frame that will hold both the main UI and the members panel
        container = ttk.Frame(self.master)
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create the Chatroom Members panel on the RIGHT
        members_frame = ttk.LabelFrame(container, text="Chatroom Members")
        members_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.members_listbox = tk.Listbox(members_frame, height=20, width=20)
        self.members_listbox.pack(fill=tk.BOTH, expand=True)
        
        # Create the main UI frame on the LEFT
        main_frame = ttk.Frame(container, name='main_frame')
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 1.2.1️⃣ Connection settings
        config_frame = ttk.LabelFrame(main_frame, text="Connection Settings")
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(config_frame, text="BBS Host:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.host_entry = ttk.Entry(config_frame, textvariable=self.host, width=30)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        self.create_context_menu(self.host_entry)
        
        ttk.Label(config_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        self.port_entry = ttk.Entry(config_frame, textvariable=self.port, width=6)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.create_context_menu(self.port_entry)
        
        self.connect_button = ttk.Button(config_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Favorites
        favorites_button = ttk.Button(config_frame, text="Favorites", command=self.show_favorites_window)
        favorites_button.grid(row=0, column=5, padx=5, pady=5)
        
        # MUD Mode
        mud_mode_check = ttk.Checkbutton(config_frame, text="Mud Mode", variable=self.mud_mode)
        mud_mode_check.grid(row=0, column=6, padx=5, pady=5)
        
        # Keep Alive checkbox
        keep_alive_check = ttk.Checkbutton(config_frame, text="Keep Alive", variable=self.keep_alive_enabled, command=self.toggle_keep_alive)
        keep_alive_check.grid(row=0, column=8, padx=5, pady=5)
        
        # Add Triggers button
        triggers_button = ttk.Button(config_frame, text="Triggers", command=self.show_triggers_window)
        triggers_button.grid(row=0, column=9, padx=5, pady=5)
        
        # Add Chatlog button
        chatlog_button = ttk.Button(config_frame, text="Chatlog", command=self.show_chatlog_window)
        chatlog_button.grid(row=0, column=10, padx=5, pady=5)
        
        # 1.2.2️⃣ Username Frame
        username_frame = ttk.LabelFrame(main_frame, text="Username")
        username_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.username_entry = ttk.Entry(username_frame, textvariable=self.username, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_context_menu(self.username_entry)
        
        self.remember_username_check = ttk.Checkbutton(
            username_frame, text="Remember", variable=self.remember_username)
        self.remember_username_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.send_username_button = ttk.Button(username_frame, text="Send", command=self.send_username)
        self.send_username_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 1.2.3️⃣ Password Frame
        password_frame = ttk.LabelFrame(main_frame, text="Password")
        password_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.password_entry = ttk.Entry(password_frame, textvariable=self.password, width=30, show="*")
        self.password_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_context_menu(self.password_entry)
        
        self.remember_password_check = ttk.Checkbutton(
            password_frame, text="Remember", variable=self.remember_password)
        self.remember_password_check.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.send_password_button = ttk.Button(password_frame, text="Send", command=self.send_password)
        self.send_password_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 1.2.4️⃣ Terminal Output
        terminal_frame = ttk.LabelFrame(main_frame, text="BBS Output")
        terminal_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.terminal_display = tk.Text(
            terminal_frame,
            wrap=tk.WORD,
            height=15,
            state=tk.DISABLED,
            bg="black"
        )
        self.terminal_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll_bar = ttk.Scrollbar(terminal_frame, command=self.terminal_display.yview)
        scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_display.configure(yscrollcommand=scroll_bar.set)
        
        self.define_ansi_tags()

        # 1.2.5️⃣ Messages to You Frame
        directed_msg_frame = ttk.LabelFrame(main_frame, text="Messages to You")
        directed_msg_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.directed_msg_display = tk.Text(
            directed_msg_frame,
            wrap=tk.WORD,
            height=10,
            state=tk.DISABLED,
            bg="lightyellow"
        )
        self.directed_msg_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        directed_msg_scroll_bar = ttk.Scrollbar(directed_msg_frame, command=self.directed_msg_display.yview)
        directed_msg_scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.directed_msg_display.configure(yscrollcommand=directed_msg_scroll_bar.set)

        # 1.2.6️⃣ Input Frame
        input_frame = ttk.LabelFrame(main_frame, text="Send Message")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.input_var = tk.StringVar()
        self.input_box = ttk.Entry(input_frame, textvariable=self.input_var, width=80)
        self.input_box.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.input_box.bind("<Return>", self.send_message)
        self.create_context_menu(self.input_box)
        
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # 1.2.7️⃣ Settings & Font
        settings_button = ttk.Button(config_frame, text="Settings", command=self.show_settings_window)
        settings_button.grid(row=0, column=7, padx=5, pady=5)
        
        self.update_display_font()

    def create_context_menu(self, widget):
        """Create a right-click context menu for the given widget."""
        menu = tk.Menu(widget, tearoff=0)
        menu.add_command(label="Cut", command=lambda: widget.event_generate("<<Cut>>"))
        menu.add_command(label="Copy", command=lambda: widget.event_generate("<<Copy>>"))
        menu.add_command(label="Paste", command=lambda: widget.event_generate("<<Paste>>"))
        menu.add_command(label="Select All", command=lambda: widget.event_generate("<<SelectAll>>"))

        def show_context_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        widget.bind("<Button-3>", show_context_menu)

    # 1.3️⃣ SETTINGS WINDOW
    def show_settings_window(self):
        """Open a Toplevel for font settings, automation toggles, etc."""
        settings_win = tk.Toplevel(self.master)
        settings_win.title("Settings")

        row_index = 0

        # Font Name
        ttk.Label(settings_win, text="Font Name:").grid(row=row_index, column=0, padx=5, pady=5, sticky=tk.E)
        font_options = ["Courier New", "Consolas", "Lucida Console", "Terminus (TTF)"]
        font_dropdown = ttk.Combobox(settings_win, textvariable=self.font_name, values=font_options, state="readonly")
        font_dropdown.grid(row=row_index, column=1, padx=5, pady=5, sticky=tk.W)
        row_index += 1

        # Font Size
        ttk.Label(settings_win, text="Font Size:").grid(row=row_index, column=0, padx=5, pady=5, sticky=tk.E)
        ttk.Entry(settings_win, textvariable=self.font_size, width=5).grid(row=row_index, column=1, padx=5, pady=5, sticky=tk.W)
        row_index += 1

        # Logon Automation
        ttk.Label(settings_win, text="Logon Automation:").grid(row=row_index, column=0, padx=5, pady=5, sticky=tk.E)
        ttk.Checkbutton(settings_win, variable=self.logon_automation_enabled).grid(row=row_index, column=1, padx=5, pady=5, sticky=tk.W)
        row_index += 1

        # Auto Login
        ttk.Label(settings_win, text="Auto Login:").grid(row=row_index, column=0, padx=5, pady=5, sticky=tk.E)
        ttk.Checkbutton(settings_win, variable=self.auto_login_enabled).grid(row=row_index, column=1, padx=5, pady=5, sticky=tk.W)
        row_index += 1

        # Save Button
        save_button = ttk.Button(settings_win, text="Save", command=lambda: self.save_settings(settings_win))
        save_button.grid(row=row_index, column=0, columnspan=2, pady=10)

    def save_settings(self, window):
        """Called when user clicks 'Save' in the settings window."""
        self.update_display_font()
        window.destroy()

    def update_display_font(self):
        """Update the Text widget's font."""
        new_font = (self.font_name.get(), self.font_size.get())
        self.terminal_display.configure(font=new_font)

    # 1.4️⃣ ANSI PARSING
    def define_ansi_tags(self):
        """Define text tags for basic ANSI foreground colors (30-37, 90-97)."""
        self.terminal_display.tag_configure("normal", foreground="white")

        color_map = {
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'yellow',
            '34': 'blue',
            '35': 'magenta',
            '36': 'cyan',
            '37': 'white',
            '90': 'bright_black',
            '91': 'bright_red',
            '92': 'bright_green',
            '93': 'bright_yellow',
            '94': 'bright_blue',
            '95': 'bright_magenta',
            '96': 'bright_cyan',
            '97': 'bright_white'
        }
        for code, color_name in color_map.items():
            if color_name.startswith("bright_"):
                base_color = color_name.split("_", 1)[1]
                self.terminal_display.tag_configure(color_name, foreground=base_color)
            else:
                self.terminal_display.tag_configure(color_name, foreground=color_name)

    # 1.5️⃣ CONNECT / DISCONNECT
    def toggle_connection(self):
        """Connect or disconnect from the BBS."""
        if self.connected:
            asyncio.run_coroutine_threadsafe(self.disconnect_from_bbs(), self.loop).result()
        else:
            self.start_connection()

    def start_connection(self):
        """Start the telnetlib3 client in a background thread."""
        host = self.host.get()
        port = self.port.get()
        self.stop_event.clear()

        def run_telnet():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.telnet_client_task(host, port))

        thread = threading.Thread(target=run_telnet, daemon=True)
        thread.start()
        self.append_terminal_text(f"Connecting to {host}:{port}...\n", "normal")
        self.start_keep_alive()

    async def telnet_client_task(self, host, port):
        """Async function connecting via telnetlib3 (CP437 + ANSI)."""
        try:
            reader, writer = await telnetlib3.open_connection(
                host=host,
                port=port,
                term=self.terminal_mode.get().lower(),
                encoding='cp437',
                cols=132
            )
        except Exception as e:
            self.msg_queue.put_nowait(f"Connection failed: {e}\n")
            return

        self.reader = reader
        self.writer = writer
        self.connected = True
        self.connect_button.config(text="Disconnect")
        self.msg_queue.put_nowait(f"Connected to {host}:{port}\n")

        try:
            while not self.stop_event.is_set():
                data = await reader.read(4096)
                if not data:
                    break
                self.msg_queue.put_nowait(data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.msg_queue.put_nowait(f"Error reading from server: {e}\n")
        finally:
            await self.disconnect_from_bbs()

    async def disconnect_from_bbs(self):
        """Stop the background thread and close connections."""
        if not self.connected or getattr(self, '_disconnecting', False):
            return

        self._disconnecting = True
        try:
            self.stop_event.set()
            self.stop_keep_alive()

            if self.writer:
                try:
                    # Try to close the writer and allow it time to drain
                    self.writer.close()
                    await self.writer.drain()
                except Exception as e:
                    print(f"Error closing writer: {e}")

            # Mark the connection as closed
            self.connected = False
            self.reader = None
            self.writer = None

            def update_connect_button():
                if self.connect_button and self.connect_button.winfo_exists():
                    self.connect_button.config(text="Connect")
            if threading.current_thread() is threading.main_thread():
                update_connect_button()
            else:
                self.master.after_idle(update_connect_button)

            self.msg_queue.put_nowait("Disconnected from BBS.\n")
        finally:
            self._disconnecting = False

    # 1.6️⃣ MESSAGES
    def process_incoming_messages(self):
        """Check the queue for data and parse lines for display."""
        try:
            while True:
                data = self.msg_queue.get_nowait()
                self.process_data_chunk(data)
        except queue.Empty:
            pass
        finally:
            self.master.after(100, self.process_incoming_messages)

    def process_data_chunk(self, data):
        """Accumulate data, split on newlines, display in terminal."""
        data = data.replace('\r\n', '\n').replace('\r', '\n')
        self.partial_line += data
        lines = self.partial_line.split("\n")
        
        for line in lines[:-1]:
            clean_line = line.strip()
            
            # --- Filter header lines ---
            # If we're currently collecting header lines, add the line to the buffer and skip displaying it.
            if self.collecting_users:
                self.user_list_buffer.append(line)
                if "are here with you." in clean_line:
                    self.update_chat_members(self.user_list_buffer)
                    self.collecting_users = False
                    self.user_list_buffer = []
                continue  # Skip displaying this line
            
            # If the line starts the header block, begin collecting and skip displaying.
            if clean_line.startswith("You are in"):
                self.user_list_buffer = [line]
                self.collecting_users = True
                continue  # Skip displaying this line
            
            # Skip the line immediately following the header block if it starts with "Just press"
            if clean_line.startswith("Just press") and not self.collecting_users:
                continue  # Skip displaying this line
            
            # --- Process directed messages ---
            directed_msg_match = re.match(r'^From\s+(\S+)\s+\((to you|whispered)\):\s*(.+)$', clean_line, re.IGNORECASE)
            if directed_msg_match:
                sender, _, message = directed_msg_match.groups()
                self.append_directed_message(f"From {sender}: {message}\n")
                continue  # Skip displaying this line
            
            # --- Process and display non-header lines ---
            self.append_terminal_text(line + "\n", "normal")
            self.check_triggers(line)
            self.parse_and_save_chatlog_message(line)
            if self.auto_login_enabled.get() or self.logon_automation_enabled.get():
                self.detect_logon_prompt(line)

        self.partial_line = lines[-1]

    def detect_logon_prompt(self, line):
        """Simple triggers to automate login if toggles are on."""
        lower_line = line.lower()
        # Typical BBS prompts
        if "enter your password:" in lower_line:
            self.master.after(500, self.send_password)
        elif "type it in and press enter" in lower_line or 'otherwise type "new":' in lower_line:
            self.master.after(500, self.send_username)

    def parse_and_save_chatlog_message(self, line):
        """Parse and save chat messages in formats:
           - Public: 'From <username>: <message>'
           - DM:     'From <username> (to <recipient>): <message>'
        """
        # Remove any ANSI escape sequences that might interfere with matching.
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        
        # Use a regex that optionally captures the direct message recipient.
        match = re.match(
            r'^\s*From\s+(\S+)(?:\s+\(to\s+([^)]+)\))?:\s*(.+)$',
            clean_line,
            re.IGNORECASE
        )
        
        if match:
            sender, recipient, message = match.groups()
            # Replace "you" with your local username if applicable:
            if recipient and recipient.lower() == "you":
                recipient = self.username.get()
            
            # Log the message only under the sender.
            self.save_chatlog_message(sender, message)
            
            # Save the last parsed DM info for later continuation lines.
            self.last_message_info = (sender, None)  # No recipient logged

    def append_to_last_chatlog_message(self, username, extra_text):
        """Append extra_text to the last message logged for username."""
        chatlog = self.load_chatlog()
        if username in chatlog and chatlog[username]:
            chatlog[username][-1] += "\n" + extra_text
            self.save_chatlog(chatlog)

    def send_message(self, event=None):
        """Send the user's typed message to the BBS."""
        if not self.connected or not self.writer:
            self.append_terminal_text("Not connected to any BBS.\n", "normal")
            return

        user_input = self.input_var.get()
        self.input_var.set("")
        prefix = "Gos " if self.mud_mode.get() else ""
        # If there is no text, send only a carriage return (newline)
        if user_input.strip() == "":
            message = "\r\n"
        else:
            message = prefix + user_input + "\r\n"
        asyncio.run_coroutine_threadsafe(self._send_message(message), self.loop)

    async def _send_message(self, message):
        self.writer.write(message)
        await self.writer.drain()

    def send_username(self):
        """Send the username to the BBS."""
        if self.connected and self.writer:
            asyncio.run_coroutine_threadsafe(self._send_message(self.username.get() + "\r\n"), self.loop)
            if self.remember_username.get():
                self.save_username()

    def send_password(self):
        """Send the password to the BBS."""
        if self.connected and self.writer:
            asyncio.run_coroutine_threadsafe(self._send_message(self.password.get() + "\r\n"), self.loop)
            if self.remember_password.get():
                self.save_password()

    def check_triggers(self, message):
        """Check incoming messages for triggers and send automated response if matched."""
        # Loop through the triggers array
        for trigger_obj in self.triggers:
            # Perform a case-insensitive check if the trigger text exists in the message
            if trigger_obj['trigger'] and trigger_obj['trigger'].lower() in message.lower():
                # Send the associated response
                self.send_custom_message(trigger_obj['response'])

    def send_custom_message(self, message):
        """Send a custom message (for trigger responses)."""
        print(f"Sending custom message: {message}")
        asyncio.run_coroutine_threadsafe(self._send_message(message + "\r\n"), self.loop)

    # 1.7️⃣ KEEP-ALIVE
    async def keep_alive(self):
        """Send an <ENTER> keystroke every 10 seconds."""
        while not self.keep_alive_stop_event.is_set():
            if self.connected and self.writer:
                self.writer.write("\r\n")
                await self.writer.drain()
            await asyncio.sleep(10)

    def start_keep_alive(self):
        """Start the keep-alive coroutine if enabled."""
        if self.keep_alive_enabled.get():
            self.keep_alive_stop_event.clear()
            if self.loop:
                self.keep_alive_task = self.loop.create_task(self.keep_alive())

    def stop_keep_alive(self):
        """Stop the keep-alive coroutine."""
        self.keep_alive_stop_event.set()
        if self.keep_alive_task:
            self.keep_alive_task.cancel()

    def toggle_keep_alive(self):
        """Toggle the keep-alive coroutine based on the checkbox state."""
        if self.keep_alive_enabled.get():
            self.start_keep_alive()
        else:
            self.stop_keep_alive()

    # 1.8️⃣ FAVORITES
    def show_favorites_window(self):
        """Open a Toplevel window to manage favorite BBS addresses."""
        if self.favorites_window and self.favorites_window.winfo_exists():
            self.favorites_window.lift()
            return

        self.favorites_window = tk.Toplevel(self.master)
        self.favorites_window.title("Favorite BBS Addresses")

        row_index = 0
        self.favorites_listbox = tk.Listbox(self.favorites_window, height=10, width=50)
        self.favorites_listbox.grid(row=row_index, column=0, columnspan=2, padx=5, pady=5)
        self.update_favorites_listbox()

        row_index += 1
        self.new_favorite_var = tk.StringVar()
        ttk.Entry(self.favorites_window, textvariable=self.new_favorite_var, width=40).grid(
            row=row_index, column=0, padx=5, pady=5)

        add_button = ttk.Button(self.favorites_window, text="Add", command=self.add_favorite)
        add_button.grid(row=row_index, column=1, padx=5, pady=5)

        row_index += 1
        remove_button = ttk.Button(self.favorites_window, text="Remove", command=self.remove_favorite)
        remove_button.grid(row=row_index, column=0, columnspan=2, pady=5)

        self.favorites_listbox.bind("<<ListboxSelect>>", self.populate_host_field)

    def update_favorites_listbox(self):
        self.favorites_listbox.delete(0, tk.END)
        for address in self.favorites:
            self.favorites_listbox.insert(tk.END, address)

    def add_favorite(self):
        new_address = self.new_favorite_var.get().strip()
        if new_address and new_address not in self.favorites:
            self.favorites.append(new_address)
            self.update_favorites_listbox()
            self.new_favorite_var.set("")
            self.save_favorites()

    def remove_favorite(self):
        selected_index = self.favorites_listbox.curselection()
        if selected_index:
            address = self.favorites_listbox.get(selected_index)
            self.favorites.remove(address)
            self.update_favorites_listbox()
            self.save_favorites()

    def populate_host_field(self, event):
        selected_index = self.favorites_listbox.curselection()
        if selected_index:
            address = self.favorites_listbox.get(selected_index)
            self.host.set(address)

    def load_favorites(self):
        if os.path.exists("favorites.json"):
            with open("favorites.json", "r") as file:
                return json.load(file)
        return []

    def save_favorites(self):
        with open("favorites.json", "w") as file:
            json.dump(self.favorites, file)

    # 1.9️⃣ LOCAL STORAGE FOR USER/PASS
    def load_username(self):
        if os.path.exists("username.json"):
            with open("username.json", "r") as file:
                return json.load(file)
        return ""

    def save_username(self):
        with open("username.json", "w") as file:
            json.dump(self.username.get(), file)

    def load_password(self):
        if os.path.exists("password.json"):
            with open("password.json", "r") as file:
                return json.load(file)
        return ""

    def save_password(self):
        with open("password.json", "w") as file:
            json.dump(self.password.get(), file)

    def load_triggers(self):
        """Load triggers from a local file or initialize an empty list."""
        if os.path.exists("triggers.json"):
            with open("triggers.json", "r") as file:
                return json.load(file)
        return []

    def save_triggers_to_file(self):
        """Save triggers to a local file."""
        with open("triggers.json", "w") as file:
            json.dump(self.triggers, file)

    def show_triggers_window(self):
        """Open a Toplevel window to manage triggers."""
        if self.triggers_window and self.triggers_window.winfo_exists():
            self.triggers_window.lift()
            return

        self.triggers_window = tk.Toplevel(self.master)
        self.triggers_window.title("Automation Triggers")

        row_index = 0
        triggers_frame = ttk.Frame(self.triggers_window)
        triggers_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.trigger_vars = []
        self.response_vars = []

        for i in range(10):
            ttk.Label(triggers_frame, text=f"Trigger {i+1}:").grid(row=row_index, column=0, padx=5, pady=5, sticky=tk.E)
            trigger_var = tk.StringVar(value=self.triggers[i]['trigger'] if i < len(self.triggers) else "")
            response_var = tk.StringVar(value=self.triggers[i]['response'] if i < len(self.triggers) else "")
            self.trigger_vars.append(trigger_var)
            self.response_vars.append(response_var)
            ttk.Entry(triggers_frame, textvariable=trigger_var, width=30).grid(row=row_index, column=1, padx=5, pady=5, sticky=tk.W)
            ttk.Entry(triggers_frame, textvariable=response_var, width=30).grid(row=row_index, column=2, padx=5, pady=5, sticky=tk.W)
            row_index += 1

        save_button = ttk.Button(triggers_frame, text="Save", command=self.save_triggers)
        save_button.grid(row=row_index, column=0, columnspan=3, pady=10)

    def save_triggers(self):
        """Save triggers from the triggers window."""
        self.triggers = []
        for trigger_var, response_var in zip(self.trigger_vars, self.response_vars):
            self.triggers.append({
                'trigger': trigger_var.get().strip(),
                'response': response_var.get().strip()
            })
        self.save_triggers_to_file()
        self.triggers_window.destroy()

    def append_terminal_text(self, text, default_tag="normal"):
        """Append text to the terminal display with optional ANSI parsing."""
        self.terminal_display.configure(state=tk.NORMAL)
        self.parse_ansi_and_insert(text)
        self.terminal_display.see(tk.END)
        self.terminal_display.configure(state=tk.DISABLED)

    def parse_ansi_and_insert(self, text_data):
        """Minimal parser for ANSI color codes (foreground only)."""
        ansi_escape_regex = re.compile(r'\x1b\[(.*?)m')
        last_end = 0
        current_tag = "normal"

        for match in ansi_escape_regex.finditer(text_data):
            start, end = match.span()
            if start > last_end:
                self.terminal_display.insert(tk.END, text_data[last_end:start], current_tag)
            code_string = match.group(1)
            codes = code_string.split(';')
            if '0' in codes:
                current_tag = "normal"
                codes.remove('0')

            for c in codes:
                mapped_tag = self.map_code_to_tag(c)
                if mapped_tag:
                    current_tag = mapped_tag
            last_end = end

        if last_end < len(text_data):
            self.terminal_display.insert(tk.END, text_data[last_end:], current_tag)

    def map_code_to_tag(self, color_code):
        """Map numeric color code to a defined Tk tag."""
        valid_codes = {
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'yellow',
            '34': 'blue',
            '35': 'magenta',
            '36': 'cyan',
            '37': 'white',
            '90': 'bright_black',
            '91': 'bright_red',
            '92': 'bright_green',
            '93': 'bright_yellow',
            '94': 'bright_blue',
            '95': 'bright_magenta',
            '96': 'bright_cyan',
            '97': 'bright_white',
        }
        return valid_codes.get(color_code, None)

    def save_chatlog_message(self, username, message):
        """Save a message to the chatlog."""
        chatlog = self.load_chatlog()
        if username not in chatlog:
            chatlog[username] = []
        chatlog[username].append(message)

        # Check if chatlog exceeds 1GB and trim if necessary
        chatlog_size = len(json.dumps(chatlog).encode('utf-8'))
        if chatlog_size > 1 * 1024 * 1024 * 1024:  # 1GB
            self.trim_chatlog(chatlog)

        self.save_chatlog(chatlog)

    def load_chatlog(self):
        """Load chatlog from a local file or initialize an empty dictionary."""
        if os.path.exists("chatlog.json"):
            with open("chatlog.json", "r") as file:
                return json.load(file)
        return {}

    def save_chatlog(self, chatlog):
        """Save chatlog to a local file."""
        with open("chatlog.json", "w") as file:
            json.dump(chatlog, file)

    def trim_chatlog(self, chatlog):
        """Trim the chatlog to fit within the size limit."""
        usernames = list(chatlog.keys())
        while len(json.dumps(chatlog).encode('utf-8')) > 1 * 1024 * 1024 * 1024:  # 1GB
            for username in usernames:
                if chatlog[username]:
                    chatlog[username].pop(0)  # Remove the oldest message
                    if len(json.dumps(chatlog).encode('utf-8')) <= 1 * 1024 * 1024 * 1024:
                        break

    def clear_chatlog_for_user(self, username):
        """Clear all chatlog messages for the specified username."""
        chatlog = self.load_chatlog()
        if username in chatlog:
            chatlog[username] = []  # Reset the messages list
            self.save_chatlog(chatlog)

    def clear_active_chatlog(self):
        """Clear chatlog messages for the currently selected user in the listbox."""
        selected_index = self.chatlog_listbox.curselection()
        if selected_index:
            username = self.chatlog_listbox.get(selected_index)
            self.clear_chatlog_for_user(username)
            self.display_chatlog_messages(None)  # Refresh the display

    def show_chatlog_window(self):
        """Open a Toplevel window to manage chatlog."""
        if self.chatlog_window and self.chatlog_window.winfo_exists():
            self.chatlog_window.lift()
            return

        self.chatlog_window = tk.Toplevel(self.master)
        self.chatlog_window.title("Chatlog")

        row_index = 0
        chatlog_frame = ttk.Frame(self.chatlog_window)
        chatlog_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.chatlog_listbox = tk.Listbox(chatlog_frame, height=10, width=30)
        self.chatlog_listbox.grid(row=row_index, column=0, padx=5, pady=5, sticky=tk.N+tk.S)
        self.chatlog_listbox.bind("<<ListboxSelect>>", self.display_chatlog_messages)

        self.chatlog_display = tk.Text(chatlog_frame, wrap=tk.WORD, state=tk.DISABLED, bg="white")
        self.chatlog_display.grid(row=row_index, column=1, padx=5, pady=5, sticky=tk.N+tk.S+tk.E+tk.W)

        chatlog_scrollbar = ttk.Scrollbar(chatlog_frame, command=self.chatlog_display.yview)
        chatlog_scrollbar.grid(row=row_index, column=2, sticky=tk.N+tk.S)
        self.chatlog_display.configure(yscrollcommand=chatlog_scrollbar.set)

        self.load_chatlog_list()

        # Add Clear and Close buttons below the chatlog display.
        row_index += 1
        clear_button = ttk.Button(chatlog_frame, text="Clear", command=self.clear_active_chatlog)
        clear_button.grid(row=row_index, column=0, columnspan=3, pady=5)

        close_button = ttk.Button(chatlog_frame, text="Close", command=self.chatlog_window.destroy)
        close_button.grid(row=row_index+1, column=0, columnspan=3, pady=10)

    def load_chatlog_list(self):
        """Load chatlog from a local file and populate the listbox."""
        chatlog = self.load_chatlog()
        self.chatlog_listbox.delete(0, tk.END)
        for username in chatlog.keys():
            self.chatlog_listbox.insert(tk.END, username)

    def display_chatlog_messages(self, event):
        """Display messages for the selected user."""
        selected_index = self.chatlog_listbox.curselection()
        if selected_index:
            username = self.chatlog_listbox.get(selected_index)
            chatlog = self.load_chatlog()
            messages = chatlog.get(username, [])
            self.chatlog_display.configure(state=tk.NORMAL)
            self.chatlog_display.delete(1.0, tk.END)
            for message in messages:
                self.chatlog_display.insert(tk.END, message + "\n")
            self.chatlog_display.configure(state=tk.DISABLED)

    def update_members_display(self):
        """Update the chat members Listbox with the current chat_members set."""
        self.members_listbox.delete(0, tk.END)
        for member in sorted(self.chat_members):
            self.members_listbox.insert(tk.END, member)

    def update_chat_members(self, lines_with_users):
        """Update the chat members based on the provided lines."""
        combined = " ".join(lines_with_users)
        combined_clean = re.sub(r'\x1b\[[0-9;]*m', '', combined)
        print(f"[DEBUG] Combined user lines: {combined_clean}")

        # Use regex to capture email addresses in the user list.
        addresses = re.findall(r'\b\S+@\S+\.\S+\b', combined_clean)
        print(f"[DEBUG] Regex match addresses: {addresses}")

        # Extract usernames (the part before the '@')
        usernames = [address.split('@')[0] for address in addresses]

        # In some cases, the last username might be listed without an email,
        # so we can try an additional search.
        last_user_match = re.search(r'and (\S+) are here with you\.', combined_clean)
        if last_user_match:
            usernames.append(last_user_match.group(1))

        # Also check for lines like "<username> is here with you."
        user_without_domain_matches = re.findall(r'\b(\S+)\s+is here with you\.', combined_clean)
        usernames.extend(user_without_domain_matches)

        print(f"[DEBUG] Extracted usernames: {usernames}")
        self.chat_members = set(usernames)

        # Optionally update last seen timestamps
        current_time = int(time.time())
        for member in self.chat_members:
            self.last_seen[member.lower()] = current_time
        self.save_last_seen_file()

        # Save the chat members to file
        self.save_chat_members_file()

        # Refresh the members display panel
        self.update_members_display()

    def load_chat_members_file(self):
        """Load chat members from chat_members.json, or return an empty set if not found."""
        if os.path.exists("chat_members.json"):
            with open("chat_members.json", "r") as file:
                try:
                    return set(json.load(file))
                except Exception as e:
                    print(f"[DEBUG] Error loading chat members file: {e}")
                    return set()
        return set()

    def save_chat_members_file(self):
        """Save the current chat members set to chat_members.json."""
        try:
            with open("chat_members.json", "w") as file:
                json.dump(list(self.chat_members), file)
        except Exception as e:
            print(f"[DEBUG] Error saving chat members file: {e}")

    def load_last_seen_file(self):
        """Load last seen timestamps from last_seen.json, or return an empty dictionary if not found."""
        if os.path.exists("last_seen.json"):
            with open("last_seen.json", "r") as file:
                try:
                    return json.load(file)
                except Exception as e:
                    print(f"[DEBUG] Error loading last seen file: {e}")
                    return {}
        return {}

    def save_last_seen_file(self):
        """Save the current last seen timestamps to last_seen.json."""
        try:
            with open("last_seen.json", "w") as file:
                json.dump(self.last_seen, file)
        except Exception as e:
            print(f"[DEBUG] Error saving last seen file: {e}")

    def refresh_chat_members(self):
        """Periodically refresh the chat members list."""
        self.update_members_display()
        self.master.after(5000, self.refresh_chat_members)

    def append_directed_message(self, text):
        """Append text to the directed messages display."""
        self.directed_msg_display.configure(state=tk.NORMAL)
        self.directed_msg_display.insert(tk.END, text)
        self.directed_msg_display.see(tk.END)
        self.directed_msg_display.configure(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = BBSTerminalApp(root)
    root.mainloop()
    # Cleanup
    if app.connected:
        try:
            asyncio.run_coroutine_threadsafe(app.disconnect_from_bbs(), app.loop).result()
        except Exception as e:
            print(f"Error during disconnect: {e}")
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.close()
    except Exception as e:
        print(f"Error closing loop: {e}")


if __name__ == "__main__":
    main()
