import os
import json

DEFAULT_CONFIG_FILES = {
    "chat_members.json": [],
    "chatlog.json": {},
    "favorites.json": [],
    "frame_sizes.json": {
        "paned_pos": 200,
        "window_geometry": "800x600"
    },
    "hyperlinks.json": [],
    "last_seen.json": {},
    "panel_sizes.json": {
        "users": 150,
        "links": 300
    },
    "settings.json": {
        "font_name": "Courier New",
        "font_size": 10,
        "logon_automation": False,
        "keep_alive": False,
        "show_messages": True,
        "majorlink_mode": True
    },
    "font_settings.json": {
        "font_name": "Courier New",
        "font_size": 10,
        "fg": "white",
        "bg": "black"
    },
    "triggers.json": []
}

def init_config_files():
    """Initialize all required configuration files if they don't exist."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    for filename, default_content in DEFAULT_CONFIG_FILES.items():
        filepath = os.path.join(script_dir, filename)
        if not os.path.exists(filepath):
            print(f"Creating default {filename}")
            with open(filepath, 'w') as f:
                json.dump(default_content, f, indent=4)

def verify_sound_files():
    """Ensure sound files exist with default content."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sound_files = {
        "chat.wav": b"",  # Add default WAV file content here if needed
        "directed.wav": b""  # Add default WAV file content here if needed
    }
    
    for filename, content in sound_files.items():
        filepath = os.path.join(script_dir, filename)
        if not os.path.exists(filepath):
            print(f"Creating empty sound file {filename}")
            with open(filepath, 'wb') as f:
                f.write(content)
