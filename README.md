# SCGM-Auto-Br

A automation for Battle Royale game sessions

## Key Features

- **Automated Workflow**: Manages the complete cycle from initial queue to match completion.
- **Integrated Asset Management**: Built-in GUI for managing detection targets, including an interactive screen capture and cropping tool.
- **Discord Integration**: Automated notifications via Webhooks for match state changes.

## Prerequisites

- Windows Operating System
- Python 3.10 or higher

## Installation

### From Source
1. Clone the repository:
   ```bash
   git clone https://github.com/Comelt5920/GPO-auto-battleroyale.git
   cd GPO-auto-battleroyale
   ```
2. Initialize and activate the virtual environment:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```
3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute the application:
   ```bash
   python main.py
   ```

### Standalone Executable
Standardized binaries are available under the [Releases](https://github.com/Comelt5920/GPO-auto-battleroyale/releases) section.

## Operation Manual

1. Launch the application.
2. Navigate to the **Asset Management** tab.
3. Configure detection targets using the **Capture Helper** or by selecting existing image files.
4. Return to the **Bot Control** tab and initiate the automation via the **START** button or the **F1** hotkey.

## Technical Build Instructions

To generate a standalone executable using PyInstaller, execute the following command:
```bash
pyinstaller --onefile --noconsole --name SCGM_AutoBR_v1.0.0 main.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---
*Developed for advanced game automation and state-based detection.*
