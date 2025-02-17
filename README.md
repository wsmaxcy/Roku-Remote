# Roku Remote

A visually polished and functional Roku remote written in Python (PyQt5). This project features:

- **Network Discovery**: Automatically scans your local subnet (via [scapy](https://pypi.org/project/scapy/)) to find a Roku device on port 8060.  
- **Animated Glow Buttons**: Each button “fades in” (brightens) when you move your mouse, and “fades out” (dims) after a period of inactivity.  
- **Custom D-Pad**: A plus-shaped background is painted behind the Up/Down/Left/Right/OK buttons, using dynamic geometry and a purple Roku theme.  
- **API Integration**: Uses the Roku ECP (External Control Protocol) to send commands like `keypress/home` or `launch/12` for Netflix, etc.  
- **Qt UI**: A fully skinned interface with gradient backgrounds, 3D-styled buttons, and a draggable, frameless window.  

---

## Table of Contents

1. [Requirements](#requirements)  
2. [Installation](#installation)  
3. [Usage](#usage)  
4. [Features](#features)  
5. [Screenshot](#screenshot)  
6. [License](#license)  

---

## Requirements

- **Python 3.7+** (tested up to 3.10 or 3.11, for example)  
- [PyQt5](https://pypi.org/project/PyQt5/)  
- [scapy](https://pypi.org/project/scapy/)  
- A local network with a Roku device accessible on port 8060  

(Optional) **Wireshark** or other network tools can be installed, but not strictly required.

---

## Installation

1. **Clone** or download this repo:

   ```bash
   git clone https://github.com/YOUR_USERNAME/roku-remote-pyqt.git
    ```

2. **Install dependencies** (preferably in a virtual environment):

    ```bash
    pip install -r requirements.txt
    ```

3. **Optional** On Windows, you may need to run Python with elevated privileges for scapy to properly send ARP packets.

---

## Usage

1. **Run** the main script:
    
```python
python remote.py
```
    
2. **UI** will appear as a frameless window. You can **drag** it around by clicking anywhere on its surface and moving your mouse.
    
3. **Scan** for Roku: On the “Connect” tab, click **“Scan”**. If discovered successfully, it displays `Roku found at XXX.XXX.XXX.XXX`.
    
4. **Remote** features:
    - **Power** button (⏻) attempts to toggle Roku power (note: some Roku devices don’t support real power toggle).
    - **Back** (⏴), **Home** (⌂) let you navigate basic Roku functions.
    - **Arrows** (▲, ▼, ◀, ▶) & **OK** in the center to navigate the GUI.
    - **B1–B4** at the bottom can launch specific apps or be changed via right-click (supports Netflix, Hulu, Max, Apple TV, etc.).
    - **Typing** (on the “Search” tab) is a placeholder for text input logic.
5. **Close** the window by clicking the small “X” in the top-right corner.

---
## Features

- **Frameless Window**: Painted with a custom gradient, including a purple “ROKU” ribbon at the bottom.
- **Drag** anywhere: No title bar, so a custom mouse event approach handles movement.
- **Glow Animations**: Buttons start dim (#000000 or #808080) and fade to bright (#ffffff) on user activity, then fade out after ~10s idle.
- **D-Pad**: The arrow + OK area is absolutely positioned to keep them close, with a painted shape behind them forming a “plus” with rounded corners.
- **scapy-based** Network Discovery: Scans subnets to find the Roku’s IP on port 8060.

---
## Screenshot

![Screenshot](https://github.com/wsmaxcy/Roku-Remote/blob/main/img/screenshot.png)

---
## License

This project is released under the **MIT License**. See LICENSE for details.
You’re welcome to modify, distribute, or integrate it in your own projects.