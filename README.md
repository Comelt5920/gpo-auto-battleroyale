# SCGM-Auto-Br (Advanced)

A Python automation tool for Battle Royale games featuring a complete match loop, Discord alerts, and anti-AFK movement.

## Features
- **Standard Tkinter GUI**: Stable and lightweight interface.
- **Match Tracker**: Tracks total matches and session time.
- **Discord Integration**: Real-time "Match Found" notifications via Webhooks.
- **AFK Protection**: 5 minutes of random WASD movement during matches.
- **Full Automation Loop**: Queue -> Mode Select -> Match -> Loot/Finish -> Restart.

## Setup Instructions

1. **Images (Assets)**:
   Place these screenshots (PNG) inside the `assets/` folder:
   - `queue.png`: The initial queue button.
   - `br_mode.png`: The Battle Royale mode select button.
   - `solo_mode.png`: The Solo mode button.
   - `match_found.png`: A unique HUD element that appears when a match starts.
   - `open.png`: The post-match "Open" button.
   - `continue.png`: The final "Continue" button to return to lobby.

2. **Discord**: (Optional) Paste your Webhook URL into the GUI to receive alerts.

## How to Run
```bash
.\venv\Scripts\python main.py
```
