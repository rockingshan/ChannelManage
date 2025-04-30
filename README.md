# LCN Channel Restart Tool

![LCN Channel Restart Tool](https://via.placeholder.com/800x200.png?text=LCN+Channel+Restart+Tool)  
*Manage and restart IPTV channels with ease using a user-friendly GUI.*

The **LCN Channel Restart Tool** is a Python-based desktop application designed to streamline the management and restarting of IPTV channels via SSH. It supports processing raw CSV files, securely storing server credentials, and playing UDP/HTTP streams using VLC Media Player. Built with a Tkinter GUI, this tool is ideal for IPTV service administrators who need to automate channel restarts, verify stream status, and manage server configurations efficiently.

The application can be run as a Python script or packaged as a standalone Windows executable (`manage.exe`) for easy distribution.

---

## Table of Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Requirements](#requirements)
- [Installation](#installation)
  - [For End-Users (Using the Executable)](#for-end-users-using-the-executable)
  - [For Developers (Running the Source Code)](#for-developers-running-the-source-code)
- [Usage](#usage)
- [Building the Executable](#building-the-executable)
- [Security Considerations](#security-considerations)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Features

- **Process Raw CSV Files**: Import channel data (LCN, server IP, channel name, UDP/HTTP URLs) from CSV files and store it in a SQLite database.
- **Secure Server Management**: Add, delete, and store server credentials (IP, username, password) with passwords encrypted using Fernet symmetric encryption.
- **SSH Command Execution**: Execute remote SSH commands to restart IPTV channels based on Logical Channel Number (LCN).
- **VLC Integration**: Play UDP and HTTP streams directly in VLC Media Player, with persistent VLC path storage.
- **Real-Time Status Checking**: Automatically check UDP/HTTP stream status, displaying "OK" or "Offline".
- **Log Management**: Generate and view detailed logs of SSH commands and outputs, saved in UTF-8 with BOM for compatibility.
- **Portable Executable**: Build a standalone Windows `.exe` using PyInstaller for easy distribution.
- **Persistent Data Storage**: Store database (`servers.db`) and encryption key (`key.key`) in the executable’s directory for data persistence.

---

## Screenshots

*Coming soon! Screenshots of the GUI will be added to showcase the main window, server management dialog, and log viewer.*

> **Note**: Want to contribute screenshots? Capture the GUI and submit them via a pull request to the `screenshots/` folder!

---

## Requirements

- **Operating System**: Windows (for `.exe`); Python version supports Windows, macOS, and Linux.
- **Python**: 3.8 or higher (for running the source code).
- **VLC Media Player**: Required for playing UDP/HTTP streams.
- **Dependencies** (for source code):
  - `paramiko`: For SSH connections.
  - `cryptography`: For password encryption.
  - `python-dotenv`: For loading `.env` variables.
- **Optional** (for building `.exe`):
  - `pyinstaller`: To create the standalone executable.

---

## Installation

### For End-Users (Using the Executable)

1. **Download the Executable**:
   - Get `manage.exe` from the [Releases](https://github.com/yourusername/lcn-channel-restart-tool/releases) page or a trusted source.
   - Place `manage.exe` in a writable directory (e.g., `C:\Users\YourName\LCNTool`).
   - Ensure `app.ico` is in the same directory for the application icon.

2. **Install VLC Media Player**:
   - Download and install VLC from [VideoLAN](https://www.videolan.org/vlc/).

3. **Configure the Environment**:
   - Create a `.env` file in the same directory as `manage.exe`:
     ```bash
     HTTP_BASE_URL=http://<YOUR_IP>:<YOUR_PORT>
     ```
   - Replace `<YOUR_IP>:<YOUR_PORT>` with your server’s HTTP base URL (e.g., `http://192.168.1.100:4022`).

4. **Run the Application**:
   - Double-click `manage.exe` to launch the GUI.
   - See the [Usage](#usage) section for how to use the tool.

### For Developers (Running the Source Code)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/yourusername/lcn-channel-restart-tool.git
   cd lcn-channel-restart-tool
