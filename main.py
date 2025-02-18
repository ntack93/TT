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
import webbrowser
from PIL import Image, ImageTk
import requests
from io import BytesIO
import winsound  # Import winsound for playing sound effects on Windows
from tkinter import simpledialog  # Import simpledialog for input dialogs


###############################################################################
#                         BBS Telnet App (No Chatbot)
###############################################################################

class BBSTerminalApp:
    def __init__(self, master):
        # 1.0️⃣ 🎉 SETUP
        self.master = master
        self.master.title("Retro BBS Terminal")

        # Load saved font settings or use defaults
        saved_font_settings = self.load_font_settings()
        self.font_name = tk.StringVar(value=saved_font_settings.get('font_name', "Courier New"))
        self.font_size = tk.IntVar(value=saved_font_settings.get('font_size', 10))
        self.current_font_settings = {
            'font': (self.font_name.get(), self.font_size.get()),
            'fg': saved_font_settings.get('fg', 'white'),
            'bg': saved_font_settings.get('bg', 'black')
        }

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

        self.cols = 136  # Set the number of columns
        self.rows = 50   # Set the number of rows

        self.preview_window = None  # Initialize the preview_window attribute

        # Variables to track visibility of sections
        self.show_connection_settings = tk.BooleanVar(value=True)
        self.show_username = tk.BooleanVar(value=True)
        self.show_password = tk.BooleanVar(value=True)
        self.show_all = tk.BooleanVar(value=True)

        # Action list
        self.actions = []
        self.collecting_actions = False

        # 1.2️⃣ 🎉 BUILD UI
        self.build_ui()

        # Periodically check for incoming telnet data
        self.master.after(100, self.process_incoming_messages)

        # Start the periodic task to refresh chat members
        self.master.after(5000, self.refresh_chat_members)

    def build_ui(self):
        """Creates all the frames and widgets for the UI."""
        # Configure button styles
        self.configure_button_styles()
        
        # Create a container frame that will hold both the main UI and the members panel
        container = ttk.Frame(self.master)
        container.pack(fill=tk.BOTH, expand=True)

        # Create the Actions listbox on the RIGHT, just to the left of the Chatroom Members Panel
        actions_frame = ttk.LabelFrame(container, text="Actions")
        actions_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.actions_listbox = tk.Listbox(actions_frame, height=20, width=20, exportselection=False)  # Add exportselection=False
        self.actions_listbox.pack(fill=tk.BOTH, expand=True)
        self.actions_listbox.bind("<Double-Button-1>", self.on_action_select)
        self.actions_listbox.bind("<Return>", self.on_action_select)
        self.actions_listbox.bind("<Button-1>", self.on_action_select)

        # Create the Chatroom Members panel on the RIGHT
        members_frame = ttk.LabelFrame(container, text="Chatroom Members")
        members_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        self.members_listbox = tk.Listbox(members_frame, height=20, width=20, exportselection=False)  # Add exportselection=False
        self.members_listbox.pack(fill=tk.BOTH, expand=True)
        self.create_members_context_menu()

        # Create the main UI frame on the LEFT using grid layout
        main_frame = ttk.Frame(container, name='main_frame')
        main_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=3)  # Paned container gets most space
        main_frame.rowconfigure(2, weight=0)
        
        # --- Row 0: Top frame (connection settings, username, password) ---
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Master checkbox to show/hide all sections
        master_check = ttk.Checkbutton(top_frame, text="Show All", variable=self.show_all, command=self.toggle_all_sections)
        master_check.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        # Add Teleconference Action buttons
        wave_button = ttk.Button(top_frame, text="Wave", command=lambda: self.send_action("wave"), style="Wave.TButton")
        wave_button.grid(row=0, column=1, padx=5, pady=5)
        smile_button = ttk.Button(top_frame, text="Smile", command=lambda: self.send_action("smile"), style="Smile.TButton")
        smile_button.grid(row=0, column=2, padx=5, pady=5)
        dance_button = ttk.Button(top_frame, text="Dance", command=lambda: self.send_action("dance"), style="Dance.TButton")
        dance_button.grid(row=0, column=3, padx=5, pady=5)
        bow_button = ttk.Button(top_frame, text="Bow", command=lambda: self.send_action("bow"), style="Bow.TButton")
        bow_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Add the Chatlog button
        chatlog_button = ttk.Button(top_frame, text="Chatlog", command=self.show_chatlog_window, style="Chatlog.TButton")
        chatlog_button.grid(row=0, column=5, padx=5, pady=5)

        # Connection settings example:
        self.conn_frame = ttk.LabelFrame(top_frame, text="Connection Settings")
        self.conn_frame.grid(row=1, column=0, columnspan=6, sticky="ew", padx=5, pady=5)
        ttk.Label(self.conn_frame, text="BBS Host:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.E)
        self.host_entry = ttk.Entry(self.conn_frame, textvariable=self.host, width=30)
        self.host_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        ttk.Label(self.conn_frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.E)
        self.port_entry = ttk.Entry(self.conn_frame, textvariable=self.port, width=6)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        self.connect_button = ttk.Button(self.conn_frame, text="Connect", command=self.toggle_connection, style="Connect.TButton")
        self.connect_button.grid(row=0, column=4, padx=5, pady=5)
        
        # Add the Favorites button
        favorites_button = ttk.Button(self.conn_frame, text="Favorites", command=self.show_favorites_window, style="Favorites.TButton")
        favorites_button.grid(row=0, column=5, padx=5, pady=5)
        
        # Add the Settings button
        settings_button = ttk.Button(self.conn_frame, text="Settings", command=self.show_settings_window, style="Settings.TButton")
        settings_button.grid(row=0, column=6, padx=5, pady=5)
        
        # Add the Triggers button
        triggers_button = ttk.Button(self.conn_frame, text="Triggers", command=self.show_triggers_window, style="Triggers.TButton")
        triggers_button.grid(row=0, column=7, padx=5, pady=5)
        
        # Add the Keep Alive checkbox
        keep_alive_check = ttk.Checkbutton(self.conn_frame, text="Keep Alive", variable=self.keep_alive_enabled, command=self.toggle_keep_alive)
        keep_alive_check.grid(row=0, column=8, padx=5, pady=5)

        # Checkbox frame for visibility toggles
        checkbox_frame = ttk.Frame(top_frame)
        checkbox_frame.grid(row=2, column=0, columnspan=5, sticky="ew", padx=5, pady=5)

        # Checkbox to show/hide Connection Settings
        conn_check = ttk.Checkbutton(checkbox_frame, text="Show Connection Settings", variable=self.show_connection_settings, command=self.toggle_connection_settings)
        conn_check.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # Checkbox to show/hide Username
        username_check = ttk.Checkbutton(checkbox_frame, text="Show Username", variable=self.show_username, command=self.toggle_username)
        username_check.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # Checkbox to show/hide Password
        password_check = ttk.Checkbutton(checkbox_frame, text="Show Password", variable=self.show_password, command=self.toggle_password)
        password_check.grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        
        # Username frame
        self.username_frame = ttk.LabelFrame(top_frame, text="Username")
        self.username_frame.grid(row=3, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        self.username_entry = ttk.Entry(self.username_frame, textvariable=self.username, width=30)
        self.username_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_context_menu(self.username_entry)
        self.remember_username_check = ttk.Checkbutton(self.username_frame, text="Remember", variable=self.remember_username)
        self.remember_username_check.pack(side=tk.LEFT, padx=5, pady=5)
        self.send_username_button = ttk.Button(self.username_frame, text="Send", command=self.send_username)
        self.send_username_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Password frame
        self.password_frame = ttk.LabelFrame(top_frame, text="Password")
        self.password_frame.grid(row=4, column=0, columnspan=5, sticky="ew", padx=5, pady=5)
        self.password_entry = ttk.Entry(self.password_frame, textvariable=self.password, width=30, show="*")
        self.password_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_context_menu(self.password_entry)
        self.remember_password_check = ttk.Checkbutton(self.password_frame, text="Remember", variable=self.remember_password)
        self.remember_password_check.pack(side=tk.LEFT, padx=5, pady=5)
        self.send_password_button = ttk.Button(self.password_frame, text="Send", command=self.send_password)
        self.send_password_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # --- Row 1: Paned container for BBS Output and Messages to You ---
        paned_container = ttk.Frame(main_frame)
        paned_container.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        paned_container.columnconfigure(0, weight=1)
        paned_container.rowconfigure(0, weight=1)
        
        self.paned = tk.PanedWindow(paned_container, orient=tk.VERTICAL, sashwidth=10, sashrelief=tk.RAISED)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # Top pane: BBS Output
        self.output_frame = ttk.LabelFrame(self.paned, text="BBS Output")
        self.paned.add(self.output_frame)
        self.paned.paneconfig(self.output_frame, minsize=200)  # Set minimum size for the top pane
        self.terminal_display = tk.Text(self.output_frame, wrap=tk.WORD, state=tk.DISABLED, bg="black", font=("Courier New", 10))
        self.terminal_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_bar = ttk.Scrollbar(self.output_frame, command=self.terminal_display.yview)
        scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_display.configure(yscrollcommand=scroll_bar.set)
        self.define_ansi_tags()
        self.terminal_display.tag_configure("hyperlink", foreground="blue", underline=True)
        self.terminal_display.tag_bind("hyperlink", "<Button-1>", self.open_hyperlink)
        self.terminal_display.tag_bind("hyperlink", "<Enter>", self.show_thumbnail_preview)
        self.terminal_display.tag_bind("hyperlink", "<Leave>", self.hide_thumbnail_preview)
        
        # Bottom pane: Messages to You
        messages_frame = ttk.LabelFrame(self.paned, text="Messages to You")
        self.paned.add(messages_frame)
        self.paned.paneconfig(messages_frame, minsize=100)  # Set minimum size for the bottom pane
        self.directed_msg_display = tk.Text(messages_frame, wrap=tk.WORD, state=tk.DISABLED, bg="lightyellow", font=("Courier New", 10, "bold"))
        self.directed_msg_display.pack(fill=tk.BOTH, expand=True)
        self.directed_msg_display.tag_configure("hyperlink", foreground="blue", underline=True)
        self.directed_msg_display.tag_bind("hyperlink", "<Button-1>", self.open_directed_message_hyperlink)
        self.directed_msg_display.tag_bind("hyperlink", "<Enter>", self.show_directed_message_thumbnail_preview)
        self.directed_msg_display.tag_bind("hyperlink", "<Leave>", self.hide_thumbnail_preview)
        
        # --- Row 2: Input frame for sending messages ---
        input_frame = ttk.LabelFrame(main_frame, text="Send Message")
        input_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.input_var = tk.StringVar()
        self.input_box = ttk.Entry(input_frame, textvariable=self.input_var, width=80)
        self.input_box.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        self.input_box.bind("<Return>", self.send_message)
        self.create_context_menu(self.input_box)
        self.send_button = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.update_display_font()

    def configure_button_styles(self):
        """Configure custom styles for buttons."""
        style = ttk.Style()
        
        # Enable themed widgets to use ttk styles
        style.theme_use('default')
        
        # Configure default style settings for all states
        def configure_button_style(name, bg, fg="white"):
            # Create custom style
            style.configure(
                f"{name}.TButton",
                foreground=fg,
                background=bg,
                bordercolor=bg,
                darkcolor=bg,
                lightcolor=bg,
                font=("Arial", 9, "bold"),
                relief="raised",
                padding=(10, 5)
            )
            
            # Map the same colors to all states
            style.map(
                f"{name}.TButton",
                foreground=[("pressed", fg), ("active", fg)],
                background=[("pressed", bg), ("active", bg)],
                bordercolor=[("pressed", bg), ("active", bg)],
                relief=[("pressed", "sunken"), ("active", "raised")]
            )
        
        # Connection button styles (dynamic green/red)
        configure_button_style("Connect", "#28a745")  # Green
        configure_button_style("Disconnect", "#dc3545")  # Red
        
        # Action buttons (playful colors)
        configure_button_style("Wave", "#17a2b8")     # Blue
        configure_button_style("Smile", "#ffc107", "black")  # Yellow with black text
        configure_button_style("Dance", "#e83e8c")    # Pink
        configure_button_style("Bow", "#6f42c1")      # Purple
        
        # Utility buttons
        configure_button_style("Chatlog", "#007bff")   # Blue
        configure_button_style("Favorites", "#fd7e14")  # Orange
        configure_button_style("Settings", "#6c757d")   # Gray
        configure_button_style("Triggers", "#20c997")   # Teal

    def toggle_all_sections(self):
        """Toggle visibility of all sections based on the master checkbox."""
        show = self.show_all.get()
        self.show_connection_settings.set(show)
        self.show_username.set(show)
        self.show_password.set(show)
        self.toggle_connection_settings()
        self.toggle_username()
        self.toggle_password()

    def toggle_connection_settings(self):
        """Toggle visibility of the Connection Settings section."""
        if self.show_connection_settings.get():
            self.conn_frame.grid()
        else:
            self.conn_frame.grid_remove()
        self.update_paned_size()

    def toggle_username(self):
        """Toggle visibility of the Username section."""
        if self.show_username.get():
            self.username_frame.grid()
        else:
            self.username_frame.grid_remove()
        self.update_paned_size()

    def toggle_password(self):
        """Toggle visibility of the Password section."""
        if self.show_password.get():
            self.password_frame.grid()
        else:
            self.password_frame.grid_remove()
        self.update_paned_size()

    def update_paned_size(self):
        """Update the size of the paned window based on the visibility of sections."""
        total_height = 200  # Base height for the BBS Output pane
        if not self.show_connection_settings.get():
            total_height += 50
        if not self.show_username.get():
            total_height += 50
        if not self.show_password.get():
            total_height += 50
        self.paned.paneconfig(self.output_frame, minsize=total_height)

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

    def create_members_context_menu(self):
        """Create a right-click context menu for the members listbox."""
        menu = tk.Menu(self.members_listbox, tearoff=0)
        menu.add_command(label="Chatlog", command=self.show_member_chatlog)

        def show_context_menu(event):
            menu.tk_popup(event.x_root, event.y_root)

        self.members_listbox.bind("<Button-3>", show_context_menu)

    def show_member_chatlog(self):
        """Show the chatlog for the selected member."""
        selected_index = self.members_listbox.curselection()
        if selected_index:
            username = self.members_listbox.get(selected_index)
            self.show_chatlog_window()
            self.select_chatlog_user(username)

    def select_chatlog_user(self, username):
        """Select the specified user in the chatlog listbox."""
        for i in range(self.chatlog_listbox.size()):
            if self.chatlog_listbox.get(i) == username:
                self.chatlog_listbox.selection_set(i)
                self.chatlog_listbox.see(i)
                self.display_chatlog_messages(None)
                break

    def toggle_all_sections(self):
        """Toggle visibility of all sections based on the master checkbox."""
        show = self.show_all.get()
        self.show_connection_settings.set(show)
        self.show_username.set(show)
        self.show_password.set(show)
        self.toggle_connection_settings()
        self.toggle_username()
        self.toggle_password()

    def toggle_connection_settings(self):
        """Toggle visibility of the Connection Settings section."""
        if self.show_connection_settings.get():
            self.conn_frame.grid()
        else:
            self.conn_frame.grid_remove()
        self.update_paned_size()

    def toggle_username(self):
        """Toggle visibility of the Username section."""
        if self.show_username.get():
            self.username_frame.grid()
        else:
            self.username_frame.grid_remove()
        self.update_paned_size()

    def toggle_password(self):
        """Toggle visibility of the Password section."""
        if self.show_password.get():
            self.password_frame.grid()
        else:
            self.password_frame.grid_remove()
        self.update_paned_size()

    def update_paned_size(self):
        """Update the size of the paned window based on the visibility of sections."""
        total_height = 200  # Base height for the BBS Output pane
        if not self.show_connection_settings.get():
            total_height += 50
        if not self.show_username.get():
            total_height += 50
        if not self.show_password.get():
            total_height += 50
        self.paned.paneconfig(self.output_frame, minsize=total_height)

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
        """Update all text widgets' fonts with current settings."""
        try:
            font_settings = {
                'font': (self.font_name.get(), self.font_size.get()),
                'fg': self.current_font_settings.get('fg', 'white'),
                'bg': self.current_font_settings.get('bg', 'black')
            }
            self.terminal_display.configure(**font_settings)
            self.directed_msg_display.configure(**font_settings)
            self.members_listbox.configure(**font_settings)
            self.actions_listbox.configure(**font_settings)
        except Exception as e:
            print(f"Error updating display font: {e}")

    # 1.4️⃣ ANSI PARSING
    def define_ansi_tags(self):
        """Define text tags for basic ANSI foreground colors (30-37, 90-97) and custom colors."""
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
            '97': 'bright_white',
            '38': 'grey'  # Custom tag for grey color
        }

        for code, tag in color_map.items():
            if tag == 'blue':
                # Use a lighter blue instead of the default dark blue
                self.terminal_display.tag_configure(tag, foreground="#3399FF")
            elif tag == 'grey':
                # Set grey color to a visible shade
                self.terminal_display.tag_configure(tag, foreground="#B0B0B0")
            elif tag.startswith("bright_"):
                base_color = tag.split("_", 1)[1]
                self.terminal_display.tag_configure(tag, foreground=base_color)
            else:
                self.terminal_display.tag_configure(tag, foreground=tag)

    # 1.5️⃣ CONNECT / DISCONNECT
    def toggle_connection(self):
        """Connect or disconnect from the BBS."""
        if self.connected:
            self.connect_button.configure(style="Disconnect.TButton")
            self.send_custom_message('=x')
        else:
            self.connect_button.configure(style="Connect.TButton")
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
                encoding='cp437',  # Use 'latin1' if your BBS uses it
                cols=self.cols,    # Use the configured number of columns
                rows=self.rows     # Use the configured number of rows
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
        """Accumulate data, split on newlines, and process each complete line."""
        # Normalize newlines
        data = data.replace('\r\n', '\n').replace('\r', '\n')
        self.partial_line += data
        lines = self.partial_line.split("\n")
        
        # Precompile an ANSI escape code regex
        ansi_regex = re.compile(r'\x1b\[[0-9;]*m')
        
        for line in lines[:-1]:
            # Remove ANSI codes for filtering purposes only.
            clean_line = ansi_regex.sub('', line).strip()
            
            # --- Filter header lines ---
            if self.collecting_users:
                self.user_list_buffer.append(line)
                if "are here with you." in clean_line:
                    self.update_chat_members(self.user_list_buffer)
                    self.collecting_users = False
                    self.user_list_buffer = []
                # continue  # Skip displaying header lines
            
            if clean_line.startswith("You are in"):
                self.user_list_buffer = [line]
                self.collecting_users = True
                # continue  # Skip displaying header line
            
            # Skip the line immediately following the header block if it starts with "Just press"
            # if clean_line.startswith("Just press") and not self.collecting_users:
            #     continue
            
            # --- Process directed messages ---
            directed_msg_match = re.match(r'^From\s+(\S+)\s+\((to you|whispered)\):\s*(.+)$', clean_line, re.IGNORECASE)
            if directed_msg_match:
                sender, _, message = directed_msg_match.groups()
                self.append_directed_message(f"From {sender}: {message}\n")
                self.play_ding_sound()  # Play ding sound for directed messages
                # Display directed messages in the main terminal as well
                self.append_terminal_text(line + "\n", "normal")
                continue
            
            # --- Detect and update Action List ---
            if clean_line.startswith("Action listing for:"):
                self.actions = []
                self.collecting_actions = True
                continue
            if clean_line == ":" and self.collecting_actions:
                self.update_actions_listbox()
                self.collecting_actions = False
                continue
            if self.collecting_actions:
                self.actions.extend(clean_line.split())
                self.update_actions_listbox()
                continue
            
            # --- Process and display non-header lines ---
            self.append_terminal_text(line + "\n", "normal")
            self.check_triggers(line)
            self.parse_and_save_chatlog_message(line)
            if self.auto_login_enabled.get() or self.logon_automation_enabled.get():
                self.detect_logon_prompt(line)
            
            # Play ding sound for any message
            if re.match(r'^From\s+\S+', clean_line, re.IGNORECASE):
                self.play_ding_sound()
        
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
        """Parse and save chat messages with timestamps in formats:
           - Public: 'From <username>: <message>'
           - DM:     'From <username> (to <recipient>): <message>'
        """
        # Remove any ANSI escape sequences that might interfere with matching.
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        
        # Skip non-user messages
        if any(phrase in clean_line for phrase in [
            "You are in the", "There is currently no one else here with you.", 
            'Just press "?" if you need any assistance.', ":join main"
        ]):
            return
        
        # Check if the line starts with "From <username>"
        match = re.match(r'^\s*From\s+(\S+)', clean_line, re.IGNORECASE)
        
        if match:
            sender = match.group(1)
            self.last_message_info = (sender, "")
            self.append_to_last_chatlog_message(sender, clean_line)
        elif self.last_message_info:
            sender, message = self.last_message_info
            if ':' in clean_line:
                # Append the line to the current message
                self.append_to_last_chatlog_message(sender, clean_line)
                # Check if this line contains the second colon
                if message.count(':') >= 2:
                    self.last_message_info = None
            else:
                # Append the line to the current message
                self.append_to_last_chatlog_message(sender, clean_line)

    def append_to_last_chatlog_message(self, username, extra_text):
        """Append extra_text to the last message logged for username."""
        chatlog = self.load_chatlog()
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ")
        if username in chatlog and chatlog[username]:
            chatlog[username][-1] += "\n" + timestamp + extra_text
        else:
            chatlog[username] = [timestamp + extra_text]
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

    def send_action(self, action):
        """Send an action to the BBS, optionally appending the highlighted username."""
        selected_indices = self.members_listbox.curselection()
        if selected_indices:
            username = self.members_listbox.get(selected_indices[0])
            action = f"{action} {username}"
        asyncio.run_coroutine_threadsafe(self._send_message(action + "\r\n"), self.loop)
        
        # Deselect the action after sending
        self.actions_listbox.selection_clear(0, tk.END)
        self.members_listbox.selection_clear(0, tk.END)

    # 1.7️⃣ KEEP-ALIVE
    async def keep_alive(self):
        """Send an <ENTER> keystroke every 10 seconds."""
        while not self.keep_alive_stop_event.is_set():
            if self.connected and self.writer:
                self.writer.write("\r\n")
                await self.writer.drain()
            await asyncio.sleep(60)

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
        url_regex = re.compile(r'(https?://\S+)')
        last_end = 0
        current_tag = "normal"

        for match in ansi_escape_regex.finditer(text_data):
            start, end = match.span()
            if start > last_end:
                segment = text_data[last_end:start]
                self.insert_with_hyperlinks(segment, current_tag)
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
            segment = text_data[last_end:]
            self.insert_with_hyperlinks(segment, current_tag)

    def insert_with_hyperlinks(self, text, tag):
        """Insert text with hyperlinks detected and tagged."""
        url_regex = re.compile(r'(https?://\S+)')
        last_end = 0
        for match in url_regex.finditer(text):
            start, end = match.span()
            if start > last_end:
                self.terminal_display.insert(tk.END, text[last_end:start], tag)
            self.terminal_display.insert(tk.END, text[start:end], ("hyperlink", tag))
            last_end = end
        if last_end < len(text):
            self.terminal_display.insert(tk.END, text[last_end:], tag)

    def insert_directed_message_with_hyperlinks(self, text, tag):
        """Insert directed message text with hyperlinks detected and tagged."""
        url_regex = re.compile(r'(https?://\S+)')
        last_end = 0
        for match in url_regex.finditer(text):
            start, end = match.span()
            if start > last_end:
                self.directed_msg_display.insert(tk.END, text[last_end:start], tag)
            self.directed_msg_display.insert(tk.END, text[start:end], ("hyperlink", tag))
            last_end = end
        if last_end < len(text):
            self.directed_msg_display.insert(tk.END, text[last_end:], tag)

    def open_hyperlink(self, event):
        """Open the hyperlink in a web browser."""
        index = self.terminal_display.index("@%s,%s" % (event.x, event.y))
        start_index = self.terminal_display.search("https://", index, backwards=True, stopindex="1.0")
        if not start_index:
            start_index = self.terminal_display.search("http://", index, backwards=True, stopindex="1.0")
        end_index = self.terminal_display.search(r"\s", start_index, stopindex="end", regexp=True)
        if not end_index:
            end_index = self.terminal_display.index("end")
        url = self.terminal_display.get(start_index, end_index).strip()
        webbrowser.open(url)

    def open_directed_message_hyperlink(self, event):
        """Open the hyperlink in a web browser from directed messages."""
        index = self.directed_msg_display.index("@%s,%s" % (event.x, event.y))
        start_index = self.directed_msg_display.search("https://", index, backwards=True, stopindex="1.0")
        if not start_index:
            start_index = self.directed_msg_display.search("http://", index, backwards=True, stopindex="1.0")
        end_index = self.directed_msg_display.search(r"\s", start_index, stopindex="end", regexp=True)
        if not end_index:
            end_index = self.directed_msg_display.index("end")
        url = self.directed_msg_display.get(start_index, end_index).strip()
        webbrowser.open(url)

    def show_thumbnail_preview(self, event):
        """Show a thumbnail preview of the hyperlink."""
        index = self.terminal_display.index("@%s,%s" % (event.x, event.y))
        start_index = self.terminal_display.search("https://", index, backwards=True, stopindex="1.0")
        end_index = self.terminal_display.search(r"\s", index, stopindex="end", regexp=True)
        if not end_index:
            end_index = self.terminal_display.index("end")
        url = self.terminal_display.get(start_index, end_index).strip()
        self.show_thumbnail(url, event)

    def show_directed_message_thumbnail_preview(self, event):
        """Show a thumbnail preview of the hyperlink from directed messages."""
        index = self.directed_msg_display.index("@%s,%s" % (event.x, event.y))
        start_index = self.directed_msg_display.search("https://", index, backwards=True, stopindex="1.0")
        end_index = self.directed_msg_display.search(r"\s", index, stopindex="end", regexp=True)
        if not end_index:
            end_index = self.directed_msg_display.index("end")
        url = self.directed_msg_display.get(start_index, end_index).strip()
        self.show_thumbnail(url, event)

    def show_thumbnail(self, url, event):
        """Display a thumbnail preview near the mouse pointer."""
        if self.preview_window is not None:
            self.preview_window.destroy()

        self.preview_window = tk.Toplevel(self.master)
        self.preview_window.overrideredirect(True)
        self.preview_window.attributes("-topmost", True)

        # Position the preview window near the mouse pointer
        x = self.master.winfo_pointerx() + 10
        y = self.master.winfo_pointery() + 10
        self.preview_window.geometry(f"+{x}+{y}")

        label = tk.Label(self.preview_window, text="Loading preview...", background="white")
        label.pack()

        # Fetch and display the thumbnail in a separate thread
        threading.Thread(target=self._fetch_and_display_thumbnail, args=(url, label), daemon=True).start()

    def _fetch_and_display_thumbnail(self, url, label):
        """Fetch and display the thumbnail. Handle GIFs and static images."""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")

            # Check if the URL is a GIF or another image type
            if "image" in content_type:
                image_data = BytesIO(response.content)

                # Process GIF
                if "gif" in content_type or url.endswith(".gif"):
                    gif = Image.open(image_data)
                    frames = []
                    try:
                        while True:
                            frame = gif.copy()
                            frame.thumbnail((200, 150))  # Resize
                            frames.append(ImageTk.PhotoImage(frame))
                            gif.seek(len(frames))  # Move to next frame
                    except EOFError:
                        pass  # End of GIF frames

                    if frames:
                        self._display_animated_gif(frames, label)
                    return

                # Process static images
                image = Image.open(image_data)
                image.thumbnail((200, 150))
                photo = ImageTk.PhotoImage(image)

                def update_label():
                    if self.preview_window and label.winfo_exists():
                        label.config(image=photo, text="")
                        label.image = photo  # Keep reference to avoid garbage collection
                self.master.after(0, update_label)

        except Exception as e:
            print(f"DEBUG: Exception in _fetch_and_display_thumbnail: {e}")
            def update_label_error():
                if self.preview_window and label.winfo_exists():
                    label.config(text="Preview not available")
            self.master.after(0, update_label_error)

    def _display_animated_gif(self, frames, label):
        """Display animated GIF in the label."""
        def animate(index):
            if self.preview_window and label.winfo_exists():
                label.config(image=frames[index])
                index = (index + 1) % len(frames)
                label.image = frames[index]  # Keep reference
                label.after(100, animate, index)  # Adjust speed as needed

        self.master.after(0, animate, 0)

    def hide_thumbnail_preview(self, event):
        """Hide the thumbnail preview."""
        if self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None

    def get_thumbnail(self, url):
        """Attempt to load a thumbnail image from an image URL.
           Returns a PhotoImage if successful, otherwise None.
        """
        if any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif"]):
            try:
                response = requests.get(url, timeout=5)
                image_data = response.content
                image = Image.open(BytesIO(image_data))
                image.thumbnail((200, 200))  # Set thumbnail size as needed.
                return ImageTk.PhotoImage(image)
            except Exception as e:
                print("Error loading thumbnail:", e)
        return None

    def show_preview(self, event, url):
        """Display a live preview thumbnail in a small Toplevel near the mouse pointer."""
        photo = self.get_thumbnail(url)
        if photo:
            self.preview_window = tk.Toplevel(self.master)
            self.preview_window.overrideredirect(True)
            self.preview_window.attributes("-topmost", True)
            label = tk.Label(self.preview_window, image=photo, bd=1, relief="solid")
            label.image = photo  # keep a reference to avoid garbage collection
            label.pack()
            x = event.x_root + 10
            y = event.y_root + 10
            self.preview_window.geometry(f"+{x}+{y}")

    def hide_preview(self, event):
        """Hide the preview window if it exists."""
        if hasattr(self, 'preview_window') and self.preview_window:
            self.preview_window.destroy()
            self.preview_window = None

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
        """Open a Toplevel window to manage chatlog and hyperlinks."""
        if self.chatlog_window and self.chatlog_window.winfo_exists():
            self.chatlog_window.lift()
            return

        self.chatlog_window = tk.Toplevel(self.master)
        self.chatlog_window.title("Chatlog")
        self.chatlog_window.geometry("1200x600")  # Slightly wider default size
        
        # Make the window resizable
        self.chatlog_window.columnconfigure(0, weight=1)
        self.chatlog_window.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.chatlog_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Create paned window to hold all panels
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.grid(row=0, column=0, sticky="nsew")

        # Left panel - Users list (25% width)
        users_frame = ttk.Frame(paned)
        users_frame.columnconfigure(0, weight=1)
        users_frame.rowconfigure(1, weight=1)
        
        ttk.Label(users_frame, text="Users").grid(row=0, column=0, sticky="w")
        self.chatlog_listbox = tk.Listbox(users_frame, height=10)
        self.chatlog_listbox.grid(row=1, column=0, sticky="nsew")
        users_scrollbar = ttk.Scrollbar(users_frame, command=self.chatlog_listbox.yview)
        users_scrollbar.grid(row=1, column=1, sticky="ns")
        self.chatlog_listbox.configure(yscrollcommand=users_scrollbar.set)
        self.chatlog_listbox.bind("<<ListboxSelect>>", self.display_chatlog_messages)
        
        paned.add(users_frame, weight=25)

        # Middle panel - Messages (50% width)
        messages_frame = ttk.Frame(paned)
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(1, weight=1)
        
        ttk.Label(messages_frame, text="Messages").grid(row=0, column=0, sticky="w")
        self.chatlog_display = tk.Text(messages_frame, wrap=tk.WORD, state=tk.DISABLED,
                                     bg="white", font=("Courier New", 10))
        self.chatlog_display.grid(row=1, column=0, sticky="nsew")
        messages_scrollbar = ttk.Scrollbar(messages_frame, command=self.chatlog_display.yview)
        messages_scrollbar.grid(row=1, column=1, sticky="ns")
        self.chatlog_display.configure(yscrollcommand=messages_scrollbar.set)
        
        paned.add(messages_frame, weight=50)

        # Right panel - Hyperlinks (25% width)
        links_frame = ttk.Frame(paned)
        links_frame.columnconfigure(0, weight=1)
        links_frame.rowconfigure(1, weight=1)
        
        ttk.Label(links_frame, text="Hyperlinks").grid(row=0, column=0, sticky="w")
        self.links_display = tk.Text(links_frame, wrap=tk.WORD, state=tk.DISABLED,
                                   bg="lightyellow", font=("Courier New", 10))
        self.links_display.grid(row=1, column=0, sticky="nsew")
        links_scrollbar = ttk.Scrollbar(links_frame, command=self.links_display.yview)
        links_scrollbar.grid(row=1, column=1, sticky="ns")
        self.links_display.configure(yscrollcommand=links_scrollbar.set)
        
        self.links_display.tag_configure("hyperlink", foreground="blue", underline=True)
        self.links_display.tag_bind("hyperlink", "<Button-1>", self.open_chatlog_hyperlink)
        self.links_display.tag_bind("hyperlink", "<Enter>", self.show_chatlog_thumbnail_preview)
        self.links_display.tag_bind("hyperlink", "<Leave>", self.hide_thumbnail_preview)
        
        paned.add(links_frame, weight=25)

        # Buttons frame at bottom
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, sticky="ew", pady=5)
        
        ttk.Button(buttons_frame, text="Clear Chat", command=self.confirm_clear_chatlog).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear Links", command=self.confirm_clear_links).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Show All", command=self.show_all_messages).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Close", command=self.chatlog_window.destroy).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Change Font", command=self.show_change_font_window).pack(side=tk.RIGHT, padx=5)  # New button for changing font and colors

        self.load_chatlog_list()
        self.display_stored_links()

    def show_change_font_window(self):
        """Open a Toplevel window to change font, font size, font color, and background color."""
        font_window = tk.Toplevel(self.master)
        font_window.title("Change Font Settings")
        font_window.geometry("800x600")
        font_window.grab_set()  # Make window modal

        # Store current selections
        self.current_selections = {
            'font': None,
            'size': None,
            'color': None,
            'bg': None
        }
        
        main_frame = ttk.Frame(font_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for i in range(4):
            main_frame.columnconfigure(i, weight=1)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)
        
        # Font selection
        font_frame = ttk.LabelFrame(main_frame, text="Font")
        font_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        font_frame.rowconfigure(0, weight=1)
        font_frame.columnconfigure(0, weight=1)
        
        self.font_listbox = tk.Listbox(font_frame, exportselection=False)  # Add exportselection=False
        self.font_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        font_scroll = ttk.Scrollbar(font_frame, orient="vertical", command=self.font_listbox.yview)
        font_scroll.grid(row=0, column=1, sticky="ns")
        self.font_listbox.configure(yscrollcommand=font_scroll.set)
        
        # Extended font list with DOS/Terminal themed fonts
        fonts = [
            "Courier New",
            "Consolas",
            "Terminal",
            "Fixedsys",
            "System",
            "Modern DOS 8x16",
            "Modern DOS 8x8",
            "Perfect DOS VGA 437",
            "MS Gothic",
            "SimSun-ExtB",
            "NSimSun",
            "Lucida Console",
            "OCR A Extended",
            "Prestige Elite Std",
            "Letter Gothic Std",
            "FreeMono",
            "DejaVu Sans Mono",
            "Liberation Mono",
            "IBM Plex Mono",
            "PT Mono",
            "Share Tech Mono",
            "VT323",
            "Press Start 2P",
            "DOS/V",
            "TerminalVector"
        ]
        
        for font in fonts:
            self.font_listbox.insert(tk.END, font)
        
        # Font size selection
        size_frame = ttk.LabelFrame(main_frame, text="Size")
        size_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        size_frame.rowconfigure(0, weight=1)
        size_frame.columnconfigure(0, weight=1)
        
        self.size_listbox = tk.Listbox(size_frame, exportselection=False)  # Add exportselection=False
        self.size_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        size_scroll = ttk.Scrollbar(size_frame, orient="vertical", command=self.size_listbox.yview)
        size_scroll.grid(row=0, column=1, sticky="ns")
        self.size_listbox.configure(yscrollcommand=size_scroll.set)
        
        sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36]
        for size in sizes:
            self.size_listbox.insert(tk.END, size)
        
        # Font color selection
        color_frame = ttk.LabelFrame(main_frame, text="Font Color")
        color_frame.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        color_frame.rowconfigure(0, weight=1)
        color_frame.columnconfigure(0, weight=1)
        
        self.color_listbox = tk.Listbox(color_frame, exportselection=False)  # Add exportselection=False
        self.color_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        color_scroll = ttk.Scrollbar(color_frame, orient="vertical", command=self.color_listbox.yview)
        color_scroll.grid(row=0, column=1, sticky="ns")
        self.color_listbox.configure(yscrollcommand=color_scroll.set)
        
        colors = ["black", "white", "red", "green", "blue", "yellow", "magenta", "cyan", 
                 "gray70", "gray50", "gray30", "orange", "purple", "brown", "pink"]
        for color in colors:
            self.color_listbox.insert(tk.END, color)
            self.color_listbox.itemconfigure(colors.index(color), {'bg': color})
        
        # Background color selection
        bg_frame = ttk.LabelFrame(main_frame, text="Background Color")
        bg_frame.grid(row=0, column=3, padx=5, pady=5, sticky="nsew")
        bg_frame.rowconfigure(0, weight=1)
        bg_frame.columnconfigure(0, weight=1)
        
        self.bg_listbox = tk.Listbox(bg_frame, exportselection=False)  # Add exportselection=False
        self.bg_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        bg_scroll = ttk.Scrollbar(bg_frame, orient="vertical", command=self.bg_listbox.yview)
        bg_scroll.grid(row=0, column=1, sticky="ns")
        self.bg_listbox.configure(yscrollcommand=bg_scroll.set)
        
        bg_colors = ["white", "black", "gray90", "gray80", "gray70", "lightyellow", 
                     "lightblue", "lightgreen", "azure", "ivory", "honeydew", "lavender"]
        for bg in bg_colors:
            self.bg_listbox.insert(tk.END, bg)
            self.bg_listbox.itemconfigure(bg_colors.index(bg), {'bg': bg})
        
        # Add selection event handlers
        def on_select(event, category):
            widget = event.widget
            try:
                selection = widget.get(widget.curselection())
                self.current_selections[category] = selection
            except (tk.TclError, TypeError):
                pass  # No selection
        
        self.font_listbox.bind('<<ListboxSelect>>', lambda e: on_select(e, 'font'))
        self.size_listbox.bind('<<ListboxSelect>>', lambda e: on_select(e, 'size'))
        self.color_listbox.bind('<<ListboxSelect>>', lambda e: on_select(e, 'color'))
        self.bg_listbox.bind('<<ListboxSelect>>', lambda e: on_select(e, 'bg'))
        
        # Buttons frame at the bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=4, pady=10)
        
        ttk.Button(button_frame, text="Save", command=lambda: self.save_font_settings(font_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=font_window.destroy).pack(side=tk.LEFT, padx=5)
        
        # Set initial selections
        current_font = self.chatlog_display.cget("font").split()[0]
        current_size = int(self.chatlog_display.cget("font").split()[1])
        current_fg = self.chatlog_display.cget("fg")
        current_bg = self.chatlog_display.cget("bg")
        
        # Initialize current_selections with current values
        self.current_selections = {
            'font': current_font,
            'size': current_size,
            'color': current_fg,
            'bg': current_bg
        }
        
        # Set initial selections in listboxes
        if current_font in fonts:
            self.font_listbox.selection_set(fonts.index(current_font))
            self.font_listbox.see(fonts.index(current_font))
        
        if current_size in sizes:
            self.size_listbox.selection_set(sizes.index(current_size))
            self.size_listbox.see(sizes.index(current_size))
        
        if current_fg in colors:
            self.color_listbox.selection_set(colors.index(current_fg))
            self.color_listbox.see(colors.index(current_fg))
        
        if current_bg in bg_colors:
            self.bg_listbox.selection_set(bg_colors.index(current_bg))
            self.bg_listbox.see(bg_colors.index(current_bg))

    def save_font_settings(self, window):
        """Save the selected font settings and apply them to all text displays."""
        try:
            if not all(self.current_selections.values()):
                tk.messagebox.showerror("Error", "Please select an option from each list")
                return
                
            # Create font settings dictionary
            font_settings = {
                'font': (self.current_selections['font'], self.current_selections['size']),
                'fg': self.current_selections['color'],
                'bg': self.current_selections['bg']
            }
            
            # Apply to all text displays
            self.chatlog_display.configure(**font_settings)
            self.directed_msg_display.configure(**font_settings)
            self.members_listbox.configure(**font_settings)
            self.actions_listbox.configure(**font_settings)
            
            # Store settings for future use
            self.current_font_settings = font_settings
            
            # Save to file
            settings_to_save = {
                'font_name': self.current_selections['font'],
                'font_size': self.current_selections['size'],
                'fg': self.current_selections['color'],
                'bg': self.current_selections['bg']
            }
            with open("font_settings.json", "w") as file:
                json.dump(settings_to_save, file)
            
            window.destroy()
        except Exception as e:
            tk.messagebox.showerror("Error", f"Error applying settings: {str(e)}")

    def confirm_clear_chatlog(self):
        """Show confirmation dialog before clearing chatlog."""
        selected_index = self.chatlog_listbox.curselection()
        if not selected_index:
            return
            
        username = self.chatlog_listbox.get(selected_index)
        if tk.messagebox.askyesno("Confirm Clear", 
                                 f"Are you sure you want to clear the chatlog for {username}?",
                                 icon='warning'):
            self.clear_active_chatlog()

    def confirm_clear_links(self):
        """Show confirmation dialog before clearing links history."""
        if tk.messagebox.askyesno("Confirm Clear", 
                                 "Are you sure you want to clear all stored hyperlinks?",
                                 icon='warning'):
            self.clear_links_history()

    def load_chatlog_list(self):
        """Load chatlog from a local file and populate the listbox."""
        chatlog = self.load_chatlog()
        self.chatlog_listbox.delete(0, tk.END)
        for username in chatlog.keys():
            self.chatlog_listbox.insert(tk.END, username)

    def display_chatlog_messages(self, event):
        """Display messages for the selected user or all messages if no user is selected."""
        selected_index = self.chatlog_listbox.curselection()
        chatlog = self.load_chatlog()
        self.chatlog_display.configure(state=tk.NORMAL)
        self.chatlog_display.delete(1.0, tk.END)
        
        if selected_index:
            # Show messages for selected user
            username = self.chatlog_listbox.get(selected_index)
            messages = chatlog.get(username, [])
            for message in messages:
                # Format: [timestamp] From <username>: message
                if not message.strip().startswith('['):  # Add timestamp if missing
                    message = time.strftime("[%Y-%m-%d %H:%M:%S] ") + message
                if not "From" in message[:message.find(':') if ':' in message else len(message)]:
                    message = message.replace(']', '] From ' + username + ':')
                self.chatlog_display.insert(tk.END, message + "\n")
        else:
            # Show all messages sorted by timestamp
            all_messages = []
            for username, messages in chatlog.items():
                for msg in messages:
                    # Format: [timestamp] From <username>: message
                    if not msg.strip().startswith('['):  # Add timestamp if missing
                        msg = time.strftime("[%Y-%m-%d %H:%M:%S] ") + msg
                    if not "From" in msg[:msg.find(':') if ':' in msg else len(msg)]:
                        msg = msg.replace(']', '] From ' + username + ':')
                    all_messages.append((msg, username))
            
            # Sort messages by timestamp
            def get_timestamp(msg_tuple):
                timestamp_match = re.match(r'\[(.*?)\]', msg_tuple[0])
                return timestamp_match.group(1) if timestamp_match else ""
            
            all_messages.sort(key=lambda x: get_timestamp(x))
            
            # Display all messages
            for message, _ in all_messages:
                self.chatlog_display.insert(tk.END, f"{message}\n")
        
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
        
        # First extract the section between "Topic:" and "are here with you"
        match = re.search(r'Topic:.*?(?=\s+are here with you\.)', combined_clean, re.DOTALL | re.IGNORECASE)
        if not match:
            return
            
        user_section = match.group(0)
        
        # Remove the "Topic:" part and any parenthetical content
        user_section = re.sub(r'Topic:.*?\)', '', user_section, flags=re.DOTALL)
        user_section = re.sub(r'\(.*?\)', '', user_section)
        
        # Split by commas and "and", clean up each part
        parts = re.split(r',\s*|\s+and\s+', user_section)
        
        final_usernames = set()
        for part in parts:
            # Extract username part from email-like format
            username = part.strip()
            if '@' in username:
                username = username.split('@')[0]
            
            # Only accept usernames that:
            # 1. Are not common words
            # 2. Are at least 2 characters
            # 3. Start with a letter
            # 4. Contain only letters, numbers, dots, underscores
            if (len(username) >= 2 and 
                username.lower() not in {'in', 'the', 'chat', 'general', 'channel', 'topic'} and
                re.match(r'^[A-Za-z][A-Za-z0-9._]*$', username)):
                final_usernames.add(username)

        print(f"[DEBUG] Extracted usernames: {final_usernames}")
        self.chat_members = final_usernames

        # Update last seen timestamps
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
        """Append text to the directed messages display with a timestamp."""
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ")
        self.directed_msg_display.configure(state=tk.NORMAL)
        self.insert_directed_message_with_hyperlinks(timestamp + text + "\n", "normal")
        self.directed_msg_display.see(tk.END)
        self.directed_msg_display.configure(state=tk.DISABLED)

    def play_ding_sound(self):
        """Play a standard ding sound effect."""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

    def update_actions_listbox(self):
        """Update the Actions listbox with the current actions."""
        self.actions_listbox.delete(0, tk.END)
        for action in self.actions:
            self.actions_listbox.insert(tk.END, action)

    def on_action_select(self, event):
        """Handle action selection and send the action to the highlighted username."""
        selected_action_index = self.actions_listbox.curselection()
        selected_member_index = self.members_listbox.curselection()
        
        if selected_action_index and selected_member_index:
            action = self.actions_listbox.get(selected_action_index[0])
            username = self.members_listbox.get(selected_member_index[0])
            
            # Format and send the action command
            action_command = f"{action} {username}"
            if self.connected and self.writer:
                asyncio.run_coroutine_threadsafe(
                    self._send_message(action_command + "\r\n"), 
                    self.loop
                )
                
                # Deselect the action after sending
                self.actions_listbox.selection_clear(0, tk.END)
                self.members_listbox.selection_clear(0, tk.END)

    def store_hyperlink(self, url, sender="Unknown", timestamp=None):
        """Store a hyperlink with metadata."""
        if timestamp is None:
            timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        
        links = self.load_links_history()
        links.append({
            "url": url,
            "sender": sender,
            "timestamp": timestamp
        })
        self.save_links_history(links)
        
        # Update links display if window is open
        if self.chatlog_window and self.chatlog_window.winfo_exists():
            self.display_stored_links()

    def load_links_history(self):
        """Load stored hyperlinks from file."""
        if os.path.exists("hyperlinks.json"):
            with open("hyperlinks.json", "r") as file:
                return json.load(file)
        return []

    def save_links_history(self, links):
        """Save hyperlinks to file."""
        with open("hyperlinks.json", "w") as file:
            json.dump(links, file)

    def clear_links_history(self):
        """Clear all stored hyperlinks."""
        self.save_links_history([])
        if self.chatlog_window and self.chatlog_window.winfo_exists():
            self.display_stored_links()

    def display_stored_links(self):
        """Display stored hyperlinks in the links panel."""
        if not hasattr(self, 'links_display'):
            return

        self.links_display.configure(state=tk.NORMAL)
        self.links_display.delete(1.0, tk.END)
        
        links = self.load_links_history()
        for link in links:
            timestamp = link.get("timestamp", "")
            sender = link.get("sender", "Unknown")
            url = link.get("url", "")
            
            self.links_display.insert(tk.END, f"{timestamp} from {sender}:\n")
            self.links_display.insert(tk.END, f"{url}\n\n", "hyperlink")
        
        self.links_display.configure(state=tk.DISABLED)

    def open_chatlog_hyperlink(self, event):
        """Handle clicking a hyperlink in the chatlog links panel."""
        index = self.links_display.index("@%s,%s" % (event.x, event.y))
        for tag_name in self.links_display.tag_names(index):
            if tag_name == "hyperlink":
                line_start = self.links_display.index(f"{index} linestart")
                line_end = self.links_display.index(f"{index} lineend")
                url = self.links_display.get(line_start, line_end).strip()
                webbrowser.open(url)
                break

    def show_chatlog_thumbnail_preview(self, event):
        """Show thumbnail preview for links in the chatlog links panel."""
        index = self.links_display.index("@%s,%s" % (event.x, event.y))
        for tag_name in self.links_display.tag_names(index):
            if tag_name == "hyperlink":
                line_start = self.links_display.index(f"{index} linestart")
                line_end = self.links_display.index(f"{index} lineend")
                url = self.links_display.get(line_start, line_end).strip()
                self.show_thumbnail(url, event)
                break

    def parse_and_store_hyperlinks(self, message, sender=None):
        """Extract and store hyperlinks from a message."""
        url_pattern = re.compile(r'(https?://\S+)')
        urls = url_pattern.findall(message)
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        
        for url in urls:
            self.store_hyperlink(url, sender, timestamp)

    def show_all_messages(self):
        """Deselect user and show all messages combined."""
        self.chatlog_listbox.selection_clear(0, tk.END)
        self.display_chatlog_messages(None)

    def load_font_settings(self):
        """Load font settings from a local file or return defaults."""
        try:
            if os.path.exists("font_settings.json"):
                with open("font_settings.json", "r") as file:
                    return json.load(file)
        except Exception as e:
            print(f"Error loading font settings: {e}")
        return {
            'font_name': "Courier New",
            'font_size': 10,
            'fg': 'white',
            'bg': 'black'
        }

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
