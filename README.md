# BBS Telnet Terminal

A retro Telnet terminal application for connecting to BBS systems, with features like chat logging, message filtering, and live URL previews.

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup Instructions](#setup-instructions)
  - [Prerequisites](#prerequisites)
  - [Installation Steps](#installation-steps)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- **Telnet Connectivity:** Connect to BBS servers using Telnet.
- **Chat Logging:** Automatically save and review chat messages.
- **Automation Triggers:** Add up to 10 trigger/response pairs to automate responses.
- **Favorites Management:** Save favorite BBS addresses for quick access.
- **Live Chatroom Members Panel:** View active users in the chatroom.
- **Desktop and Web UI:** Interact via a Tkinter desktop app or a web-based interface.
- **Hyperlink Detection and Preview:** (Web UI) Detect URLs and display a thumbnail preview when hovered.

---

## Requirements

- **Python 3.7+**
- **Tkinter** (usually included with Python)
- **telnetlib3**
- **Pillow** (for image preview in the desktop app)
- **requests**

A sample `requirements.txt` is provided:
```txt
telnetlib3>=1.0.2
Pillow
requests
```

---

## Setup Instructions

### Prerequisites
- Python 3.7 or higher
- Windows OS (for sound features)
- Internet connection
- Administrative privileges to install Python packages

### Installation Steps

1. **Install Python:**
   - Download Python from [python.org](https://python.org/downloads)
   - Run installer and check "Add Python to PATH"
   - Verify installation by opening Command Prompt and typing:
     ```
     python --version
     ```

2. **Download the Project:**
   - Download this project as ZIP or clone it
   - Extract to a folder of your choice
   - Remember the path (example: `C:\Users\YourName\Documents\TT`)

3. **Set Up Virtual Environment:**
   ```powershell
   # Open PowerShell and navigate to project folder
   cd C:\Users\YourName\Documents\TT

   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   .\venv\Scripts\Activate.ps1

   # If you get a security error, run:
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   # Then try activating again
   ```

4. **Install Dependencies:**
   ```powershell
   # Make sure venv is activated (you see "(venv)" in prompt)
   pip install -r requirements.txt
   ```

---

## Running the Application

1. **Start the Program:**
   ```powershell
   # Make sure you're in the project directory with venv activated
   python main.py
   ```

2. **Initial Configuration:**
   - Click "Settings" to configure font and colors
   - Set up any triggers you want in the "Triggers" window
   - Add favorite BBS addresses in the "Favorites" window

3. **Connect to a BBS:**
   - Enter BBS host address and port
   - Click "Connect"
   - Enter username/password when prompted
   - Check "Remember" to save credentials

### Optional Features

#### MajorLink Mode
- Filters out system messages and banners
- Toggle with checkbox in main window
- Recommended for cleaner chat experience

#### Keep Alive
- Prevents timeout disconnects
- Sends periodic signals to server
- Enable via checkbox in main window

#### Sound Notifications
- Plays sound on private messages
- Requires Windows OS
- Always enabled by default

---

## Usage

- **Connecting:**
  - Enter the BBS host and port in the connection settings, then click **Connect**. The **Connect** button will change to **Disconnect** when connected.

- **Username/Password:**
  - Use the Username and Password fields to send your credentials. You can enable “Remember” to store these locally.

- **Sending Messages:**
  - Type a message into the input field at the bottom. Press **Enter** to send. If the input is empty, an ENTER (newline) keystroke will be sent.

- **Triggers:**
  - Click the **Triggers** button to open a small window with 10 rows (2 columns: Trigger and Response). Fill in your automation pairs and click **Save**. When a message received in the terminal matches any trigger (case‑insensitive), the associated response is automatically sent.

- **Chatlog:**
  - Click the **Chatlog** button to view a chatlog window. The left pane lists users who have sent messages, and clicking a username displays their messages in the right pane. Use the **Clear** button to clear the log for the selected user.

- **Favorites:**
  - Use the **Favorites** button to manage and quickly select favorite BBS addresses.

- **Additional Controls:**
  - Options like **MUD Mode**, **Keep Alive**, and action buttons (Wave, Smile, Dance, Bow) are available to customize your experience.

- **Chatroom Members:**
  - The chat members panel (on the right side of the desktop app) shows active members.

---

## File Structure

```
.
├── main.py            # Main Tkinter desktop application for BBS Telnet
├── ui.html            # Web-based UI for the BBS Terminal
├── ui.js              # JavaScript for the web UI (triggers, favorites, chatlog, etc.)
├── requirements.txt   # Python dependencies
├── favorites.json     # (Auto-generated) Stores favorite BBS addresses
├── triggers.json      # (Auto-generated) Stores trigger/response pairs
├── chatlog.json       # (Auto-generated) Stores chat log messages
├── chat_members.json  # (Auto-generated) Stores current chatroom members
└── last_seen.json     # (Auto-generated) Stores last seen timestamps for members
```

### Files Created

The program creates several JSON files in its directory:
```
favorites.json      - Saved BBS addresses
triggers.json       - Automation triggers
chatlog.json       - Saved chat messages
chat_members.json   - Current chat participants
last_seen.json     - User activity timestamps
font_settings.json  - UI customization settings
username.json      - Saved username (if enabled)
password.json      - Saved password (if enabled)
```

---

## Troubleshooting

- **No Chat Messages Displayed:**
  - Ensure that your regex filters (in `process_data_chunk`) match the format of incoming messages. For public messages, the expected format is `From <username>: <message>` (or similar). Adjust the regex if needed.

- **Triggers Not Firing:**
  - Verify that your trigger strings exactly match parts of the incoming message (case-insensitive). You can test by manually injecting sample messages into the terminal.

- **UI Elements Not Visible:**
  - Do a hard refresh in your browser or restart the desktop app to ensure that the latest HTML/CSS/JS changes are loaded.

- **Connection Issues:**
  - Check that the BBS host and port are correct. Use debugging messages (printed to the console) to see connection status.

- **Sound Not Working:**
  - Verify Windows sound is enabled
  - Check system volume
  - Ensure no other app is blocking sounds

- **Font Issues:**
  - Try default "Courier New" if custom font fails
  - Install missing fonts if needed
  - Use Settings to select available fonts

- **Performance Issues:**
  - Clear chat logs if file gets too large
  - Reduce font size for faster rendering
  - Disable MajorLink mode if CPU usage is high

### Support Files

If you need to reset settings, delete these files:
```
font_settings.json
triggers.json
favorites.json
```
The program will recreate them with defaults on next start.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
