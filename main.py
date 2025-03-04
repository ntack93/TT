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
import random
from ASCII_EXT import create_cp437_to_unicode_map  # Import the function from ASCII_EXT.py
from init_config import init_config_files, verify_sound_files  # Add this line
import traceback

try:
    import enchant
except ImportError:
    enchant = None


###############################################################################
#                         BBS Telnet App (No Chatbot)
###############################################################################



class BBSTerminalApp:
    def __init__(self, master):
        # Initialize sound-related attributes first
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.chat_sound_file = os.path.join(script_dir, "chat.wav")
        self.directed_sound_file = os.path.join(script_dir, "directed.wav")
        self.current_sound = None
        self.last_sound_time = 0
        
        print(f"[DEBUG] Chat sound path: {self.chat_sound_file}")
        print(f"[DEBUG] Directed sound path: {self.directed_sound_file}")
        
        # Add at the start of __init__
        self.show_messages_to_you = tk.BooleanVar(value=True)
        self.actions_request_lock = asyncio.Lock()
        # 1.0️⃣ 🎉 SETUP
        self.master = master
        self.master.title("Retro BBS Terminal")
        
        # Add sound file paths
        self.chat_sound_file = os.path.join(os.path.dirname(__file__), "chat.wav")
        self.directed_sound_file = os.path.join(os.path.dirname(__file__), "directed.wav")

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
        self.keep_alive_minutes = tk.StringVar(value="1")
        self.keep_alive_seconds = tk.StringVar(value="0")

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

        self.majorlink_mode = tk.BooleanVar(value=True)  # True = filtering enabled
        self.pbx_mode = tk.BooleanVar(value=False)

        # Add frame size tracking
        self.frame_sizes = self.load_frame_sizes()
        
        # Add settings persistence
        self.saved_settings = self.load_saved_settings()
        
        # Create StringVar with max length for input
        self.input_var = tk.StringVar()
        self.input_var.trace('w', self.limit_input_length)

        # Add blink state tracking
        self.blink_state = False
        self.blink_tags = set()

        self.paned = None  # Initialize paned attribute

        self.first_banner_seen = False  # Add new flag to track first banner
        self.actions_requested = False  # Keep existing flag
        self.last_banner_time = 0  # Add new timestamp tracker

        self.has_requested_actions = False  # Track if we've already requested actions this session

        # At the beginning of __init__, after creating self.master
        self.spell = None  # Spell checker instance
        self.spell_popup = None  # Popup window for suggestions
        self.autocorrect_enabled = tk.BooleanVar(value=True)  # Toggle for autocorrect
        
        # Add spell checking suggestion tracking
        self.current_suggestion = None
        self.current_misspelled = None
        
        # Initialize spell checker
        try:
            if enchant:
                self.spell = enchant.Dict("en_US")
        except Exception as e:
            print("Error initializing spell checker:", e)
            self.spell = None

        # Add page notifications pattern
        self.page_pattern = re.compile(r'(\w+) is paging you from (\w+): (.+)')
        
        # Add current sound tracking
        self.current_sound = None

        # Add escape handling variables
        self.escape_count = 0
        self.escape_timer = None

        # Add new variable for Messages to You visibility
        self.show_messages_to_you = tk.BooleanVar(value=True)

        # Add missing show_messages_to_you attribute early in initialization
        self.show_messages_to_you = tk.BooleanVar(value=True)

        # Add new state tracking variables
        self.actions_list_requested = False
        self.banner_seen_this_session = False
        self.last_banner_time = 0

        # Add command history tracking
        self.command_history = []
        self.command_index = -1
        self.current_command = ""  # Store current input when browsing history
        
        # Add mousewheel handler
        self.current_scrollable_frame = None

        # Add session state tracking
        self.actions_requested_this_session = False
        self.current_topic = ""

        # Add command history support
        self.command_history = self.load_command_history()
        self.command_index = -1
        self.current_command = ""

        # 1.BUILD UI
        self.build_ui()

        # Periodically check for incoming telnet data
        self.master.after(100, self.process_incoming_messages)

        # Start the periodic task to refresh chat members
        self.master.after(5000, self.refresh_chat_members)

        self.cp437_map = create_cp437_to_unicode_map()

    def build_ui(self):
        """Creates all the frames and widgets for the UI."""
        # Configure button styles
        self.configure_button_styles()
        
        # Create a main PanedWindow container
        container = ttk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        container.pack(fill=tk.BOTH, expand=True)

        # Create the main UI frame on the LEFT with weight 3
        main_frame = ttk.Frame(container, name='main_frame')
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=3)
        main_frame.rowconfigure(2, weight=0)
        container.add(main_frame, weight=3)

        # Define default width for side panels (1.5 inches * 96 DPI)
        default_panel_width = 130

        # Create the Chatroom Members panel in the MIDDLE with fixed width
        members_frame = ttk.LabelFrame(container, text="Chatroom Members", width=default_panel_width)
        members_frame.pack_propagate(False)  # Prevent frame from shrinking
        self.members_canvas = tk.Canvas(members_frame, highlightthickness=0)
        self.members_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        members_scrollbar = ttk.Scrollbar(members_frame, orient=tk.VERTICAL, 
                                         command=self.members_canvas.yview)
        members_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.members_canvas.configure(yscrollcommand=members_scrollbar.set)
        
        self.members_frame = ttk.Frame(self.members_canvas)
        self.members_canvas.create_window((0, 0), window=self.members_frame, 
                                        anchor=tk.NW, tags="self.members_frame")
        
        def on_configure(event):
            self.members_canvas.configure(scrollregion=self.members_canvas.bbox("all"))
        
        self.members_frame.bind('<Configure>', on_configure)
        container.add(members_frame, weight=0)  # Set weight to 0 to maintain fixed width

        # Create the Actions listbox on the RIGHT with fixed width
        actions_frame = ttk.LabelFrame(container, text="Actions", width=default_panel_width)
        actions_frame.pack_propagate(False)  # Prevent frame from shrinking
        self.actions_canvas = tk.Canvas(actions_frame, highlightthickness=0)
        self.actions_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        actions_scrollbar = ttk.Scrollbar(actions_frame, orient=tk.VERTICAL, 
                                         command=self.actions_canvas.yview)
        actions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.actions_canvas.configure(yscrollcommand=actions_scrollbar.set)
        
        self.actions_frame = ttk.Frame(self.actions_canvas)
        self.actions_canvas.create_window((0, 0), window=self.actions_frame, 
                                        anchor=tk.NW, tags="self.actions_frame")
        
        def on_actions_configure(event):
            self.actions_canvas.configure(scrollregion=self.actions_canvas.bbox("all"))
        
        self.actions_frame.bind('<Configure>', on_actions_configure)
        container.add(actions_frame, weight=0)  # Set weight to 0 to maintain fixed width

        # Set initial pane sizes after window is drawn
        def set_initial_sizes():
            container.update()
            total_width = container.winfo_width()
            main_width = total_width - (2 * default_panel_width)
            container.sashpos(0, main_width)  # Position between main and members
            container.sashpos(1, main_width + default_panel_width)  # Position between members and actions

        self.master.after(100, set_initial_sizes)

        # --- Row 0: Top frame (connection settings, username, password) ---
        top_frame = ttk.Frame(main_frame)
        top_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        
        # Master checkbox to show/hide all sections
        master_check = ttk.Checkbutton(top_frame, text="Show All", variable=self.show_all, command=self.toggle_all_sections)
        master_check.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        # Create a container frame for the action buttons to keep them together
        action_buttons_frame = ttk.Frame(top_frame)
        action_buttons_frame.grid(row=0, column=1, sticky="w", padx=5)
        
        # Add Teleconference Action buttons with minimal spacing
        wave_button = ttk.Button(action_buttons_frame, text="Wave", 
                                command=lambda: self.send_action("wave"), style="Wave.TButton")
        wave_button.pack(side=tk.LEFT, padx=1)
        
        smile_button = ttk.Button(action_buttons_frame, text="Smile", 
                                 command=lambda: self.send_action("smile"), style="Smile.TButton")
        smile_button.pack(side=tk.LEFT, padx=1)
        
        dance_button = ttk.Button(action_buttons_frame, text="Dance", 
                                 command=lambda: self.send_action("dance"), style="Dance.TButton")
        dance_button.pack(side=tk.LEFT, padx=1)
        
        bow_button = ttk.Button(action_buttons_frame, text="Bow", 
                               command=lambda: self.send_action("bow"), style="Bow.TButton")
        bow_button.pack(side=tk.LEFT, padx=(1, 10))  # Extra right padding to separate from utility buttons

        # Utility buttons in their own frame
        util_buttons_frame = ttk.Frame(top_frame)
        util_buttons_frame.grid(row=0, column=2, sticky="w")
        
        tele_button = ttk.Button(util_buttons_frame, text="Go Teleconference", 
                                command=lambda: self.send_custom_message("/go tele"), 
                                style="Teleconference.TButton")
        tele_button.pack(side=tk.LEFT, padx=2)
        
        brb_button = ttk.Button(util_buttons_frame, text="BRB", 
                               command=lambda: self.send_custom_message("ga will be right back!"), 
                                style="BRB.TButton")
        brb_button.pack(side=tk.LEFT, padx=2)
        
        chatlog_button = ttk.Button(util_buttons_frame, text="Chatlog", 
                                   command=self.show_chatlog_window, style="Chatlog.TButton")
        chatlog_button.pack(side=tk.LEFT, padx=2)

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
        favorites_button = ttk.Button(self.conn_frame, text="Favorites", 
                                    command=self.show_favorites_window, 
                                    style="Favorites.TButton")
        favorites_button.grid(row=0, column=5, padx=5, pady=5)
        
        # Add the Triggers button
        triggers_button = ttk.Button(self.conn_frame, text="Triggers", 
                                   command=self.show_triggers_window, 
                                   style="Triggers.TButton")
        triggers_button.grid(row=0, column=6, padx=5, pady=5)

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

        # Add MajorLink Mode checkbox
        majorlink_check = ttk.Checkbutton(
            checkbox_frame, 
            text="MajorLink Mode", 
            variable=self.majorlink_mode,
            command=self.toggle_majorlink_mode
        )
        majorlink_check.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)
        
        pbx_check = ttk.Checkbutton(
            checkbox_frame,
            text="PBX Mode",
            variable=self.pbx_mode,
            command=self.toggle_pbx_mode
        )
        pbx_check.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)

        # Add the Keep Alive checkbox
        keep_alive_frame = ttk.Frame(self.conn_frame)
        keep_alive_frame.grid(row=0, column=8, padx=5, pady=5)
        
        keep_alive_check = ttk.Checkbutton(keep_alive_frame, text="Keep Alive", 
                                         variable=self.keep_alive_enabled, 
                                         command=self.toggle_keep_alive)
        keep_alive_check.pack(side=tk.LEFT)

        # Add timing controls
        timing_frame = ttk.Frame(keep_alive_frame)
        timing_frame.pack(side=tk.LEFT)
        
        minutes_entry = ttk.Entry(timing_frame, textvariable=self.keep_alive_minutes, 
                                width=2, justify='center')
        minutes_entry.pack(side=tk.LEFT, padx=(2, 0))
        ttk.Label(timing_frame, text="m").pack(side=tk.LEFT)
        
        seconds_entry = ttk.Entry(timing_frame, textvariable=self.keep_alive_seconds, 
                                width=2, justify='center')
        seconds_entry.pack(side=tk.LEFT, padx=(2, 0))
        ttk.Label(timing_frame, text="s").pack(side=tk.LEFT)

        # Add validation
        def validate_time(var, new_value):
            if new_value == "": return True
            try:
                value = int(new_value)
                if var == self.keep_alive_minutes:
                    return 0 <= value <= 59
                else:  # seconds
                    return 0 <= value <= 59
            except ValueError:
                return False
                
        minutes_entry.config(validate='key', 
            validatecommand=(self.master.register(
                lambda new_val: validate_time(self.keep_alive_minutes, new_val)), '%P'))
        seconds_entry.config(validate='key',
            validatecommand=(self.master.register(
                lambda new_val: validate_time(self.keep_alive_seconds, new_val)), '%P'))

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
        
        # Switch to tk.PanedWindow with specific size and relief
        self.paned = tk.PanedWindow(paned_container, orient=tk.VERTICAL, 
                               sashwidth=5, sashrelief=tk.RAISED,
                               height=400, width=600)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # Top pane: BBS Output with explicit minimum height
        self.output_frame = ttk.LabelFrame(self.paned, text="Terminal")
        self.paned.add(self.output_frame, minsize=200, stretch="always")
        self.terminal_display = tk.Text(self.output_frame, wrap=tk.WORD, state=tk.DISABLED, bg="black", font=("Courier New", 10))
        self.terminal_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scroll_bar = ttk.Scrollbar(self.output_frame, command=self.terminal_display.yview)
        scroll_bar.pack(side=tk.RIGHT, fill=tk.Y)
        self.terminal_display.configure(yscrollcommand=self.on_scroll_change)
        self.define_ansi_tags()
        self.terminal_display.tag_configure("hyperlink", foreground="blue", underline=True)
        self.terminal_display.tag_bind("hyperlink", "<Button-1>", self.open_hyperlink)
        self.terminal_display.tag_bind("hyperlink", "<Enter>", self.show_thumbnail_preview)
        self.terminal_display.tag_bind("hyperlink", "<Leave>", self.hide_thumbnail_preview)
        
        # Bottom pane: Messages to You
        self.messages_frame = ttk.LabelFrame(self.paned, text="Messages to You") 
        self.paned.add(self.messages_frame, minsize=100)
        self.directed_msg_display = tk.Text(self.messages_frame, wrap=tk.WORD, state=tk.DISABLED, bg="lightyellow", font=("Courier New", 10, "bold"))
        self.directed_msg_display.pack(fill=tk.BOTH, expand=True)
        self.directed_msg_display.tag_configure("hyperlink", foreground="blue", underline=True)
        self.directed_msg_display.tag_bind("hyperlink", "<Button-1>", self.open_directed_message_hyperlink)
        self.directed_msg_display.tag_bind("hyperlink", "<Enter>", self.show_directed_message_thumbnail_preview)
        self.directed_msg_display.tag_bind("hyperlink", "<Leave>", self.hide_thumbnail_preview)
        
        # --- Row 2: Input frame for sending messages ---
        input_frame = ttk.LabelFrame(main_frame, text="Send Message")
        input_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=5, pady=5)
        self.input_box = ttk.Entry(input_frame, textvariable=self.input_var, width=80)
        self.input_box.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        # Only bind Return event, remove any other bindings
        self.input_box.bind("<Return>", self.send_message)
        self.create_context_menu(self.input_box)
        # Make send button use command instead of bind
        self.send_button = ttk.Button(input_frame, text="Send", command=lambda: self.send_message(None))
        self.send_button.pack(side=tk.LEFT, padx=5, pady=5)

        # In the input frame section, after creating input_box
        ttk.Checkbutton(
            input_frame, 
            text="Autocorrect", 
            variable=self.autocorrect_enabled
        ).pack(side=tk.LEFT, padx=5)

        # Add escape key binding to input box
        self.input_box.bind("<Escape>", self.handle_escape)

        # Configure style for suggestion buttons
        style = ttk.Style()
        style.configure(
            "Spell.TButton",
            foreground="darkblue",
            background="white",
            font=("Arial VGA 437", 9),
            padding=(5, 2)
        )
        
        self.setup_autocorrect()
        
        # Restore frame sizes if saved
        if 'paned_pos' in self.frame_sizes:
            pos = self.frame_sizes['paned_pos']
            # Use different method based on paned window type
            if isinstance(self.paned, ttk.PanedWindow):
                self.master.after(100, lambda: self.paned.sashposition(0, pos))
            else:
                self.master.after(100, lambda: self.paned.sash_place(0, pos, 0))

        self.update_display_font()

        # In the checkbox_frame section, add back the Messages to You checkbox:
        # After the PBX Mode checkbox
        pbx_check = ttk.Checkbutton(
            checkbox_frame,
            text="PBX Mode",
            variable=self.pbx_mode,
            command=self.toggle_pbx_mode
        )
        pbx_check.grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)

        # Add Messages to You checkbox
        messages_check = ttk.Checkbutton(
            checkbox_frame,
            text="Messages to You",
            variable=self.show_messages_to_you,
            command=self.toggle_messages_frame
        )
        messages_check.grid(row=0, column=5, padx=5, pady=5, sticky=tk.W)

        # At the end of build_ui, apply saved settings
        self.master.after(100, self.apply_saved_settings)

        # Modify input box bindings for command history
        self.input_box.bind("<Up>", self.previous_command)
        self.input_box.bind("<Down>", self.next_command)
        
        # Add focus bindings for input box to preserve partial input
        self.input_box.bind("<FocusOut>", self.save_current_input)
        self.input_box.bind("<FocusIn>", self.restore_current_input)

        # Fix mousewheel binding in update_actions_listbox
        def on_mousewheel(event):
            if self.current_scrollable_frame == self.actions_canvas:
                self.actions_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def on_enter_frame(event):
            self.current_scrollable_frame = self.actions_canvas
            self.master.bind_all("<MouseWheel>", on_mousewheel)

        def on_leave_frame(event):
            if self.current_scrollable_frame == self.actions_canvas:
                self.current_scrollable_frame = None
                self.master.unbind_all("<MouseWheel>")

        self.actions_canvas.bind("<Enter>", on_enter_frame)
        self.actions_canvas.bind("<Leave>", on_leave_frame)

    def configure_button_styles(self):
        """Configure custom styles for buttons including bubbles."""
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
                font=("Arial VGA 437", 9, "bold"),
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

        # Add new button styles
        configure_button_style("Teleconference", "#20c997")  # Teal
        configure_button_style("BRB", "#6610f2")  # Purple

        # Configure bubble styles
        style.configure("Bubble.TButton",
            padding=(10, 5),
            relief="raised",
            background="#f0f0f0",
            borderwidth=2,
            font=("Arial VGA 437", 9))
            
        style.configure("BubbleHover.TButton",
            padding=(10, 5),
            relief="raised",
            background="#e0e0e0",
            borderwidth=2,
            font=("Arial VGA 437", 9))
            
        style.configure("BubbleSelected.TButton",
            padding=(10, 5),
            relief="sunken",
            background="#d0d0d0",
            borderwidth=2,
            font=("Arial VGA 437", 9))

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
    def show_chatlog_window(self):
        """Open a Toplevel window to manage chatlog and hyperlinks."""
        if self.chatlog_window and self.chatlog_window.winfo_exists():
            self.chatlog_window.lift()
            self.chatlog_window.attributes('-topmost', True)
            return

        # Load saved font settings
        saved_font_settings = self.load_font_settings()
        chatlog_font_settings = {
            'font': (saved_font_settings.get('font_name', "Courier New"), 
                    saved_font_settings.get('font_size', 10)),
            'fg': saved_font_settings.get('fg', 'white'),
            'bg': saved_font_settings.get('bg', 'black')
        }

        # Load saved panel sizes or use defaults
        panel_sizes = self.load_panel_sizes()

        self.chatlog_window = tk.Toplevel(self.master)
        self.chatlog_window.title("Chatlog")
        self.chatlog_window.geometry("1200x600")
        self.chatlog_window.attributes('-topmost', True)
        
        # Make the window resizable
        self.chatlog_window.columnconfigure(0, weight=1)
        self.chatlog_window.rowconfigure(0, weight=1)

        main_frame = ttk.Frame(self.chatlog_window)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)

        # Create paned window with users/messages/links panels
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL, name="main_paned")
        paned.grid(row=0, column=0, sticky="nsew")

        # Users panel
        users_frame = ttk.Frame(paned, width=panel_sizes["users"])
        users_frame.pack_propagate(False)  # Prevent shrinking below specified width
        users_frame.columnconfigure(0, weight=1)
        users_frame.rowconfigure(1, weight=1)
        
        ttk.Label(users_frame, text="Users").grid(row=0, column=0, sticky="w")
        self.chatlog_listbox = tk.Listbox(users_frame, height=10, **chatlog_font_settings)
        self.chatlog_listbox.grid(row=1, column=0, sticky="nsew")
        users_scrollbar = ttk.Scrollbar(users_frame, command=self.chatlog_listbox.yview)
        users_scrollbar.grid(row=1, column=1, sticky="ns")
        self.chatlog_listbox.configure(yscrollcommand=users_scrollbar.set)
        self.chatlog_listbox.bind("<<ListboxSelect>>", self.display_chatlog_messages)
        
        paned.add(users_frame)

        # Messages panel (takes remaining space)
        messages_frame = ttk.Frame(paned)
        messages_frame.columnconfigure(0, weight=1)
        messages_frame.rowconfigure(1, weight=1)
        
        ttk.Label(messages_frame, text="Messages").grid(row=0, column=0, sticky="w")
        self.chatlog_display = tk.Text(messages_frame, wrap=tk.WORD, state=tk.DISABLED,
                                 **chatlog_font_settings)
        self.chatlog_display.grid(row=1, column=0, sticky="nsew")
        messages_scrollbar = ttk.Scrollbar(messages_frame, command=self.chatlog_display.yview)
        messages_scrollbar.grid(row=1, column=1, sticky="ns")
        self.chatlog_display.configure(yscrollcommand=messages_scrollbar.set)
        
        paned.add(messages_frame)

        # Links panel
        links_frame = ttk.Frame(paned, width=panel_sizes["links"])
        links_frame.pack_propagate(False)  # Prevent shrinking below specified width
        links_frame.columnconfigure(0, weight=1)
        links_frame.rowconfigure(1, weight=1)
        
        ttk.Label(links_frame, text="Hyperlinks").grid(row=0, column=0, sticky="w")
        self.links_display = tk.Text(links_frame, wrap=tk.WORD, state=tk.DISABLED,
                               **chatlog_font_settings)
        self.links_display.grid(row=1, column=0, sticky="nsew")
        links_scrollbar = ttk.Scrollbar(links_frame, command=self.links_display.yview)
        links_scrollbar.grid(row=1, column=1, sticky="ns")
        self.links_display.configure(yscrollcommand=links_scrollbar.set)
        
        self.links_display.tag_configure("hyperlink", foreground="blue", underline=True)
        self.links_display.tag_bind("hyperlink", "<Button-1>", self.open_chatlog_hyperlink)
        self.links_display.tag_bind("hyperlink", "<Enter>", self.show_chatlog_thumbnail_preview)
        self.links_display.tag_bind("hyperlink", "<Leave>", self.hide_thumbnail_preview)
        
        paned.add(links_frame)

        # Set initial sash positions based on saved sizes
        def after_show():
            total_width = paned.winfo_width()
            users_width = panel_sizes["users"]
            links_width = panel_sizes["links"]
            messages_width = total_width - users_width - links_width
            
            # Set sash positions
            paned.sashpos(0, users_width)  # Position between users and messages
            paned.sashpos(1, users_width + messages_width)  # Position between messages and links

        # Wait for window to be drawn before setting sash positions
        self.chatlog_window.after(100, after_show)

        # Save sizes when window is closed
        self.chatlog_window.protocol("WM_DELETE_WINDOW", 
            lambda: (self.save_panel_sizes(), self.chatlog_window.destroy()))

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
        self.create_chatlog_context_menu()

        self.master.after(100, self.show_all_messages)

    def save_font_settings(self, window):
        """Save the selected font settings and apply them to terminal displays only."""
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
            
            # Apply only to terminal displays
            self.chatlog_display.configure(**font_settings)
            self.directed_msg_display.configure(**font_settings)
            
            # For BBS Output, only update font, not colors
            self.terminal_display.configure(font=(self.current_selections['font'], 
                                               self.current_selections['size']))
            
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

    # 1.4️⃣ ANSI PARSING
    def define_ansi_tags(self):
        """Define text tags for ANSI colors and attributes including blink."""
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

        # Add blink tags
        self.terminal_display.tag_configure("blink", background="")
        self.blink_tags = set()
    
        # Start blink timer
        self.blink_timer()

        # Ensure color tags have priority over other tags
        for tag in self.get_all_color_tags():
            if hasattr(self.terminal_display, 'tag_raise'):
                self.terminal_display.tag_raise(tag)

    def blink_timer(self):
        """Toggle blink state every 500ms."""
        self.blink_state = not self.blink_state
        
        # Update all blinking text
        for tag in self.blink_tags:
            if self.blink_state:
                self.terminal_display.tag_configure(tag, background="grey20")
            else:
                self.terminal_display.tag_configure(tag, background="")
        
        # Schedule next blink
        self.master.after(500, self.blink_timer)

    def get_all_color_tags(self):
        """Return a set of all possible color tags."""
        return {
            'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white',
            'bright_black', 'bright_red', 'bright_green', 'bright_yellow',
            'bright_blue', 'bright_magenta', 'bright_cyan', 'bright_white'
        }

    def parse_ansi_and_insert(self, text_data):
        """Enhanced parser for ANSI codes including blink and overlapping colors."""
        ansi_escape_regex = re.compile(r'\x1b\[(.*?)m')
        last_end = 0
        current_tags = ["normal"]
        color_stack = []
        blink_tag = None

        for match in ansi_escape_regex.finditer(text_data):
            start, end = match.span()
            if start > last_end:
                segment = text_data[last_end:start]
                # Insert without hyperlink processing for Terminal display
                self.terminal_display.insert(tk.END, segment, tuple(current_tags))
            
            code_string = match.group(1)
            codes = code_string.split(';')
            
            # Handle reset code
            if '0' in codes or not codes:
                current_tags = ["normal"]
                color_stack = []
                blink_tag = None
                codes = [code for code in codes if code not in ['0', '']]

            for code in codes:
                if code in ['5', '6']:  # Blink codes
                    if not blink_tag:
                        blink_tag = f"blink_{len(self.blink_tags)}"
                        self.terminal_display.tag_configure(blink_tag, background="")
                        self.blink_tags.add(blink_tag)
                    if blink_tag not in current_tags:
                        current_tags.append(blink_tag)
                else:
                    # Handle color codes
                    mapped_tag = self.map_code_to_tag(code)
                    if mapped_tag and mapped_tag not in current_tags:
                        # Remove any existing color tags
                        current_tags = [tag for tag in current_tags if tag not in self.get_all_color_tags()]
                        current_tags.append(mapped_tag)
                        # Update color stack
                        color_stack.append(mapped_tag)

            last_end = end

        # Insert any remaining text
        if last_end < len(text_data):
            segment = text_data[last_end:]
            self.terminal_display.insert(tk.END, segment, tuple(current_tags))

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
        """Start the telnetlib3 client and handle automated logon if enabled."""
        host = self.host.get()
        port = self.port.get()
        self.stop_event.clear()

        # Reset flags
        self.first_banner_seen = False
        self.actions_requested = False

        # Reset session state
        self.actions_requested_this_session = False
        self.current_topic = ""

        def run_telnet():
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.telnet_client_task(host, port))

        thread = threading.Thread(target=run_telnet, daemon=True)
        thread.start()
        self.append_terminal_text(f"Connecting to {host}:{port}...\n", "normal")
        self.start_keep_alive()

        # Start automated logon sequence if enabled
        if self.logon_automation_enabled.get():
            self.master.after(10000, self.automated_logon_sequence)

    def automated_logon_sequence(self):
        """Execute the automated logon sequence."""
        if not self.connected or not self.writer:
            return
            
        username = self.username.get()
        password = self.password.get()
        
        # Send username
        self.master.after(0, lambda: self.send_custom_message(username))
        
        # Send password after 2 seconds
        self.master.after(2000, lambda: self.send_custom_message(password))
        
        # Send first enter after 1 second
        self.master.after(3000, lambda: self.send_custom_message("\r\n"))
        
        # Send second enter after 1 second
        self.master.after(4000, lambda: self.send_custom_message("\r\n"))
        
        # Send third enter after 1 second
        self.master.after(5000, lambda: self.send_custom_message("/go chat"))
        
        # Send C after 1 second
        self.master.after(6000, lambda: self.send_custom_message("t"))

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
            self.reader = reader
            self.writer = writer
            self.connected = True
            self.connect_button.config(text="Disconnect")
            self.msg_queue.put_nowait(f"Connected to {host}:{port}\n")

            while not self.stop_event.is_set():
                try:
                    # Use shield to prevent cancellation during critical operations
                    data = await asyncio.shield(
                        asyncio.wait_for(reader.read(4096), timeout=30)
                    )
                    if not data:
                        break
                    self.msg_queue.put_nowait(data)
                except asyncio.TimeoutError:
                    continue
                except ConnectionResetError:
                    print("[DEBUG] Connection reset by peer")
                    break
                except Exception as e:
                    print(f"[DEBUG] Error reading data: {e}")
                    break

        except Exception as e:
            print(f"[DEBUG] Connection failed: {e}")
            self.msg_queue.put_nowait(f"Connection failed: {e}\n")
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
            
            # Clear the members list before disconnecting
            self.clear_chat_members()

            if self.writer:
                try:
                    # Send disconnect command if still connected
                    try:
                        self.writer.write('quit\r\n')
                        await self.writer.drain()
                    except Exception:
                        pass  # Ignore errors during quit command
                    
                    # Close the writer
                    if not self.writer.is_closing():
                        self.writer.close()
                        # Some telnet writers may not have wait_closed
                        if hasattr(self.writer, 'wait_closed'):
                            try:
                                await self.writer.wait_closed()
                            except Exception as e:
                                print("Warning: Error during wait_closed: {e}")
                        else:
                            # Give the writer a moment to finish closing
                            await asyncio.sleep(0.1)
                except Exception as e:
                    print(f"Warning: Error closing writer: {e}")

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

        # Reset the action request flag on disconnect
        self.has_requested_actions = False

    def clear_chat_members(self):
        """Clear the active chat members list but preserve last seen timestamps."""
        self.chat_members = set()
        self.save_chat_members_file()
        self.update_members_display()

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

    def decode_cp437(self, data):
        """Decode CP437 encoded text, preserving special characters"""
        # Convert bytes to list of integers if needed
        if isinstance(data, bytes):
            data = list(data)
        
        # Map each byte to its Unicode equivalent
        result = ''
        for byte in data:
            if byte in self.cp437_map:
                result += self.cp437_map[byte]
            else:
                result += chr(byte)
        
        return result

    def process_data_chunk(self, data):
        """Process incoming data with improved action list handling."""
        # Decode CP437 data
        if isinstance(data, bytes):
            data = self.decode_cp437(data)
        else:
            data = self.decode_cp437(data.encode('cp437'))
            
        # Normalize newlines
        data = data.replace('\r\n', '\n').replace('\r', '\n')
        self.partial_line += data
        lines = self.partial_line.split("\n")
        
        # Precompile an ANSI escape code regex
        ansi_regex = re.compile(r'\x1b\[[0-9;]*m')
        
        skip_display = False  # Flag to track if we're in a banner section
        
        # Add message tracking
        self.last_message = None
        
        for line in lines[:-1]:
            clean_line = ansi_regex.sub('', line).strip()
            
            # Handle banner detection and user list collection
            if any(x in clean_line for x in ["Topic:", "You are in"]):
                self.user_list_buffer = [line]
                self.collecting_users = True
                # Skip display if both PBX and Majorlink modes are enabled
                if self.pbx_mode.get() and self.majorlink_mode.get():
                    continue
            
            elif self.collecting_users:
                self.user_list_buffer.append(line)
                # More flexible end-of-banner detection
                if "you." in clean_line or "with you." in clean_line:
                    print("[DEBUG] Banner end detected, processing users")
                    self.update_chat_members(self.user_list_buffer)
                    self.collecting_users = False
                    self.user_list_buffer = []
                    
                    # Skip display in PBX mode
                    if self.pbx_mode.get():
                        continue
                    
                    # Trigger actions request after banner if not done this session
                    if not self.actions_requested_this_session:
                        current_time = time.time()
                        if current_time - self.last_banner_time > 5:
                            print("[DEBUG] First banner this session, requesting actions")
                            self.last_banner_time = current_time
                            self.actions_requested_this_session = True
                            self.master.after(500, self.request_actions_list)

            # First check for actions list
            if "Action listing for:" in clean_line:
                print("[DEBUG] Action listing header detected")
                self.actions = []
                self.collecting_actions = True
                continue
            elif self.collecting_actions:
                if clean_line == ":" or clean_line == "" or "Just press" in clean_line:
                    if self.actions:
                        print(f"[DEBUG] Finished collecting actions: {self.actions}")
                        self.collecting_actions = False
                        self.master.after_idle(self.update_actions_listbox)
                    continue
                    
                action_matches = re.findall(r'\b[A-Za-z]{2,}\b', clean_line)
                valid_actions = [
                    word for word in action_matches 
                    if (word.lower() not in {
                        'action', 'list', 'for', 'the', 'and', 'you', 'are',
                        'can', 'use', 'these', 'actions', 'available'
                    } and len(word) >= 2)
                ]
                    
                if valid_actions:
                    print(f"[DEBUG] Found valid actions: {valid_actions}")
                    self.actions.extend(valid_actions)
                continue

            # Check for user list in banner
            if "You are in" in clean_line and not self.collecting_users:
                self.user_list_buffer = [line]
                self.collecting_users = True
                
            elif self.collecting_users:
                self.user_list_buffer.append(line)
                if "are here with you." in clean_line:
                    self.update_chat_members(self.user_list_buffer)
                    self.collecting_users = False
                    self.user_list_buffer = []

            # Handle PBX mode
            display_line = True
            if self.pbx_mode.get():
                if self.process_pbx_line(clean_line, line):  # Pass original line
                    display_line = False  # Skip display if PBX line was processed
            
            # Handle MajorLink mode filtering
            elif self.majorlink_mode.get():
                if any(pattern in clean_line for pattern in [
                    "Topic:",
                    "Just press",
                    "are here with you"
                ]):
                    display_line = False

            # Display the line if it hasn't been filtered out
            if display_line and clean_line:
                self.append_terminal_text(line + "\n", "normal")
                self.check_triggers(line)
                # Save the cleaned message to the chatlog
                self.parse_and_save_chatlog_message(clean_line, line)

            # Check for entry messages and request actions if needed
            if (not self.has_requested_actions and 
                "You are in" in clean_line and 
                "are here with you" in clean_line):
                current_time = time.time()
                if current_time - self.last_banner_time > 5:
                    print("[DEBUG] Detected room entry, requesting actions list")
                    self.last_banner_time = current_time
                    self.has_requested_actions = True
                    self.master.after(500, self.request_actions_list)

        self.partial_line = lines[-1]

    def detect_logon_prompt(self, line):
        """Simple triggers to automate login if toggles are on."""
        lower_line = line.lower()
        # Typical BBS prompts
        if "enter your password:" in lower_line:
            self.master.after(500, self.send_password)
        elif "type it in and press enter" in lower_line or 'otherwise type "new":' in lower_line:
            self.master.after(500, self.send_username)

    def parse_and_save_chatlog_message(self, clean_line, original_line):
        """Parse and save chat messages with timestamps, handling both normal and PBX formats."""
        # Skip system messages and banner info
        skip_patterns = [
            r"You are in",
            r"Topic:",
            r"Just press",
            r"are here with you",
            r"^\s*$",  # Empty lines
            r"^\s*:.*$",  # Lines starting with colon (commands)
            r"^\s*\(.*\)\s*$"  # Lines containing only parenthetical content
        ]
        
        if any(re.search(pattern, clean_line, re.IGNORECASE) for pattern in skip_patterns):
            return

        # Check if message already has a timestamp
        has_timestamp = bool(re.match(r'^\[\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\]', clean_line))
        
        if self.pbx_mode.get():
            # Handle PBX format
            if self.process_pbx_line(clean_line, original_line):
                return
        
        # If not in PBX mode or if PBX parsing failed, use normal parsing
        # Enhanced patterns to match different message types
        message_patterns = [
            # Whispered messages - check these first
            r'^(?:\[[\d-]+\s+[\d:]+\]\s+)?From\s+(\S+?)(?:@[\w.-]+)?\s*\(whispered(?:\s+to\s+you)?\):\s*(.+)$',
            # Directed messages
            r'^(?:\[[\d-]+\s+[\d:]+\]\s+)?From\s+(\S+?)(?:@[\w.-]+)?\s*\(to\s+you\):\s*(.+)$',
            # Normal messages
            r'^(?:\[[\d-]+\s+[\d:]+\]\s+)?From\s+(\S+?)(?:\s+\([^)]+\))?\s*:\s*(.+)$'
        ]

        for pattern in message_patterns:
            message_match = re.match(pattern, clean_line, re.IGNORECASE)
            if message_match:
                sender = message_match.group(1)
                message = message_match.group(2)
                
                # Only add timestamp if not already present
                if not has_timestamp:
                    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ")
                    message_with_timestamp = f"{timestamp}From {sender}: {message}"
                else:
                    message_with_timestamp = clean_line

                # Check for directed message or whisper
                if "(whispered" in clean_line or "(to you)" in clean_line:
                    self.append_directed_message(message_with_timestamp)
                    self.play_directed_sound()
                else:
                    self.play_chat_sound()

                # Save to chatlog
                self.save_chatlog_message(sender, message_with_timestamp)
                # Extract any URLs (pass sender for attribution)
                self.parse_and_store_hyperlinks(message_with_timestamp, sender)
                break

    def send_message(self, event=None):
        """Send the user's typed message and manage command history."""
        if not self.connected or not self.writer:
            self.append_terminal_text("Not connected to any BBS.\n", "normal")
            return

        # Only apply autocorrect if escape wasn't pressed twice
        if self.escape_count < 2:
            # Apply top suggestion if available before sending
            if hasattr(self, 'current_suggestion') and self.current_suggestion:
                text = self.input_var.get()
                if self.current_misspelled in text:
                    text = text.rsplit(self.current_misspelled, 1)[0] + self.current_suggestion
                    self.input_var.set(text)

        # Reset autocorrect and escape state
        self.current_suggestion = None
        self.current_misspelled = None
        self.escape_count = 0
        if self.escape_timer:
            self.master.after_cancel(self.escape_timer)
            self.escape_timer = None

        user_input = self.input_var.get().strip()
        
        if user_input:
            # Add to command history if different from last command
            if not self.command_history or user_input != self.command_history[-1]:
                self.command_history.append(user_input)
                # Keep history to last 100 commands
                if len(self.command_history) > 100:
                    self.command_history.pop(0)
                self.save_command_history()

        # Clear input before sending
        self.input_var.set("")
        
        if not user_input:
            message = "\r\n"
        else:
            # Add prefix if mud mode enabled
            prefix = "Gos " if self.mud_mode.get() else ""
            message = prefix + user_input + "\r\n"

        # Send message using asyncio.run_coroutine_threadsafe
        if self.connected and self.writer:
            async def send():
                try:
                    self.writer.write(message)
                    await self.writer.drain()
                except Exception as e:
                    print(f"Error sending message: {e}")
                    
            asyncio.run_coroutine_threadsafe(send(), self.loop)

        # Only process non-empty messages
        if user_input:
            # Add to command history if different from last command
            if not self.command_history or user_input != self.command_history[-1]:
                self.command_history.append(user_input)
                # Keep history to last 100 commands
                if len(self.command_history) > 100:
                    self.command_history.pop(0)
            
            # Reset history browsing
            self.command_index = -1
            self.current_command = ""

    def send_username(self):
        """Send the username to the BBS."""
        if self.connected and self.writer:
            message = self.username.get() + "\r\n"
            self.writer.write(message)
            try:
                self.loop.call_soon_threadsafe(self.writer.drain)
                if self.remember_username.get():
                    self.save_username()
            except Exception as e:
                print(f"Error sending username: {e}")

    def send_password(self):
        """Send the password to the BBS."""
        if self.connected and self.writer:
            message = self.password.get() + "\r\n"
            self.writer.write(message)
            try:
                self.loop.call_soon_threadsafe(self.writer.drain)
                if self.remember_password.get():
                    self.save_password()
            except Exception as e:
                print(f"Error sending password: {e}")

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
        if self.connected and self.writer:
            message = message + "\r\n"
            async def send():
                try:
                    self.writer.write(message)
                    await self.writer.drain()
                except Exception as e:
                    print(f"Error sending custom message: {e}")
                    
            asyncio.run_coroutine_threadsafe(send(), self.loop)

    def send_action(self, action):
        """Send an action to the BBS, optionally appending the highlighted username."""
        if not self.connected or not self.writer:
            return
            
        if hasattr(self, 'selected_member') and self.selected_member:
            action = f"{action} {self.selected_member}"
            
        message = action + "\r\n"
        async def send():
            try:
                self.writer.write(message)
                await self.writer.drain()
                # Deselect the member after sending
                self.deselect_all_members()
            except Exception as e:
                print(f"Error sending action: {e}")
                
        asyncio.run_coroutine_threadsafe(send(), self.loop)

    # 1.7️⃣ KEEP-ALIVE
    async def keep_alive(self):
        """Send an <ENTER> keystroke at the specified interval."""
        while not self.keep_alive_stop_event.is_set():
            if self.connected and self.writer:
                self.writer.write("\r\n")
                await self.writer.drain()
            
            # Calculate total seconds from minutes and seconds
            try:
                minutes = int(self.keep_alive_minutes.get() or "0")
                seconds = int(self.keep_alive_seconds.get() or "0")
                total_seconds = (minutes * 60) + seconds
                if total_seconds < 1:  # Minimum 1 second
                    total_seconds = 60  # Default to 60 seconds
            except ValueError:
                total_seconds = 60  # Default if invalid values
                
            await asyncio.sleep(total_seconds)

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
            self.favorites_window.attributes('-topmost', True)
            return

        self.favorites_window = tk.Toplevel(self.master)
        self.favorites_window.title("Favorite BBS Addresses")
        self.favorites_window.attributes('-topmost', True)  # Keep window on top

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
            self.triggers_window.attributes('-topmost', True)
            return

        self.triggers_window = tk.Toplevel(self.master)
        self.triggers_window.title("Automation Triggers")
        self.triggers_window.attributes('-topmost', True)  # Keep window on top

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
        """Append text to the terminal display with ANSI parsing and hyperlink support."""
        self.terminal_display.configure(state=tk.NORMAL)
        
        # Handle ANSI codes first
        ansi_escape_regex = re.compile(r'\x1b\[(.*?)m')
        segments = ansi_escape_regex.split(text)
        
        current_tags = [default_tag]
        for i, segment in enumerate(segments):
            if i % 2 == 0:  # This is text content
                self.insert_with_hyperlinks(segment, tuple(current_tags))
            else:  # This is an ANSI code
                new_tag = self.map_code_to_tag(segment)
                if new_tag:
                    current_tags = [new_tag]
        
        self.terminal_display.see(tk.END)
        self.master.update_idletasks()
        self.terminal_display.configure(state=tk.DISABLED)

    def insert_with_hyperlinks(self, text, tags):
        """Enhanced hyperlink detection and insertion."""
        url_pattern = re.compile(r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)')
        last_end = 0
        
        for match in url_pattern.finditer(text):
            start, end = match.span()
            # Insert non-URL text
            if start > last_end:
                self.terminal_display.insert(tk.END, text[last_end:start], tags)
            
            # Clean and insert URL
            url = text[start:end].rstrip('.,;:)]}\'"')
            if url.startswith('www.'):
                url = 'http://' + url
            self.terminal_display.insert(tk.END, url, ("hyperlink",) + (tags if isinstance(tags, tuple) else (tags,)))
            
            last_end = end
        
        # Insert remaining text
        if last_end < len(text):
            self.terminal_display.insert(tk.END, text[last_end:], tags)

    def insert_directed_message_with_hyperlinks(self, text, tag):
        """Insert directed message text with hyperlinks detected and tagged."""
        url_pattern = re.compile(r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)')
        last_end = 0
        
        for match in url_pattern.finditer(text):
            start, end = match.span()
            # Insert non-URL text
            if start > last_end:
                self.directed_msg_display.insert(tk.END, text[last_end:start], tag)
            
            # Clean and insert URL
            url = text[start:end].rstrip('.,;:)]}\'"')
            if url.startswith('www.'):
                url = 'http://' + url
            self.directed_msg_display.insert(tk.END, url, ("hyperlink", tag))
            
            last_end = end
        
        # Insert remaining text
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

        # Start a new thread to fetch the preview
        threading.Thread(target=self._fetch_preview, args=(url, label), daemon=True).start()

    def _fetch_preview(self, url, label):
        """Fetch either an image thumbnail or website favicon."""
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            # Check if URL is directly an image
            if any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif']):
                response = requests.get(url, headers=headers, timeout=5)
                response.raise_for_status()
                self._handle_image_preview(response.content, label, is_gif=url.lower().endswith('.gif'))
            else:
                # Try to get webpage first to check for proper image content type
                response = requests.get(url, headers=headers, timeout=5)
                content_type = response.headers.get("Content-Type", "").lower()
                
                if "image" in content_type:
                    self._handle_image_preview(response.content, label, is_gif='gif' in content_type)
                else:
                    self._handle_website_preview(url, label)

        except Exception as e:
            print(f"DEBUG: Preview error: {e}")
            def update_label_error():
                if self.preview_window and label.winfo_exists():
                    label.config(text="Preview not available")
            self.master.after(0, update_label_error)

    def _handle_image_preview(self, image_data, label, is_gif=False):
        """Handle preview for image content, including GIFs."""
        try:
            image = Image.open(BytesIO(image_data))
            
            if is_gif and getattr(image, "is_animated", False):
                # Handle animated GIF
                frames = []
                try:
                    while True:
                        frame = image.copy()
                        frame.thumbnail((200, 150))
                        frames.append(ImageTk.PhotoImage(frame))
                        image.seek(len(frames))
                except EOFError:
                    pass
                
                if frames:
                    def animate(frame_index=0):
                        if self.preview_window and label.winfo_exists():
                            label.config(image=frames[frame_index])
                            label.image = frames[frame_index]  # Keep reference
                            next_frame = (frame_index + 1) % len(frames)
                            self.master.after(100, lambda: animate(next_frame))
                    
                    self.master.after(0, animate)
                    return
            else:
                # Handle static image
                image.thumbnail((200, 150))
                photo = ImageTk.PhotoImage(image)
                
                def update_label():
                    if self.preview_window and label.winfo_exists():
                        label.config(image=photo, text="")
                        label.image = photo
                self.master.after(0, update_label)
        except Exception as e:
            print(f"Image preview error: {e}")

    def _handle_website_preview(self, url, label):
        """Handle preview for website content by showing favicon."""
        try:
            # Parse the URL to get the base domain
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            favicon_url = f"{parsed_url.scheme}://{parsed_url.netloc}/favicon.ico"
            
            # Try to get the favicon
            response = requests.get(favicon_url, timeout=5)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                # Resize favicon to reasonable size
                image = image.resize((32, 32), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)

                def update_label():
                    if self.preview_window and label.winfo_exists():
                        label.config(image=photo, text=parsed_url.netloc)
                        label.image = photo
                self.master.after(0, update_label)
            else:
                raise Exception("Favicon not found")
        except Exception as e:
            print(f"Favicon preview error: {e}")
            # Show domain name if favicon fails
            parsed_url = urlparse(url)
            def update_label():
                if self.preview_window and label.winfo_exists():
                    label.config(text=parsed_url.netloc)
            self.master.after(0, update_label)

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

    def load_panel_sizes(self):
        """Load saved panel sizes from file."""
        try:
            if os.path.exists("panel_sizes.json"):
                with open("panel_sizes.json", "r") as file:
                    return json.load(file)
        except Exception as e:
            print(f"Error loading panel sizes: {e}")
        return {
            "users": 150,  # 15 chars * ~10 pixels per char
            "links": 300,  # 30 chars * ~10 pixels per char
        }

    def save_panel_sizes(self):
        """Save current panel sizes to file."""
        if not hasattr(self, 'chatlog_window') or not self.chatlog_window.winfo_exists():
            return
            
        try:
            # Get current sizes from the paned window
            paned = self.chatlog_window.nametowidget("main_paned")
            sash_pos1 = paned.sashpos(0)  # Position of first sash
            sash_pos2 = paned.sashpos(1)  # Position of second sash
            
            sizes = {
                "users": sash_pos1,
                "links": paned.winfo_width() - sash_pos2
            }
            
            with open("panel_sizes.json", "w") as file:
                json.dump(sizes, file)
        except Exception as e:
            print(f"Error saving panel sizes: {e}")

    def show_change_font_window(self):
        """Open a Toplevel window to change font, font size, font color, and background color."""
        font_window = tk.Toplevel(self.master)
        font_window.title("Change Font Settings")
        font_window.geometry("800x600")
        font_window.grab_set()  # Make window modal
        font_window.attributes('-topmost', True)  # Keep window on top

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

        # Safely get current font settings
        try:
            current_font = self.chatlog_display.cget("font")
            if isinstance(current_font, str):
                # Handle string format "family size"
                parts = current_font.split()
                current_font = parts[0]
                current_size = 10  # Default if can't parse size
                if len(parts) > 1:
                    try:
                        current_size = int(''.join(filter(str.isdigit, parts[1])))
                    except ValueError:
                        current_size = 10
            else:
                # Handle tuple format (family, size, ...)
                current_font = current_font[0]
                current_size = int(current_font[1]) if len(current_font) > 1 else 10
        except Exception as e:
            print(f"Error parsing font settings: {e}")
            current_font = "Courier New"
            current_size = 10

        current_fg = self.chatlog_display.cget("fg")
        current_bg = self.chatlog_display.cget("bg")
        
        # Initialize current_selections with current values
        self.current_selections = {
            'font': current_font,
            'size': current_size,
            'color': current_fg,
            'bg': current_bg
        }

    def confirm_clear_chatlog(self):
        """Show confirmation dialog before clearing chatlog."""
        selected_index = self.chatlog_listbox.curselection()
        if not selected_index:
            return
            
        username = self.chatlog_listbox.get(selected_index)
        
        confirm_dialog = tk.Toplevel(self.master)
        confirm_dialog.title("Confirm Clear")
        confirm_dialog.attributes('-topmost', True)
        confirm_dialog.grab_set()  # Make dialog modal
        
        msg = f"Are you sure you want to clear the chatlog for {username}?"
        tk.Label(confirm_dialog, text=msg, padx=20, pady=10).pack()
        
        def confirm():
            chatlog = self.load_chatlog()
            if username in chatlog:
                del chatlog[username]
                self.save_chatlog(chatlog)
            confirm_dialog.destroy()
            self.show_all_messages()
        
        def cancel():
            confirm_dialog.destroy()
        
        button_frame = ttk.Frame(confirm_dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Yes", command=confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="No", command=cancel).pack(side=tk.LEFT, padx=5)

    def confirm_clear_links(self):
        """Show confirmation dialog before clearing links history."""
        confirm_dialog = tk.Toplevel(self.master)
        confirm_dialog.title("Confirm Clear")
        confirm_dialog.attributes('-topmost', True)
        confirm_dialog.grab_set()  # Make dialog modal
        
        msg = "Are you sure you want to clear all stored hyperlinks?"
        tk.Label(confirm_dialog, text=msg, padx=20, pady=10).pack()
        
        def confirm():
            self.clear_links_history()
            confirm_dialog.destroy()
        
        def cancel():
            confirm_dialog.destroy()
        
        button_frame = ttk.Frame(confirm_dialog)
        button_frame.pack(pady=10)
        ttk.Button(button_frame, text="Yes", command=confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="No", command=cancel).pack(side=tk.LEFT, padx=5)

    def create_chatlog_context_menu(self):
        """Create right-click context menu for chatlog users."""
        menu = tk.Menu(self.chatlog_listbox, tearoff=0)
        menu.add_command(label="Delete User", command=self.delete_selected_user)
        
        def show_menu(event):
            if self.chatlog_listbox.curselection():
                menu.tk_popup(event.x_root, event.y_root)
        
        self.chatlog_listbox.bind("<Button-3>", show_menu)

    def load_chatlog_list(self):
        """Load chatlog from a local file and populate the listbox."""
        chatlog = self.load_chatlog()
        self.chatlog_listbox.delete(0, tk.END)
        for username in chatlog.keys():
            self.chatlog_listbox.insert(tk.END, username)

    def display_chatlog_messages(self, event=None):
        """Display messages with clickable hyperlinks in the chatlog panel."""
        chatlog = self.load_chatlog()
        self.chatlog_display.configure(state=tk.NORMAL)
        self.chatlog_display.delete(1.0, tk.END)
        
        try:
            if event is None or not self.chatlog_listbox.curselection():
                # Show all messages combined chronologically
                all_messages = []
                for username, messages in chatlog.items():
                    all_messages.extend((username, msg) for msg in messages)
                
                # Sort by timestamp
                all_messages.sort(key=lambda x: re.match(r'\[(.*?)\]', x[1]).group(1) if re.match(r'\[(.*?)\]', x[1]) else "0")
                
                for username, message in all_messages:
                    self.chatlog_display.insert(tk.END, "> ")
                    self.insert_message_with_hyperlinks(message, self.chatlog_display)
                    self.chatlog_display.insert(tk.END, "\n\n")
            else:
                # Show messages for selected user
                selected_index = self.chatlog_listbox.curselection()
                username = self.chatlog_listbox.get(selected_index)
                messages = chatlog.get(username, [])
                messages.sort(key=lambda x: re.match(r'\[(.*?)\]', x).group(1) if re.match(r'\[(.*?)\]', x) else "0")
                
                for message in messages:
                    self.chatlog_display.insert(tk.END, "> ")
                    self.insert_message_with_hyperlinks(message, self.chatlog_display)
                    self.chatlog_display.insert(tk.END, "\n\n")
        
        except Exception as e:
            print(f"Error displaying chatlog messages: {e}")
        finally:
            self.chatlog_display.configure(state=tk.DISABLED)
            self.chatlog_display.see(tk.END)

    def insert_message_with_hyperlinks(self, text, text_widget):
        """Insert text with hyperlinks into any text widget."""
        url_pattern = re.compile(r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)')
        last_end = 0
        
        for match in url_pattern.finditer(text):
            start, end = match.span()
            # Insert non-URL text
            if start > last_end:
                text_widget.insert(tk.END, text[last_end:start])
                
            # Clean and insert URL
            url = text[start:end].rstrip('.,;:)]}\'"')
            if url.startswith('www.'):
                url = 'http://' + url
            text_widget.insert(tk.END, url, "hyperlink")
            
            last_end = end
        
        # Insert remaining text
        if last_end < len(text):
            text_widget.insert(tk.END, text[last_end:])

    def update_members_display(self):
        """Update the chat members display with bubble icons and adjust panel width."""
        # Clear existing widgets
        for widget in self.members_frame.winfo_children():
            widget.destroy()

        # Create a temporary label to measure text width
        font = ("Arial VGA 437", 9, "bold")
        test_label = ttk.Label(self.members_frame, font=font)
        
        # Calculate max width using character-based estimation
        max_width = 0
        for member in sorted(self.chat_members):
            # Estimate width: each character is roughly 7 pixels wide in this font
            # Add extra padding (40 pixels) for button margins and safety
            text_width = (len(member) * 7) + 40
            max_width = max(max_width, text_width)
        
        test_label.destroy()
        
        # Set minimum width and add padding for scrollbar
        panel_width = max(max_width, 100) + 30  # Minimum 100px + scrollbar width
        members_frame = self.members_frame.master.master  # Get the outer frame
        members_frame.configure(width=panel_width)

        # Create member buttons
        style = ttk.Style()
        for i, member in enumerate(sorted(self.chat_members)):
            bg_color = self.random_color()
            style_name = f"Member{i}.TButton"
            style.configure(style_name,
                padding=(10, 5),
                relief="raised",
                background=bg_color,
                borderwidth=2,
                font=font)

            button = ttk.Button(self.members_frame, 
                              text=member,
                              style=style_name,
                              cursor="hand2")
            button.pack(pady=2, padx=5, fill=tk.X, expand=False, ipadx=10)
            
            button.bind('<Button-1>', lambda e, m=member: self.select_member(m))
            button.bind('<Enter>', lambda e, b=button, s=style_name: self.on_button_hover(b, True, s))
            button.bind('<Leave>', lambda e, b=button, s=style_name: self.on_button_hover(b, False, s))

        self.members_frame.update_idletasks()

    def update_chat_members(self, lines_with_users):
        """Update the chat members based on the provided lines."""
        # Combine lines and clean ANSI codes
        combined = " ".join(lines_with_users)
        combined_clean = re.sub(r'\x1b\[[0-9;]*m', '', combined)
        print(f"[DEBUG] Raw banner: {combined_clean}")
        
        # Modified pattern to better handle PBX format and topic
        if "Topic:" in combined_clean:
            # Extract everything after "General Chat"
            parts = combined_clean.split("General Chat", 1)
            if len(parts) > 1:
                after_chat = parts[1]
                # Find first comma to separate potential username from the rest
                first_comma_pos = after_chat.find(',')
                if first_comma_pos != -1:
                    # Extract first potential username
                    first_user = after_chat[:first_comma_pos].strip()
                    # Get rest of users
                    remaining_users = after_chat[first_comma_pos + 1:]
                else:
                    first_user = ""
                    remaining_users = after_chat

                # Clean up user strings
                users_text = (first_user + "," + remaining_users if first_user else remaining_users)
                users_text = re.sub(r'are here with you\.?$', '', users_text)
                users_text = re.sub(r'with you\.?$', '', users_text)
                users_text = users_text.replace(' and ', ', ')
                
                # Split into individual users
                users = [u.strip() for u in users_text.split(',') if u.strip()]
                
                final_usernames = set()
                for user in users:
                    # Extract username from email-style addresses
                    username = user.split('@')[0].strip()
                    # Clean username but preserve dots
                    username = re.sub(r'[^A-Za-z0-9._-]', '', username)
                    
                    # Validate username
                    if (len(username) >= 2 and 
                        not re.search(r'\.(net|com|org|bbs)$', username.lower()) and
                        not username.startswith('Topic:')):
                        print(f"[DEBUG] Adding valid username: {username}")
                        final_usernames.add(username)
                    else:
                        print(f"[DEBUG] Skipping invalid username: {username}")
                
                # Ensure 'Chatbot' is always included
                final_usernames.add('Chatbot')
                
                if final_usernames:
                    print(f"[DEBUG] Final usernames: {final_usernames}")
                    self.chat_members = final_usernames
                    self.save_chat_members_file()
                    self.update_members_display()
                    
                    # Only request actions if not already requested this session
                    if not getattr(self, 'actions_requested_this_session', False):
                        print("[DEBUG] First banner this session, requesting actions")
                        self.actions_requested_this_session = True
                        self.master.after(1000, self.send_actions_request)

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
            print(f"Error saving last seen file: {e}")

    def refresh_chat_members(self):
        """Periodically refresh the chat members list."""
        self.update_members_display()
        self.master.after(5000, self.refresh_chat_members)

    def append_directed_message(self, text):
        """Append text to the directed messages display with hyperlink support."""
        if not text.endswith('\n'):
            text += '\n'
            
        self.directed_msg_display.configure(state=tk.NORMAL)
        
        # Get current content
        current_content = self.directed_msg_display.get('1.0', tk.END)
        
        # Only append if the message isn't already present
        if text not in current_content:
            # Use insert_with_hyperlinks for directed messages
            self.insert_directed_message_with_hyperlinks(text, "normal")
            self.directed_msg_display.see(tk.END)
            
        self.directed_msg_display.configure(state=tk.DISABLED)

    def play_ding_sound(self):
        """Play a standard ding sound effect."""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

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
            print("Error saving last seen file: {e}")

    def refresh_chat_members(self):
        """Periodically refresh the chat members list."""
        self.update_members_display()
        self.master.after(5000, self.refresh_chat_members)

    def append_directed_message(self, text):
        """Append text to the directed messages display."""
        # Check if message already exists in the display
        if not text.endswith('\n'):
            text += '\n'
            
        self.directed_msg_display.configure(state=tk.NORMAL)
        
        # Get current content
        current_content = self.directed_msg_display.get('1.0', tk.END)
        
        # Only append if the message isn't already present
        if text not in current_content:
            self.insert_directed_message_with_hyperlinks(text, "normal")
            self.directed_msg_display.see(tk.END)
            
        self.directed_msg_display.configure(state=tk.DISABLED)

    def play_ding_sound(self):
        """Play a standard ding sound effect."""
        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)

    async def _send_message(self, message):
        """Async helper method to send messages."""
        if self.connected and self.writer:
            self.writer.write(message)
            await self.writer.drain()

    def update_actions_listbox(self):
        """Update the Actions panel with parsed actions and adjust panel width."""
        if not self.actions:
            print("[DEBUG] No actions to display")
            return
            
        # Calculate max width using character-based estimation
        font = ("Arial VGA 437", 9, "bold")
        max_width = max((len(action) * 7) + 40 for action in sorted(set(self.actions)))
        panel_width = max(max_width, 100) + 30  # Minimum 100px + scrollbar width
        
        # Set panel width
        actions_frame = self.actions_frame.master.master
        actions_frame.configure(width=panel_width)

        # Cleanup old mousewheel binding if it exists
        if hasattr(self, 'actions_canvas'):
            self.actions_canvas.unbind_all("<MouseWheel>")

        # Create new scrollable frame
        if not hasattr(self, 'actions_scrollable_frame'):
            self.actions_canvas = tk.Canvas(self.actions_frame, highlightthickness=0)
            self.actions_scrollbar = ttk.Scrollbar(self.actions_frame, orient=tk.VERTICAL, 
                                                command=self.actions_canvas.yview)
            self.actions_scrollable_frame = ttk.Frame(self.actions_canvas)
            
            # Configure scrolling
            self.actions_scrollable_frame.bind("<Configure>",
                lambda e: self.actions_canvas.configure(scrollregion=self.actions_canvas.bbox("all")))
            self.actions_canvas.create_window((0, 0), window=self.actions_scrollable_frame, anchor="nw")
            self.actions_canvas.configure(yscrollcommand=self.actions_scrollbar.set)

            # Configure mousewheel with proper cleanup
            def on_mousewheel(event):
                self.actions_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
            def on_destroy(event):
                self.actions_canvas.unbind_all("<MouseWheel>")
            
            self.actions_canvas.bind_all("<MouseWheel>", on_mousewheel)
            self.actions_scrollable_frame.bind("<Destroy>", on_destroy)

        # Clear and recreate action buttons
        for widget in self.actions_scrollable_frame.winfo_children():
            widget.destroy()

        for i, action in enumerate(sorted(set(self.actions))):
            self.create_action_button(i, action)

        # Update canvas layout
        if not self.actions_canvas.winfo_ismapped():
            self.actions_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.actions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Set visible height
        visible_height = min(20 * 30, len(self.actions) * 30)  # 30px per button
        self.actions_canvas.configure(height=visible_height)

    def create_action_button(self, index, action):
        """Helper method to create an action button."""
        try:
            # Create the button in the scrollable frame instead of actions_frame
            style = ttk.Style()
            style_name = f"Action{index}.TButton"
            bg_color = self.random_color()
            
            style.configure(
                style_name,
                padding=(10, 5),
                relief="raised",
                background=bg_color,
                borderwidth=2,
                font=("Arial VGA 437", 9, "bold")
            )

            button = ttk.Button(
                self.actions_scrollable_frame,
                text=action,
                style=style_name,
                cursor="hand2")  # Removed fixed width property
            # Add padding around text instead
            button.pack(pady=2, padx=5, fill=tk.X, expand=False, ipadx=10)  # Added ipadx for minimal padding
            
            # Bind events
            button.bind('<Button-1>', lambda e, a=action: self.on_action_select(a))
            button.bind('<Enter>', lambda e, b=button, s=style_name: self.on_button_hover(b, True, s))
            button.bind('<Leave>', lambda e, b=button, s=style_name: self.on_button_hover(b, False, s))
            
        except Exception as e:
            print(f"[DEBUG] Error creating action button: {e}")

    def on_action_select(self, action):
        """Handle action selection with or without a target username."""
        if self.connected and self.writer:
            # Format action command based on whether a member is selected
            if hasattr(self, 'selected_member') and self.selected_member:
                action_command = f"{action} {self.selected_member}"
            else:
                action_command = action
                
            # Send the action
            asyncio.run_coroutine_threadsafe(
                self._send_message(action_command + "\r\n"), 
                self.loop
            )
            
            # Deselect member if one was selected
            self.deselect_all_members()

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
        """Display stored hyperlinks in the links panel with top scroll positioning."""
        if not hasattr(self, 'links_display'):
            return

        self.links_display.configure(state=tk.NORMAL)
        self.links_display.delete(1.0, tk.END)
        
        links = self.load_links_history()
        # Display links in reverse chronological order
        links.reverse()
        
        for link in links:
            timestamp = link.get("timestamp", "")
            sender = link.get("sender", "Unknown")
            url = link.get("url", "")
            
            self.links_display.insert(tk.END, f"{timestamp} from {sender}:\n")
            self.links_display.insert(tk.END, f"{url}\n\n", "hyperlink")
        
        self.links_display.configure(state=tk.DISABLED)
        # Ensure we start at the top
        self.links_display.see("1.0")

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
        # More comprehensive URL pattern
        url_pattern = re.compile(r'(https?://[^\s<>"\']+|www\.[^\s<>"\']+)')
        
        # Extract all URLs from the message
        urls = url_pattern.findall(message)
        
        # Add debug output to see raw message
        print(f"[DEBUG] Raw message: {message}")
        print(f"[DEBUG] Found URLs: {urls}")
        
        # Clean URLs (remove trailing punctuation)
        cleaned_urls = []
        for url in urls:
            # Remove trailing punctuation that might have been caught
            url = re.sub(r'[.,;:]+$', '', url)
            # Add http:// to www. urls
            if url.startswith('www.'):
                url = 'http://' + url
            cleaned_urls.append(url)
        
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        
        for url in cleaned_urls:
            print(f"[DEBUG] Storing URL: {url} from {sender}")  # Debug line
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

    def delete_selected_user(self):
        """Delete the selected user from the chatlog and users list."""
        selected = self.chatlog_listbox.curselection()
        if not selected:
            return
            
        username = self.chatlog_listbox.get(selected)
        if tk.messagebox.askyesno("Confirm Delete", 
                                 f"Are you sure you want to delete {username} and their chat logs?",
                                 icon='warning'):
            # Remove from chatlog
            chatlog = self.load_chatlog()
            if username in chatlog:
                del chatlog[username]
                self.save_chatlog(chatlog)
            
            # Remove from listbox
            self.chatlog_listbox.delete(selected)
            
            # Show all messages after deletion
            self.display_chatlog_messages(None)

    def on_scroll_change(self, *args):
        """Custom scrollbar handler to ensure bottom line visibility."""
        self.terminal_display.yview_moveto(args[0])
        if float(args[1]) == 1.0:  # If scrolled to bottom
            self.master.update_idletasks()
            self.terminal_display.see(tk.END)

    def toggle_majorlink_mode(self):
        """Handle toggling MajorLink mode on/off."""
        self.terminal_display.configure(state=tk.NORMAL)
        self.terminal_display.delete(1.0, tk.END)
        self.terminal_display.configure(state=tk.DISABLED)
        
        mode = "enabled" if self.majorlink_mode.get() else "disabled"
        self.append_terminal_text(f"\n--- MajorLink Mode {mode} ---\n\n", "normal")

    def limit_input_length(self, *args):
        """Limit input field to 255 characters"""
        value = self.input_var.get()
        if len(value) > 255:
            self.input_var.set(value[:255])

    def load_frame_sizes(self):
        """Load saved frame sizes from file"""
        try:
            if os.path.exists("frame_sizes.json"):
                with open("frame_sizes.json", "r") as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading frame sizes: {e}")
        return {}

    def save_frame_sizes(self):
        """Save current frame sizes to file"""
        try:
            # Get sash position based on paned window type
            if isinstance(self.paned, ttk.PanedWindow):
                sash_pos = self.paned.paneconfig(self.output_frame, 'weight')[4]
            else:
                try:
                    sash_pos = self.paned.sash_coord(0)[0]
                except:
                    sash_pos = 200  # Default value if we can't get position

            sizes = {
                'paned_pos': sash_pos,
                'window_geometry': self.master.geometry()
            }
            with open("frame_sizes.json", "w") as f:
                json.dump(sizes, f)
        except Exception as e:
            print(f"Error saving frame sizes: {e}")

    def load_saved_settings(self):
        """Load all saved UI settings."""
        try:
            if os.path.exists("settings.json"):
                with open("settings.json", "r") as f:
                    settings = json.load(f)
                    # Apply loaded settings - removed auto_login
                    self.font_name.set(settings.get('font_name', "Courier New"))
                    self.font_size.set(settings.get('font_size', 10))
                    self.logon_automation_enabled.set(settings.get('logon_automation', False))
                    self.keep_alive_enabled.set(settings.get('keep_alive', False))
                    self.show_messages_to_you.set(settings.get('show_messages', True))
                    self.majorlink_mode.set(settings.get('majorlink_mode', True))
                    return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {}

    def apply_saved_settings(self):
        """Apply saved settings after UI is built."""
        settings = self.load_saved_settings()
        
        # Apply paned window position if saved
        if self.paned and 'paned_pos' in settings and settings['paned_pos']:
            try:
                # Use different methods based on paned window type
                if isinstance(self.paned, ttk.PanedWindow):
                    self.paned.paneconfig(self.output_frame, weight=settings['paned_pos'])
                else:
                    # For tk.PanedWindow
                    def set_sash():
                        try:
                            self.paned.sash_place(0, settings['paned_pos'], 0)
                        except Exception as e:
                            print(f"Error setting sash position: {e}")
                    self.master.after(100, set_sash)
            except Exception as e:
                print(f"Error applying paned window settings: {e}")

        # Apply window geometry if saved
        if 'window_geometry' in settings:
            try:
                self.master.geometry(settings['window_geometry'])
            except Exception as e:
                print(f"Error setting window geometry: {e}")

        # Apply Messages to You visibility
        if not settings.get('show_messages', True):
            self.toggle_messages_frame()

        # Update display font
        self.update_display_font()

    def on_closing(self):
        """Extended closing handler to save frame sizes and cleanup."""
        self.save_frame_sizes()
        self.close_spelling_popup()  # Add cleanup of spell popup

    async def request_actions_list(self):
        """Request the actions list with proper sequencing."""
        if not self.connected or not self.writer:
            return
            
        async with self.actions_request_lock:
            if self.actions_list_requested:
                return
                
            print("[DEBUG] Requesting actions list sequence")
            self.actions_list_requested = True
            
            try:
                # Send action list request with proper writer access
                print("[DEBUG] Sending /a list command")
                self.writer.write("/a list\r\n")
                await self.writer.drain()  # Use writer's drain method
                
                # Wait briefly
                await asyncio.sleep(0.5)
                
                # Send enter keystroke
                print("[DEBUG] Sending enter keystroke")
                self.writer.write("\r\n")
                await self.writer.drain()  # Use writer's drain method
                
                print("[DEBUG] Actions list request sequence completed")
                
            except Exception as e:
                print(f"[DEBUG] Error in request_actions_list: {e}")
            finally:
                self.actions_list_requested = False

    def send_actions_request(self):
        """Non-async wrapper for requesting actions list."""
        if self.connected and self.writer and self.loop:
            async def send():
                try:
                    await self.request_actions_list()
                except Exception as e:
                    print(f"[DEBUG] Error in send_actions_request: {e}")
            
            future = asyncio.run_coroutine_threadsafe(send(), self.loop)
            try:
                # Wait for completion with timeout
                future.result(timeout=5)
            except Exception as e:
                print(f"Error or timeout during cleanup: {e}")
        try:
            # Your code here
            pass
        finally:
            # Force quit even if cleanup fails
            try:
                root.quit()
            finally:
                root.destroy()

    def request_actions_list(self):
        """Enhanced action list request with PBX mode support."""
        if not self.connected or not self.writer:
            return
            
        print("[DEBUG] Requesting actions list")
        
        async def send_commands():
            try:
                # Send action list request
                self.writer.write("/a list\r\n")
                await self.drain()
                
                # Wait briefly then send Enter
                await asyncio.sleep(0.5)
                self.writer.write("\r\n")
                await self.drain()
                
                print("[DEBUG] Sent action list request")
            except Exception as e:
                print(f"[DEBUG] Error requesting actions list: {e}")
                
        asyncio.run_coroutine_threadsafe(send_commands(), self.loop)

    def setup_autocorrect(self):
        """Initialize autocorrect functionality."""
        self.input_box.bind('<KeyRelease>', self.check_spelling)

    def check_spelling(self, event=None):
        """Check spelling and suggest corrections for the input text."""
        if not self.autocorrect_enabled.get() or not self.spell:
            return
        
        text = self.input_var.get()
        if not text or text.isspace():
            return

        words = text.split()
        if not words:
            return

        last_word = words[-1]
        
        # Skip short words, commands, and URLs
        if (len(last_word) < 4 or 
            last_word.startswith('/') or 
            '.' in last_word or 
            '@' in last_word):
            return

        try:
            if not self.spell.check(last_word):
                suggestions = self.spell.suggest(last_word)
                if suggestions:
                    # Store top suggestion
                    self.current_suggestion = suggestions[0]
                    self.current_misspelled = last_word
                    self.show_spelling_popup(last_word, suggestions)
                else:
                    self.current_suggestion = None
                    self.current_misspelled = None
            else:
                self.current_suggestion = None
                self.current_misspelled = None
                self.close_spelling_popup()
        except Exception as e:
            print(f"Spell check error: {e}")

    def show_spelling_popup(self, word, suggestions):
        """Display spelling suggestions popup."""
        if self.spell_popup:
            self.spell_popup.destroy()
        
        self.spell_popup = tk.Toplevel(self.master)
        self.spell_popup.title("Spelling Suggestions")
        self.spell_popup.attributes('-topmost', True)
        
        # Position popup to the right of input box
        x = self.input_box.winfo_rootx() + self.input_box.winfo_width() + 10
        y = self.input_box.winfo_rooty()
        self.spell_popup.geometry(f"+{x}+{y}")
        
        # First suggestion is highlighted as the default
        for i, suggestion in enumerate(suggestions[:5]):
            btn = ttk.Button(
                self.spell_popup,
                text=suggestion,
                command=lambda s=suggestion: self.apply_suggestion(word, s),
                style="Spell.TButton"
            )
            btn.pack(padx=5, pady=2, fill=tk.X)
            try:
                # Stop any currently playing sound
                if self.current_sound:
                    winsound.PlaySound(None, winsound.SND_PURGE)
                
                # Play new sound
                self.current_sound = "directed"
                winsound.PlaySound(self.directed_sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Error playing directed sound: {e}")
                self.current_sound = None
        else:
            print(f"Directed sound file not found: {self.directed_sound_file}")

    def update_display_font(self):
        """Update font settings for terminal displays only."""
        try:
            # Create base font settings without colors for BBS terminal
            terminal_font = (self.font_name.get(), self.font_size.get())
            self.terminal_display.configure(font=terminal_font)
            
            # Full font settings for other displays
            other_displays_settings = {
                'font': terminal_font,
                'fg': self.current_font_settings.get('fg', 'white'),
                'bg': self.current_font_settings.get('bg', 'black')
            }
            
            # Apply only to terminal displays
            if hasattr(self, 'directed_msg_display'):
                self.directed_msg_display.configure(**other_displays_settings)
            if hasattr(self, 'chatlog_display'):
                self.chatlog_display.configure(**other_displays_settings)
                
        except Exception as e:
            print(f"Error updating display font: {e}")

    def handle_escape(self, event=None):
        """Handle escape key press for autocorrect."""
        self.escape_count += 1
        
        # Reset escape counter after 1 second
        if self.escape_timer:
            self.master.after_cancel(self.escape_timer)
        self.escape_timer = self.master.after(1000, self.reset_escape_count)
        
        # If pressed twice, revert to original text
        if self.escape_count >= 2:
            if self.current_misspelled and self.current_suggestion:
                # Revert any autocorrect changes
                self.current_suggestion = None
                self.current_misspelled = None
                self.close_spelling_popup()
                self.escape_count = 0
                
                # Visual feedback
                self.input_box.configure(foreground='red')
                self.master.after(500, lambda: self.input_box.configure(foreground=''))

    def reset_escape_count(self):
        """Reset the escape key counter."""
        self.escape_count = 0
        self.escape_timer = None


    def toggle_messages_frame(self):
        """Toggle visibility of the Messages to You frame."""
        if self.show_messages_to_you.get():
            self.paned.add(self.messages_frame, minsize=100)
            self.paned.update()
        else:
            self.paned.remove(self.messages_frame)
            self.paned.update()

    def select_member(self, member):
        """Select a member from the chat list."""
        print(f"Selected member: {member}")
        self.selected_member = member
        # Highlight the selected member's button
        for child in self.members_frame.winfo_children():
            if isinstance(child, ttk.Button):
                if child['text'] == member:
                    child.configure(style="BubbleSelected.TButton")
                else:
                    child.configure(style="Bubble.TButton")

    def on_button_hover(self, button, is_hovering, style_name):
        """Handle hover effects for bubble buttons."""
        style = ttk.Style()
        if is_hovering:
            if not hasattr(button, '_original_bg'):
                button._original_bg = style.lookup(style_name, 'background')
            # Darken the button slightly on hover
            style.configure(style_name, background=self.darken_color(button._original_bg))
        else:
            if hasattr(button, '_original_bg'):
                style.configure(style_name, background=button._original_bg)

    def darken_color(self, color):
        """Darken a hex color by 20%."""
        # Remove the # and convert to RGB
        rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
        # Darken each component by 20%
        darkened = tuple(int(c * 0.8) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

    def random_color(self):
        """Generate a random color with sufficient contrast."""
        # Generate pastel colors for better readability
        r = random.randint(100, 255)
        g = random.randint(100, 255)
        b = random.randint(100, 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    # Add these new helper methods
    def deselect_all_members(self):
        """Deselect all members in the list."""
        for child in self.members_frame.winfo_children():
            if isinstance(child, ttk.Button):
                child.configure(style="Bubble.TButton")
        self.selected_member = None

    def get_selected_member(self):
        """Return the currently selected member."""
        return getattr(self, 'selected_member', None)

    def toggle_pbx_mode(self):
        """Handle toggling PBX mode on/off."""
        self.terminal_display.configure(state=tk.NORMAL)
        self.terminal_display.delete(1.0, tk.END)
        self.terminal_display.configure(state=tk.DISABLED)
        
        mode = "enabled" if self.pbx_mode.get() else "disabled"
        self.append_terminal_text(f"\n--- PBX Mode {mode} ---\n\n", "normal")

    def process_pbx_line(self, clean_line, original_line):
        """Process PBX mode messages with hyperlink support."""
        try:
            # Skip system messages
            if any(re.match(pattern, clean_line) for pattern in [
                r'Topic:.*$', 
                r'.*(?:are here with you|with you)\.$',
                r'Just type.*assistance\.$'
            ]):
                return False

            # Define message patterns for all PBX formats
            patterns = {
                # Pattern for whispers (with and without domain)
                'whisper': r'\[(\S+?)(?:@[\w.-]+)?\s+\(whispered(?:\s*(?:to\s+you)?)?\):\]\s*(.+)',
                
                # Pattern for direct messages "to you" (with and without domain)
                'to_you': r'\[(\S+?)(?:@[\w.-]+)?\s+\(to\s+you\):\]\s*(.+)',
                
                # Pattern for directed messages to specific users (with and without domain)
                'public_directed': r'\[(\S+?)(?:@[\w.-]+)?\s+\(to\s+(\S+?)(?:@[\w.-]+)?\):\]\s*(.+)',
                
                # Pattern for regular public messages (with and without domain)
                'public': r'\[(\S+?)(?:@[\w.-]+)?:\]\s*(.+)'
            }

            timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")

            for msg_type, pattern in patterns.items():
                match = re.match(pattern, clean_line)
                if not match:
                    continue

                if msg_type == 'whisper':
                    sender, message = match.groups()
                    sender_clean = sender.split('@')[0]
                    formatted = f"{timestamp} From {sender} (whispered): {message}"
                    self.save_chatlog_message(sender_clean, formatted)
                    self.append_directed_message(formatted)
                    self.play_directed_sound()
                    self.append_terminal_text(original_line + "\n", "normal")
                    # Extract URLs from message
                    self.parse_and_store_hyperlinks(message, sender_clean)
                    return True

                elif msg_type == 'to_you':
                    sender, message = match.groups()
                    sender_clean = sender.split('@')[0]
                    formatted = f"{timestamp} From {sender} (to you): {message}"
                    self.save_chatlog_message(sender_clean, formatted)
                    self.append_directed_message(formatted)
                    self.play_directed_sound()
                    self.append_terminal_text(original_line + "\n", "normal")
                    # Extract URLs from message
                    self.parse_and_store_hyperlinks(message, sender_clean)
                    return True

                elif msg_type == 'public_directed':
                    sender, recipient, message = match.groups()
                    sender_clean = sender.split('@')[0]
                    recipient_clean = recipient.split('@')[0]
                    
                    # Only process as directed if it's to current user
                    if recipient_clean.lower() == self.username.get().lower():
                        formatted = f"{timestamp} From {sender} (to you): {message}"
                        self.save_chatlog_message(sender_clean, formatted)
                        self.append_directed_message(formatted)
                        self.play_directed_sound()
                    else:
                        formatted = f"{timestamp} From {sender} (to {recipient}): {message}"
                        self.save_chatlog_message(sender_clean, formatted)
                        self.play_chat_sound()
                    
                    # Extract URLs from message
                    self.parse_and_store_hyperlinks(message, sender_clean)
                    self.append_terminal_text(original_line + "\n", "normal")
                    return True

                elif msg_type == 'public':
                    sender, message = match.groups()
                    sender_clean = sender.split('@')[0]
                    formatted = f"{timestamp} From {sender}: {message}"
                    self.save_chatlog_message(sender_clean, formatted)
                    self.play_chat_sound()
                    self.append_terminal_text(original_line + "\n", "normal")
                    # Extract URLs from message
                    self.parse_and_store_hyperlinks(message, sender_clean)
                    return True

            return False

        except Exception as e:
            print(f"[DEBUG] Error in process_pbx_line: {e}")
            traceback.print_exc()
            return False

    

    def on_closing(self):
        """Extended closing handler to save frame sizes and cleanup."""
        self.save_frame_sizes()
        self.close_spelling_popup()  # Add cleanup of spell popup
        self.master.quit()  # Ensure the main loop is stopped

    async def cleanup(app):
        """Async cleanup function to handle disconnection."""
        try:
            # Cancel all pending tasks first
            for task in asyncio.all_tasks(app.loop):
                task.cancel()

            # Clear only the active members list
            app.clear_chat_members()

            # Then handle the disconnect
            if app.connected:
                await app.disconnect_from_bbs()

            # Finally close the loop 
            app.loop.stop()
            app.loop.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def previous_command(self, event=None):
        """Navigate to previous command in history."""
        if not self.command_history:
            return "break"
            
        # Save current input if starting to browse history
        if self.command_index == -1:
            self.current_command = self.input_var.get()
            
        # Move up in history
        if self.command_index < len(self.command_history) - 1:
            self.command_index += 1
            self.input_var.set(self.command_history[-(self.command_index + 1)])
            
        # Position cursor at end
        self.input_box.icursor(tk.END)
        return "break"

    def next_command(self, event=None):
        """Navigate to next command in history."""
        if self.command_index == -1:
            return "break"
            
        # Move down in history
        self.command_index -= 1
        if self.command_index == -1:
            # Restore current input when reaching bottom
            self.input_var.set(self.current_command)
        else:
            self.input_var.set(self.command_history[-(self.command_index + 1)])
            
        # Position cursor at end
        self.input_box.icursor(tk.END)
        return "break"

    def save_current_input(self, event=None):
        """Save current input when focus is lost."""
        if self.command_index == -1:
            self.current_command = self.input_var.get()

    def restore_current_input(self, event=None):
        """Restore current input when focus returns."""
        if self.command_index == -1:
            self.input_var.set(self.current_command)

    def play_chat_sound(self):
        """Play chat sound with immediate interruption of any playing sound."""
        try:
            if hasattr(self, 'chat_sound_file') and os.path.exists(self.chat_sound_file):
                print(f"[DEBUG] Playing chat sound: {self.chat_sound_file}")
                winsound.PlaySound(None, winsound.SND_PURGE)  # Stop any playing sound
                winsound.PlaySound(self.chat_sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                print(f"[DEBUG] Chat sound file not found: {getattr(self, 'chat_sound_file', 'Not set')}")
        except Exception as e:
            print(f"Error playing chat sound: {e}")

    def play_directed_sound(self):
        """Play directed sound with immediate interruption of any playing sound."""
        try:
            if hasattr(self, 'directed_sound_file') and os.path.exists(self.directed_sound_file):
                print(f"[DEBUG] Playing directed sound: {self.directed_sound_file}")
                winsound.PlaySound(None, winsound.SND_PURGE)  # Stop any playing sound
                winsound.PlaySound(self.directed_sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                print(f"[DEBUG] Directed sound file not found: {getattr(self, 'directed_sound_file', 'Not set')}")
        except Exception as e:
            print(f"Error playing directed sound: {e}")

    def load_command_history(self):
        """Load command history from file."""
        try:
            if os.path.exists("command_history.json"):
                with open("command_history.json", "r") as file:
                    return json.load(file)
        except Exception as e:
            print(f"Error loading command history: {e}")
        return []

    def save_command_history(self):
        """Save command history to file."""
        try:
            with open("command_history.json", "w") as file:
                json.dump(self.command_history[-100:], file)  # Keep only last 100 commands
        except Exception as e:
            print(f"Error saving command history: {e}")

def main():
    # Initialize configuration files
    init_config_files()
    verify_sound_files()
    
    root = tk.Tk()
    app = BBSTerminalApp(root)

    def on_closing():
        """Handle window closing event."""
        try:
            app.on_closing()  # Call the app's closing handler first
            # Create a new event loop for cleanup
            cleanup_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cleanup_loop)

            # Run cleanup synchronously with a timeout
            cleanup_loop.run_until_complete(asyncio.wait_for(cleanup(app), timeout=5.0))
            cleanup_loop.close()
        except (asyncio.TimeoutError, Exception) as e:
            print(f"Error or timeout during cleanup: {e}")
        finally:
            # Force quit even if cleanup fails
            try:
                root.quit()
            finally:
                root.destroy()

    # Bind the closing handler
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Restore window geometry if saved
    if 'window_geometry' in app.frame_sizes:
        root.geometry(app.frame_sizes['window_geometry'])

    # Start the main loop
    root.mainloop()

if __name__ == "__main__":
    main()
