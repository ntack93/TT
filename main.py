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

try:
    import enchant
except ImportError:
    enchant = None


###############################################################################
#                         BBS Telnet App (No Chatbot)
###############################################################################

def create_cp437_to_unicode_map():
    """Create a mapping of CP437 codes to their Unicode equivalents"""
    # Standard ASCII (0-127) maps directly
    cp437_map = {i: chr(i) for i in range(128)}
    
    # Extended ASCII (128-255) special mapping
    cp437_extended = [
        # Box drawing and block elements (128-175)
        '€', 'ü', 'é', 'â', 'ä', 'à', 'å', 'ç', 'ê', 'ë', 'è', 'ï', 'î', 'ì', 'Ä', 'Å',
        'É', 'æ', 'Æ', 'ô', 'ö', 'ò', 'û', 'ù', 'ÿ', 'Ö', 'Ü', '¢', '£', '¥', '₧', 'ƒ',
        'á', 'í', 'ó', 'ú', 'ñ', 'Ñ', 'ª', 'º', '¿', '⌐', '¬', '½', '¼', '¡', '«', '»',
        '░', '▒', '▓', '│', '┤', '╡', '╢', '╖', '╕', '╣', '║', '╗', '╝', '╜', '╛', '┐',
        '└', '┴', '┬', '├', '─', '┼', '╞', '╟', '╚', '╔', '╩', '╦', '╠', '═', '╬', '╧',
        '╨', '╤', '╥', '╙', '╘', '╒', '╓', '╫', '╪', '┘', '┌', '█', '▄', '▌', '▐', '▀',
        # Special characters and symbols (0-31)
        '␀', '☺', '☻', '♥', '♦', '♣', '♠', '•', '◘', '○', '◙', '♂', '♀', '♪', '♫', '☼',
        '►', '◄', '↕', '‼', '¶', '§', '▬', '↨', '↑', '↓', '→', '←', '∟', '↔', '▲', '▼',
        # Rest of extended ASCII (176-255)
        'α', 'β', 'Γ', 'π', 'Σ', 'σ', 'µ', 'τ', 'Φ', 'Θ', 'Ω', 'δ', '∞', 'φ', 'ε', '∩',
        '≡', '±', '≥', '≤', '⌠', '⌡', '÷', '≈', '°', '∙', '·', '√', 'ⁿ', '²', '■', ' '
    ]
    
    # Add extended ASCII mappings
    for i, char in enumerate(cp437_extended):
        cp437_map[i + 128] = char
        
    return cp437_map

class BBSTerminalApp:
    def __init__(self, master):
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

        # Create the main UI frame on the LEFT
        main_frame = ttk.Frame(container, name='main_frame')
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=0)
        main_frame.rowconfigure(1, weight=3)
        main_frame.rowconfigure(2, weight=0)
        container.add(main_frame, weight=1)

        # Create the Chatroom Members panel in the MIDDLE
        members_frame = ttk.LabelFrame(container, text="Chatroom Members")
        self.members_listbox = tk.Listbox(members_frame, height=20, width=20, exportselection=False)
        self.members_listbox.pack(fill=tk.BOTH, expand=True)
        self.create_members_context_menu()
        container.add(members_frame, weight=0)

        # Create the Actions listbox on the RIGHT
        actions_frame = ttk.LabelFrame(container, text="Actions")
        self.actions_listbox = tk.Listbox(actions_frame, height=20, width=20, exportselection=False)
        self.actions_listbox.pack(fill=tk.BOTH, expand=True)
        self.actions_listbox.bind("<Double-Button-1>", self.on_action_select)
        self.actions_listbox.bind("<Return>", self.on_action_select)
        self.actions_listbox.bind("<Button-1>", self.on_action_select)
        container.add(actions_frame, weight=0)

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
        
        # Add new Go Teleconference and BRB buttons
        tele_button = ttk.Button(top_frame, text="Go Teleconference", 
                                command=lambda: self.send_custom_message("/go tele"), 
                                style="Teleconference.TButton")
        tele_button.grid(row=0, column=5, padx=5, pady=5)
        
        brb_button = ttk.Button(top_frame, text="BRB", 
                               command=lambda: self.send_custom_message("ga will be right back!"), 
                                style="BRB.TButton")
        brb_button.grid(row=0, column=6, padx=5, pady=5)
        
        # Add the Chatlog button (moved to column 7)
        chatlog_button = ttk.Button(top_frame, text="Chatlog", command=self.show_chatlog_window, style="Chatlog.TButton")
        chatlog_button.grid(row=0, column=7, padx=5, pady=5)

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
        
        # Add the Keep Alive checkbox
        keep_alive_check = ttk.Checkbutton(self.conn_frame, text="Keep Alive", variable=self.keep_alive_enabled, command=self.toggle_keep_alive)
        keep_alive_check.grid(row=0, column=8, padx=5, pady=5)

        # Add new row for automation controls
        logon_auto_check = ttk.Checkbutton(checkbox_frame, text="Logon Automation", 
                                          variable=self.logon_automation_enabled)
        logon_auto_check.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        # Add Messages to You checkbox next to it
        messages_check = ttk.Checkbutton(checkbox_frame, text="Messages to You",
                                       variable=self.show_messages_to_you,
                                       command=self.toggle_messages_frame)
        messages_check.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

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
        self.output_frame = ttk.LabelFrame(self.paned, text="BBS Output")
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
            font=("Arial", 9),
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

        # At the end of build_ui, apply saved settings
        self.master.after(100, self.apply_saved_settings)

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

        # Add new button styles
        configure_button_style("Teleconference", "#20c997")  # Teal
        configure_button_style("BRB", "#6610f2")  # Purple

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
        """Save the selected font settings and apply them to all text displays except BBS Output."""
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
            
            # Apply to all text displays except BBS Output
            self.chatlog_display.configure(**font_settings)
            self.directed_msg_display.configure(**font_settings)
            self.members_listbox.configure(**font_settings)
            self.actions_listbox.configure(**font_settings)
            
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
        self.has_requested_actions = False

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
        
        # Send /go tele after 1 second
        self.master.after(5000, lambda: self.send_custom_message("/go tele"))
        
        # Send join majorlink after 1 second
        self.master.after(6000, lambda: self.send_custom_message("join majorlink"))

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
                                print(f"Warning: Error during wait_closed: {e}")
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
        """Accumulate data, split on newlines, and process each complete line."""
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
            # Remove ANSI codes for filtering purposes only.
            clean_line = ansi_regex.sub('', line).strip()
            
            # Process directed messages
            directed_patterns = [
                r'From\s+(\S+?)(?:@[\w.-]+)?\s*\(whispered(?:\s+to\s+you)?\):\s*(.+)',
                r'From\s+(\S+?)(?:@[\w.-]+)?\s*\(to\s+you\):\s*(.+)'
            ]
            
            for pattern in directed_patterns:
                match = re.match(pattern, clean_line)
                if match:
                    sender = match.group(1)
                    message = match.group(2)
                    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ")
                    timestamped_message = f"{timestamp}From {sender}: {message}"
                    
                    # Check if this is a duplicate message
                    if timestamped_message != self.last_message:
                        self.append_directed_message(timestamped_message)
                        self.play_directed_sound()
                        self.last_message = timestamped_message
                    break

            # Continue with existing processing
            if ("You are in" in clean_line and 
                "are here with you" in clean_line):
                current_time = time.time()
                # Only request actions if it's been more than 5 seconds since last banner
                if (current_time - self.last_banner_time > 5 and 
                    len(self.actions) == 0):
                    print("[DEBUG] Detected chatroom banner, requesting actions list")
                    self.last_banner_time = current_time
                    self.request_actions_list()

            # Add Actions list detection before MajorLink mode check
            if "Action listing for:" in clean_line:
                self.actions = []  # Clear existing actions
                self.collecting_actions = True
                self.actions_requested = False  # Reset flag after receiving list
                # Send Enter keystroke immediately when we see the action listing
                self.master.after(50, lambda: self.send_message(None))
                continue
            elif clean_line == ":" and self.collecting_actions:
                self.collecting_actions = False
                self.update_actions_listbox()  # Update the display
                continue
            elif self.collecting_actions:
                # Split line into words and add valid actions
                potential_actions = clean_line.split()
                self.actions.extend(
                    action for action in potential_actions 
                    if action and len(action) >= 2  # Ensure valid action
                )
                continue

            if self.majorlink_mode.get():
                # --- Filter header lines ---
                if self.collecting_users:
                    self.user_list_buffer.append(line)
                    if "are here with you." in clean_line:
                        self.update_chat_members(self.user_list_buffer)
                        self.collecting_users = False
                        self.user_list_buffer = []
                        skip_display = False  # End of banner section
                        continue
                    skip_display = True  # Skip displaying banner content
                    continue
                
                if clean_line.startswith("You are in"):
                    self.user_list_buffer = [line]
                    self.collecting_users = True
                    skip_display = True  # Start of banner section
                    continue
                
                # Skip displaying banner-related lines
                if any(pattern in clean_line for pattern in [
                    "Topic:",
                    "Just press",
                    "are here with you"
                ]):
                    continue

            # Always collect users for member list functionality
            if "You are in" in clean_line and not self.collecting_users:
                self.user_list_buffer = [line]
                self.collecting_users = True
            elif self.collecting_users:
                self.user_list_buffer.append(line)
                if "are here with you." in clean_line:
                    self.update_chat_members(self.user_list_buffer)
                    self.collecting_users = False
                    self.user_list_buffer = []

            # Only skip display if in MajorLink mode and skip_display is true
            if not (self.majorlink_mode.get() and skip_display) and clean_line:
                self.append_terminal_text(line + "\n", "normal")
                self.check_triggers(line)
                self.parse_and_save_chatlog_message(line)

            # Check for specific MajorLink entry message
            if (not self.has_requested_actions and 
                "Teleconference" in clean_line):
                # Look for the next line to confirm MajorLink entry
                next_line_idx = lines[:-1].index(line) + 1
                if (next_line_idx < len(lines) - 1 and 
                    "You are in the MajorLink channel" in ansi_regex.sub('', lines[next_line_idx]).strip()):
                    print("[DEBUG] Detected MajorLink entry, requesting actions list")
                    self.has_requested_actions = True  # Set flag to prevent future requests
                    self.master.after(500, self.request_actions_list)  # Small delay to ensure connection is ready

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
        """Parse and save chat messages with timestamps."""
        # Remove any ANSI escape sequences
        clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
        
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
        
        # Check for page notifications first
        page_match = self.page_pattern.match(clean_line)
        if page_match:
            sender = page_match.group(1)
            location = page_match.group(2)
            message = page_match.group(3)
            if not has_timestamp:
                timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ")
                message_with_timestamp = f"{timestamp}Page from {sender} in {location}: {message}"
            else:
                message_with_timestamp = clean_line
            self.append_directed_message(message_with_timestamp)
            self.play_directed_sound()
            return

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
        """Send the user's typed message to the BBS."""
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
        # Clear input before sending to prevent duplicates
        self.input_var.set("")
        
        if not user_input:
            # If empty/whitespace, just send newline
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
            
        selected_indices = self.members_listbox.curselection()
        if selected_indices:
            username = self.members_listbox.get(selected_indices[0])
            action = f"{action} {username}"
            
        message = action + "\r\n"
        async def send():
            try:
                self.writer.write(message)
                await self.writer.drain()
                # Deselect the action after sending
                self.actions_listbox.selection_clear(0, tk.END)
                self.members_listbox.selection_clear(0, tk.END)
            except Exception as e:
                print(f"Error sending action: {e}")
                
        asyncio.run_coroutine_threadsafe(send(), self.loop)

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
        """Append text to the terminal display with optional ANSI parsing."""
        self.terminal_display.configure(state=tk.NORMAL)
        self.parse_ansi_and_insert(text)
        self.terminal_display.see(tk.END)
        self.master.update_idletasks()  # Force update to ensure proper display
        self.terminal_display.configure(state=tk.DISABLED)

    def parse_ansi_and_insert(self, text_data):
        """Enhanced parser for ANSI codes including blink."""
        ansi_escape_regex = re.compile(r'\x1b\[(.*?)m')
        last_end = 0
        current_tags = ["normal"]
        blink_tag = None
    
        for match in ansi_escape_regex.finditer(text_data):
            start, end = match.span()
            if start > last_end:
                segment = text_data[last_end:start]
                self.insert_with_hyperlinks(segment, tuple(current_tags))
            
            code_string = match.group(1)
            codes = code_string.split(';')
            
            if '0' in codes:
                current_tags = ["normal"]
                blink_tag = None
                codes.remove('0')
    
            for code in codes:
                # Handle blink codes
                if code in ['5', '6']:  # Both slow and rapid blink
                    if not blink_tag:
                        blink_tag = f"blink_{len(self.blink_tags)}"
                        self.terminal_display.tag_configure(blink_tag, background="")
                        self.blink_tags.add(blink_tag)
                    if blink_tag not in current_tags:
                        current_tags.append(blink_tag)
                else:
                    mapped_tag = self.map_code_to_tag(code)
                    if mapped_tag and mapped_tag not in current_tags:
                        current_tags.append(mapped_tag)
                        
            last_end = end
    
        if last_end < len(text_data):
            segment = text_data[last_end:]
            self.insert_with_hyperlinks(segment, tuple(current_tags))

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
        """Display messages for the selected user or all messages if no user is selected."""
        chatlog = self.load_chatlog()
        self.chatlog_display.configure(state=tk.NORMAL)
        self.chatlog_display.delete(1.0, tk.END)
        
        if event is None or not self.chatlog_listbox.curselection():
            # Show all messages combined chronologically
            all_messages = []
            for username, messages in chatlog.items():
                all_messages.extend((username, msg) for msg in messages)
            
            # Sort by timestamp
            all_messages.sort(key=lambda x: re.match(r'\[(.*?)\]', x[1]).group(1) if re.match(r'\[(.*?)\]', x[1]) else "0")
            
            for username, message in all_messages:
                self.chatlog_display.insert(tk.END, f"> {message}\n\n")
        else:
            # Show messages for selected user
            selected_index = self.chatlog_listbox.curselection()
            username = self.chatlog_listbox.get(selected_index)
            messages = chatlog.get(username, [])
            messages.sort(key=lambda x: re.match(r'\[(.*?)\]', x).group(1) if re.match(r'\[(.*?)\]', x) else "0")
            for message in messages:
                self.chatlog_display.insert(tk.END, f"> {message}\n\n")
        
        self.chatlog_display.configure(state=tk.DISABLED)
        self.chatlog_display.see(tk.END)

    def update_members_display(self):
        """Update the chat members Listbox with the current chat_members set."""
        self.members_listbox.delete(0, tk.END)
        for member in sorted(self.chat_members):
            self.members_listbox.insert(tk.END, member)

    def update_chat_members(self, lines_with_users):
        """Update the chat members based on the provided lines."""
        combined = " ".join(lines_with_users)
        combined_clean = re.sub(r'\x1b\[[0-9;]*m', '', combined)
        print(f"[DEBUG] Raw banner: {combined_clean}")
        
        # Extract all usernames from the banner
        user_section = ""
        if "You are in" in combined_clean and "are here with you" in combined_clean:
            # Extract everything between "Topic:" and "are here with you"
            match = re.search(r'Topic:.*?(?=\s+are here with you\.)', combined_clean, re.DOTALL)
            if match:
                user_section = match.group(0)
                # Remove the Topic line and any parenthetical content
                user_section = re.sub(r'Topic:.*?\n', '\n', user_section, flags=re.DOTALL)
                user_section = re.sub(r'\(.*?\)', '', user_section)
        
        final_usernames = set()
        
        # Modified pattern to handle usernames with or without domains
        usernames = re.findall(
            r'([A-Za-z][A-Za-z0-9._-]+?)(?:@[\w.-]*)?(?:,|\s+and\s+|(?=\s+are here)|\s*$)', 
            user_section
        )
        
        # Process each username
        for username in usernames:
            username = username.strip()
            if (len(username) >= 2 and 
                username.lower() not in {'in', 'the', 'chat', 'general', 'channel', 'topic', 'majorlink'} and
                re.match(r'^[A-Za-z][A-Za-z0-9._-]*$', username)):
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
            print(f"Error saving last seen file: {e}")

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

    def request_actions_list(self):
        """Send command to request actions list from BBS."""
        if self.connected and self.writer:
            print("[DEBUG] Sending /a list command")
            self.send_custom_message("/a list")

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
            if i == 0:  # Highlight first suggestion
                btn.configure(style="SpellDefault.TButton")
        
        self.master.after(3000, self.close_spelling_popup)

    def apply_suggestion(self, old_word, new_word):
        """Replace misspelled word with suggestion."""
        current_text = self.input_var.get()
        new_text = current_text.rsplit(old_word, 1)[0] + new_word
        self.input_var.set(new_text)
        self.close_spelling_popup()

    def close_spelling_popup(self):
        """Close the spelling suggestion popup."""
        if self.spell_popup:
            self.spell_popup.destroy()
            self.spell_popup = None

    def play_chat_sound(self):
        """Play sound for general chat messages."""
        if os.path.exists(self.chat_sound_file):
            try:
                # Stop any currently playing sound
                if self.current_sound:
                    winsound.PlaySound(None, winsound.SND_PURGE)
                
                # Play new sound
                self.current_sound = "chat"
                winsound.PlaySound(self.chat_sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as e:
                print(f"Error playing chat sound: {e}")
                self.current_sound = None
        else:
            print(f"Chat sound file not found: {self.chat_sound_file}")

    def play_directed_sound(self):
        """Play sound for directed messages."""
        if os.path.exists(self.directed_sound_file):
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
        """Update font settings for all text widgets."""
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
            
            # Apply to secondary displays if they exist
            if hasattr(self, 'directed_msg_display'):
                self.directed_msg_display.configure(**other_displays_settings)
            if hasattr(self, 'members_listbox'):
                self.members_listbox.configure(**other_displays_settings)
            if hasattr(self, 'actions_listbox'):
                self.actions_listbox.configure(**other_displays_settings)
                
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
            # Show messages frame
            self.paned.add(self.messages_frame, minsize=100)
            self.paned.update()
        else:
            # Hide messages frame
            self.paned.remove(self.messages_frame)
            self.paned.update()

def main():
    root = tk.Tk()
    app = BBSTerminalApp(root)
    
    async def cleanup():
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

    def on_closing():
        """Handle window closing event."""
        try:
            app.on_closing()  # Call the app's closing handler first
            # Create a new event loop for cleanup
            cleanup_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cleanup_loop)
            
            # Run cleanup synchronously with a timeout
            cleanup_loop.run_until_complete(asyncio.wait_for(cleanup(), timeout=5.0))
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
