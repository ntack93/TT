# BBS Telnet Terminal

A retro Telnet terminal application for connecting to BBS systems. This project provides both a desktop UI (using Tkinter) and a web-based UI (HTML/JavaScript) to interact with a BBS server. It includes features such as:

- **Connection Settings:** Connect/disconnect from the BBS.
- **Username/Password Handling:** Send and optionally remember credentials.
- **Chatlog:** Save and review chat messages locally.
- **Triggers:** Create automation triggers to send custom responses when certain text appears.
- **Favorites:** Manage favorite BBS addresses.
- **Chatroom Members Panel:** View active members.
- **Live URL Previews:** Hyperlink detection with live preview thumbnails (web UI).

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Setup Instructions](#setup-instructions)
  - [Python Virtual Environment (Windows/PowerShell)](#python-virtual-environment-windowspowershell)
- [Running the Desktop Application](#running-the-desktop-application)
- [Running the Web UI](#running-the-web-ui)
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

### Python Virtual Environment (Windows/PowerShell)

1. **Open PowerShell** and navigate to your project directory:
   ```powershell
   cd path\to\your\project
   ```

2. **Create the Virtual Environment:**
   ```powershell
   python -m venv venv
   ```

3. **Activate the Virtual Environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   _If you get a script execution policy error, run:_
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
   ```

4. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

---

## Running the Desktop Application

1. **Ensure your virtual environment is activated.**
2. **Run the main Python script:**
   ```powershell
   python main.py
   ```
3. The desktop window (Tkinter UI) should open, displaying connection settings, chat output, input fields, and additional panels (chatlog, triggers, favorites, etc.).


## Usage

- **Connecting:**  
  Enter the BBS host and port in the connection settings, then click **Connect**. The **Connect** button will change to **Disconnect** when connected.

- **Username/Password:**  
  Use the Username and Password fields to send your credentials. You can enable “Remember” to store these locally.

- **Sending Messages:**  
  Type a message into the input field at the bottom. Press **Enter** to send. If the input is empty, an ENTER (newline) keystroke will be sent.

- **Triggers:**  
  Click the **Triggers** button to open a small window with 10 rows (2 columns: Trigger and Response). Fill in your automation pairs and click **Save**. When a message received in the terminal matches any trigger (case‑insensitive), the associated response is automatically sent.

- **Chatlog:**  
  Click the **Chatlog** button to view a chatlog window. The left pane lists users who have sent messages, and clicking a username displays their messages in the right pane. Use the **Clear** button to clear the log for the selected user.

- **Favorites:**  
  Use the **Favorites** button to manage and quickly select favorite BBS addresses.

- **Additional Controls:**  
  Options like **MUD Mode**, **Keep Alive**, and action buttons (Wave, Smile, Dance, Bow) are available to customize your experience.

- **Chatroom Members:**  
  The chat members panel (on the right side of the desktop app) shows active members.

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

---

## Troubleshooting

- **No Chat Messages Displayed:**  
  Ensure that your regex filters (in `process_data_chunk`) match the format of incoming messages. For public messages, the expected format is `From <username>: <message>` (or similar). Adjust the regex if needed.

- **Triggers Not Firing:**  
  Verify that your trigger strings exactly match parts of the incoming message (case-insensitive). You can test by manually injecting sample messages into the terminal.

- **UI Elements Not Visible:**  
  Do a hard refresh in your browser or restart the desktop app to ensure that the latest HTML/CSS/JS changes are loaded.

- **Connection Issues:**  
  Check that the BBS host and port are correct. Use debugging messages (printed to the console) to see connection status.

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
```
