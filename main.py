import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import time
import os
import json
import random
import requests
from datetime import datetime
import pyautogui
import pydirectinput
import keyboard
import traceback
from PIL import Image, ImageTk

# Basic Config
CONFIG_FILE = "config.json"
ASSETS_DIR = "assets"
LOG_FILE = "debug_log.txt"

class SCGMAutoBR:
    def __init__(self, root):
        self.root = root
        self.root.title("SCGM-Auto-Br (Advanced)")
        self.root.geometry("600x650")
        self.root.attributes('-topmost', True)
        
        self.is_running = False
        self.match_count = 0
        self.start_time = None
        self.config = self.load_config()
        self.asset_previews = {}
        self.match_start_time = time.time()
        self.last_leave_click_time = 0
        self.last_punch_time = 0
        
        keyboard.add_hotkey('f1', self.toggle_bot_hotkey)
        
        self.setup_ui()
        self.log("Bot Initialized. Press F1 to Start/Stop!")

    def toggle_bot_hotkey(self):
        """Thread-safe way to trigger toggle from hotkey."""
        self.root.after(0, self.toggle_bot)

    def load_config(self):
        default_config = {
            "discord_webhook": "",
            "confidence": 0.8,
            "scan_interval": 2.0,
            "match_mode": "full", # New: "full" or "quick"
            "movement_duration": 300,  # 5 minutes in seconds
            "images": {
                "change": "change.png",
                "br_mode": "br_mode.png",
                "solo_mode": "solo_mode.png",
                "return_to_lobby_alone": "leave.png",
                "ultimate": "ultimate.png",                 
                "open": "open.png",
                "continue": "continue.png"
            },
            "pos_1": [100, 100],
            "pos_2": [200, 200]
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    user_config = json.load(f)
                    
                    if "images" in user_config:
                        merged_images = default_config["images"].copy()
                        for k, v in user_config["images"].items():
                            if k in merged_images:
                                merged_images[k] = v
                        user_config["images"] = merged_images
                    
                    return {**default_config, **user_config}
            except:
                return default_config
        return default_config

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    def setup_ui(self):
        # Style
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Segoe UI', 10))
        style.configure("Header.TLabel", font=('Segoe UI', 16, 'bold'))

        # Tab Control
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Tab 1: Main Bot
        self.main_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.main_tab, text=" Bot Control ")
        self.setup_main_tab()

        # Tab 2: Assets
        self.assets_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.assets_tab, text=" Asset Management ")
        self.setup_assets_tab()

    def setup_main_tab(self):
        # Header
        ttk.Label(self.main_tab, text="SCGM-Auto-Br", style="Header.TLabel").pack(pady=10)

        stats_frame = ttk.LabelFrame(self.main_tab, text=" Match Stats ", padding="5")
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_match = ttk.Label(stats_frame, text="Matches: 0")
        self.lbl_match.pack(side=tk.LEFT, padx=10)
        
        self.lbl_timer = ttk.Label(stats_frame, text="Timer: 00:00:00")
        self.lbl_timer.pack(side=tk.RIGHT, padx=10)

        # Discord Config
        ttk.Label(self.main_tab, text="Discord Webhook:").pack(anchor=tk.W, pady=(10, 0))
        
        webhook_frame = ttk.Frame(self.main_tab)
        webhook_frame.pack(fill=tk.X, pady=5)
        
        self.ent_webhook = ttk.Entry(webhook_frame, show="*")
        self.ent_webhook.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_webhook.insert(0, self.config.get("discord_webhook", ""))
        
        self.btn_show_webhook = ttk.Button(webhook_frame, text="Show", width=6, command=self.toggle_webhook_visibility)
        self.btn_show_webhook.pack(side=tk.RIGHT, padx=(5, 0))

        # Confidence Config
        conf_frame = ttk.LabelFrame(self.main_tab, text=" Detection Sensitivity (Confidence) ", padding="5")
        conf_frame.pack(fill=tk.X, pady=5)
        
        inner_conf = ttk.Frame(conf_frame)
        inner_conf.pack(fill=tk.X)
        
        ttk.Label(inner_conf, text="Value (0.1 - 1.0):").pack(side=tk.LEFT, padx=5)
        self.ent_conf = ttk.Entry(inner_conf, width=10)
        self.ent_conf.pack(side=tk.LEFT, padx=5)
        self.ent_conf.insert(0, str(self.config.get("confidence", 0.8)))
        
        ttk.Button(inner_conf, text="Set", width=8, command=self.on_conf_change).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(conf_frame, text="Example: 0.80 (Standard) | 0.95 (Very Strict) | 0.60 (Very Loose)", 
                  font=('Segoe UI', 7), foreground="gray").pack(pady=(5,0))

        # Match Mode Selection
        mode_frame = ttk.LabelFrame(self.main_tab, text=" Match Mode ", padding="5")
        mode_frame.pack(fill=tk.X, pady=10)
        
        self.mode_var = tk.StringVar(value=self.config.get("match_mode", "full"))
        
        ttk.Radiobutton(mode_frame, text="Full Match (Wait until end)", variable=self.mode_var, 
                        value="full", command=self.on_mode_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Quick Leave (Exit early)", variable=self.mode_var, 
                        value="quick", command=self.on_mode_change).pack(side=tk.LEFT, padx=10)

        # Controls
        btn_frame = ttk.Frame(self.main_tab)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(btn_frame, text="Status: IDLE", font=('Segoe UI', 10, 'bold'))
        self.status_label.pack(pady=5)

        self.btn_toggle = ttk.Button(btn_frame, text="START BOT", command=self.toggle_bot)
        self.btn_toggle.pack(fill=tk.X)

        # Console
        ttk.Label(self.main_tab, text="Activity Log:").pack(anchor=tk.W)
        self.console = scrolledtext.ScrolledText(self.main_tab, height=13, state='disabled', font=('Consolas', 9))
        self.console.pack(fill=tk.BOTH, expand=True, pady=5)

    def on_mode_change(self):
        """Updates config when user changes match mode."""
        self.config["match_mode"] = self.mode_var.get()
        self.save_config()
        self.log(f"Mode changed to: {self.config['match_mode'].replace('_', ' ').upper()}")

    def pick_coord(self, key, label_widget):
        """Opens the coordinate picker tool with better reliability."""
        self.log(f"Preparing to set {key}... Main window will minimize.")
        self.root.iconify()
        time.sleep(1.0) # Wait for window to minimize completely
        
        try:
            screenshot = pyautogui.screenshot()
            pick_tool = CoordinatePicker(self.root, screenshot)
            self.root.wait_window(pick_tool.top) # Wait for picker to close
            
            if pick_tool.result:
                self.config[key] = pick_tool.result
                prefix = "Book" if key == "pos_1" else "Str+"
                label_widget.config(text=f"{prefix}: {pick_tool.result}")
                self.save_config()
                self.log(f"Successfully set {key} to: {pick_tool.result}")
            else:
                self.log(f"Selection for {key} was cancelled.")
        except Exception as e:
            self.log(f"Set Pos Error: {e}", is_error=True)
        
        self.root.deiconify()
        self.root.attributes("-topmost", True) # Ensure it comes back to front

    def on_conf_change(self, event=None):
        """Updates config when confidence text is set."""
        try:
            val = float(self.ent_conf.get())
            if 0.1 <= val <= 1.0:
                self.config["confidence"] = val
                self.save_config()
                self.log(f"Confidence set to: {val:.2f}")
            else:
                self.log("Invalid Confidence: must be between 0.1 and 1.0", is_error=True)
        except ValueError:
            self.log("Invalid Confidence: please enter a number", is_error=True)

    def setup_assets_tab(self):
        # Scrollable container for assets
        canvas = tk.Canvas(self.assets_tab)
        scrollbar = ttk.Scrollbar(self.assets_tab, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Asset Items
        for key, default_name in self.config["images"].items():
            frame = ttk.LabelFrame(scroll_frame, text=f" {key.replace('_', ' ').title()} ", padding="5")
            frame.pack(fill=tk.X, pady=5, padx=5)
            
            # Left: Info
            info_frame = ttk.Frame(frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            lbl_path = ttk.Label(info_frame, text=f"File: {self.config['images'][key]}", font=('Segoe UI', 8))
            lbl_path.pack(anchor=tk.W)
            
            btn_browse = ttk.Button(info_frame, text="Choose Image", width=15, 
                                    command=lambda k=key, l=lbl_path: self.browse_asset(k, l))
            btn_browse.pack(anchor=tk.W, pady=2)

            btn_capture = ttk.Button(info_frame, text="Capture Helper", width=15,
                                     command=lambda k=key, l=lbl_path: self.start_capture_helper(k, l))
            btn_capture.pack(anchor=tk.W, pady=2)

            # Special Coordinates for Ultimate (Auto-put-stats)
            if key == "ultimate":
                ttk.Separator(info_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
                ttk.Label(info_frame, text="Auto-put-stats settings:", font=('Segoe UI', 8, 'bold')).pack(anchor=tk.W)
                
                pos1_frame = ttk.Frame(info_frame)
                pos1_frame.pack(fill=tk.X, pady=2)
                self.lbl_pos1 = ttk.Label(pos1_frame, text=f"Book: {self.config.get('pos_1')}", font=('Segoe UI', 8))
                self.lbl_pos1.pack(side=tk.LEFT)
                ttk.Button(pos1_frame, text="Set Pos", width=8, 
                           command=lambda l=self.lbl_pos1: self.pick_coord("pos_1", l)).pack(side=tk.RIGHT)

                pos2_frame = ttk.Frame(info_frame)
                pos2_frame.pack(fill=tk.X, pady=2)
                self.lbl_pos2 = ttk.Label(pos2_frame, text=f"Str+: {self.config.get('pos_2')}", font=('Segoe UI', 8))
                self.lbl_pos2.pack(side=tk.LEFT)
                ttk.Button(pos2_frame, text="Set Pos", width=8, 
                           command=lambda l=self.lbl_pos2: self.pick_coord("pos_2", l)).pack(side=tk.RIGHT)
            
            # Right: Preview
            preview_label = ttk.Label(frame)
            preview_label.pack(side=tk.RIGHT)
            self.update_preview(key, preview_label)

        # Bottom Actions in Assets Tab
        action_frame = ttk.Frame(scroll_frame)
        action_frame.pack(fill=tk.X, pady=10, padx=5)
        
        ttk.Button(action_frame, text="Open Debug Log File", command=self.open_log_file).pack(fill=tk.X)

    def open_log_file(self):
        """Opens the debug log file in the default text editor."""
        if os.path.exists(LOG_FILE):
            os.startfile(LOG_FILE)
        else:
            self.log("Log file not found yet.")

    def start_capture_helper(self, key, label_widget):
        """Starts the capture countdown and overlay tool."""
        self.root.iconify() # Minimize main window
        self.log(f"Capture starting in 5 seconds for {key}...")
        
        def run_capture():
            time.sleep(5)
            screenshot = pyautogui.screenshot()
            
            cap_tool = ScreenCaptureTool(self.root, screenshot, key)
            self.root.wait_window(cap_tool.top)
            
            if cap_tool.result_path:
                self.config["images"][key] = cap_tool.result_path
                label_widget.config(text=f"File: {os.path.basename(cap_tool.result_path)}")
                self.save_config()
                self.log(f"Captured and saved {key} asset.")
                
                preview_label = label_widget.master.master.winfo_children()[-1] 
                self.update_preview(key, preview_label)
            
            self.root.deiconify()

        threading.Thread(target=run_capture, daemon=True).start()

    def browse_asset(self, key, label_widget):
        file_path = filedialog.askopenfilename(
            initialdir=ASSETS_DIR,
            title="Select Image",
            filetypes=(("PNG files", "*.png"), ("All files", "*.*"))
        )
        if file_path:
            rel_path = os.path.relpath(file_path, os.getcwd())
            self.config["images"][key] = rel_path
            label_widget.config(text=f"File: {os.path.basename(rel_path)}")
            self.save_config()
            self.log(f"Updated {key} asset.")
            
            preview_label = label_widget.master.master.winfo_children()[-1] 
            self.update_preview(key, preview_label)

    def update_preview(self, key, label_widget):
        path = self.config["images"][key]
        if not os.path.isabs(path):
            path = os.path.join(os.getcwd(), path)
            
        if os.path.exists(path):
            try:
                img = Image.open(path)
                img.thumbnail((60, 60)) # Thumbnail size
                photo = ImageTk.PhotoImage(img)
                label_widget.config(image=photo)
                label_widget.image = photo # Keep reference
                self.asset_previews[key] = photo
            except Exception as e:
                label_widget.config(text="Error", image="")
        else:
            label_widget.config(text="Missing", image="")

    def toggle_webhook_visibility(self):
        """Toggles masking of the webhook entry."""
        if self.ent_webhook.cget('show') == '*':
            self.ent_webhook.config(show='')
            self.btn_show_webhook.config(text="Hide")
        else:
            self.ent_webhook.config(show='*')
            self.btn_show_webhook.config(text="Show")

    def log(self, msg, is_error=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # UI Log
        self.console.configure(state='normal')
        self.console.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.console.see(tk.END)
        self.console.configure(state='disabled')
        
        # File Log
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{full_timestamp}] {'[ERROR] ' if is_error else ''}{msg}\n")
        except:
            pass

    def send_discord(self, message):
        webhook = self.ent_webhook.get().strip()
        if not webhook:
            return
        try:
            requests.post(webhook, json={"content": message})
        except Exception as e:
            self.log(f"Discord Error: {e}")

    def toggle_bot(self):
        if not self.is_running:
            webhook = self.ent_webhook.get().strip()
            self.config["discord_webhook"] = webhook
            self.save_config()
            
            self.is_running = True
            self.btn_toggle.config(text="STOP BOT")
            self.start_time = time.time()
            self.update_timer()
            
            self.thread = threading.Thread(target=self.bot_loop, daemon=True)
            self.thread.start()
        else:
            self.is_running = False
            self.btn_toggle.config(text="START BOT")
            self.log("Bot stopping...")

    def update_timer(self):
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.lbl_timer.config(text=f"Timer: {h:02}:{m:02}:{s:02}")
            self.root.after(1000, self.update_timer)

    def human_click(self, x, y):
        """Moves mouse smoothly and clicks using pydirectinput for better game compatibility."""
        if not self.is_running: return
        
        # Randomize target slightly within a reasonable button area
        target_x = int(x + random.randint(-8, 8))
        target_y = int(y + random.randint(-8, 8))
        
        pydirectinput.moveTo(target_x, target_y, duration=random.uniform(0.4, 0.8))
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.moveRel(random.randint(-3, 3), random.randint(-3, 3), relative=True)
        
        # Short pause before clicking
        time.sleep(random.uniform(0.1, 0.4))
        
        # Click and Hold
        pydirectinput.mouseDown()
        time.sleep(random.uniform(0.05, 0.15))
        pydirectinput.mouseUp()
        time.sleep(1.0) # Delay after click to let UI update

    def find_and_click(self, img_name, timeout=1):
        if not self.is_running: return False
        
        path = self.config["images"][img_name]
        if not os.path.exists(path):
            # self.log(f"Warning: Missing asset {path}")
            return False
            
        try:
            pos = pyautogui.locateOnScreen(path, confidence=self.config["confidence"], grayscale=True)
            if pos:
                center = pyautogui.center(pos)
                self.log(f"Found {img_name}!")
                self.human_click(center.x, center.y)
                return True
        except Exception as e:
            pass
        return False

    def random_move(self):
        """Random WASD movement and actions until the match ends."""
        mode = self.config.get("match_mode", "full")
        self.log(f"Starting phase: {mode.upper()} MODE")
        
        keys = ['w', 'a', 's', 'd']
        start_game_time = time.time()
        
        while self.is_running:
            if not self.is_running: break
            key = random.choice(keys)
            duration = random.uniform(0.2, 0.6)
            pydirectinput.keyDown(key)
            time.sleep(duration)
            pydirectinput.keyUp(key)

            mode = self.config.get("match_mode", "full")
            
            # 2. Check for end-match screen
            if self.is_image_visible("open") or self.is_image_visible("continue"):
                self.log("End-match screen detected! Stopping phase.")
                break
            
            # Periodic AFK click and Leave check if button visible (every 60s)
            is_leave_visible = self.is_image_visible("return_to_lobby_alone", confidence=0.7)
            if is_leave_visible and (time.time() - self.last_punch_time > 60):
                pydirectinput.click() # AFK prevention
                self.last_punch_time = time.time()
            
            if is_leave_visible and (time.time() - self.last_leave_click_time > 60):
                if mode == "quick": # Only click the actual button in Quick Leave
                    if self.find_and_click("return_to_lobby_alone"):
                        self.log("Quick Leave: Exit button clicked.")
                        self.last_leave_click_time = time.time()
                else: # In Full Match, just update time to keep it periodic for AFK click
                    self.last_leave_click_time = time.time()
            
            # 3. Sub-actions (Look around)
            action_roll = random.random()
            if action_roll < 0.2: # 20% chance to look around
                move_x = random.randint(-120, 120)
                pydirectinput.moveRel(move_x, 0, relative=True)
            
            # 4. Safety break
            if time.time() - start_game_time > 1080:
                self.log("Max match time reached (18m). Force checking for end buttons.")
                break
            
            time.sleep(random.uniform(0.5, 1.2))
        
        self.log("Match phase complete.")

    def auto_punch(self):
        """The auto-punching activation sequence."""
        try:
            self.log("AUTO-PUNCH TRIGGERED! Setting up stats...")
            
            # 1. Press M, wait 1s
            pydirectinput.press('m')
            time.sleep(1.0)
            
            # 2. Click Pos #1, wait 2s
            pos1 = self.config.get("pos_1", [0, 0])
            self.human_click(pos1[0], pos1[1]) # Safe human-like click
            time.sleep(1.5) # Reduced extra sleep since human_click has built-in 1s
            
            # 3. Click Pos #2 11 times, every 0.5s
            pos2 = self.config.get("pos_2", [0, 0])
            for i in range(11):
                if not self.is_running: break
                self.human_click(pos2[0], pos2[1])
                # Note: human_click has internal movement and 1s delay.
                # If 0.5s is strictly required, we might need a faster version,
                # but 'human interaction' was specifically requested.
            
            # 4. Press M, wait 1s
            pydirectinput.press('m')
            time.sleep(1.0)
            
            # 5. Press 1, wait 1s
            pydirectinput.press('1')
            time.sleep(1.0)
            
            # 6. Left Click & Move continuously until Return to lobby alone
            self.log("Auto-punching mode ACTIVE. Punching (Movement starts in 2m)...")
            keys = ['w', 'a', 's', 'd']
            punch_start_time = time.time()
            mode = self.config.get("match_mode", "full")
            
            while self.is_running:
                is_leave_visible = self.is_image_visible("return_to_lobby_alone", confidence=0.7)
                
                # Punch Logic: 60s if button visible, 0.05s otherwise
                punch_interval = 60 if is_leave_visible else 0.05
                if time.time() - self.last_punch_time > punch_interval:
                    pydirectinput.click()
                    self.last_punch_time = time.time()
                
                # Move after 2 minutes
                if time.time() - punch_start_time > 120:
                    if random.random() < 0.2:
                        key = random.choice(keys)
                        pydirectinput.keyDown(key)
                        time.sleep(0.2)
                        pydirectinput.keyUp(key)
                
                # Check exit condition
                if self.is_image_visible("open") or self.is_image_visible("continue"):
                    self.log("Match end detected via results screen.")
                    break
                
                # Periodic Leave check (every 60s)
                if is_leave_visible and (time.time() - self.last_leave_click_time > 60):
                    if mode == "quick": # Only click button in Quick mode
                        if self.find_and_click("return_to_lobby_alone"):
                            self.last_leave_click_time = time.time()
                    else:
                        self.last_leave_click_time = time.time()
                
                time.sleep(0.05)
        except Exception as e:
            self.log(f"Auto-punch Error: {e}", is_error=True)

    def is_image_visible(self, img_name, confidence=None):
        """Checks if an image is on screen without clicking it."""
        path = self.config["images"].get(img_name)
        if not path or not os.path.exists(path):
            return False
            
        conf = confidence if confidence is not None else self.config["confidence"]
        try:
            return pyautogui.locateOnScreen(path, confidence=conf, grayscale=True) is not None
        except Exception as e:
            # Only log very specific errors, ignore 'not found' errors
            return False

    def bot_loop(self):
        os.makedirs(ASSETS_DIR, exist_ok=True)
        
        while self.is_running:
            try:
                # 1. State: Lobby / Start Sequence
                self.status_label.config(text="Status: LOBBY / STARTING", foreground="blue")
                
                # Safety Check: If we see end-game buttons while in lobby state, handle them immediately
                if self.is_image_visible("open") or self.is_image_visible("continue"):
                    self.log("End-match screen detected! Jumping to results...")
                    self.handle_post_match()
                    continue

                # Check for deeper menu states first to avoid redundant clicks
                if self.is_image_visible("solo_mode"):
                    if self.find_and_click("solo_mode"):
                        self.log("Solo clicked. Entering match sequence...")
                        self.handle_match_waiting()
                        continue
                elif self.is_image_visible("br_mode"):
                    self.find_and_click("br_mode")
                else:
                    # Only click change if NOT in sub-menus
                    self.find_and_click("change")
                
                time.sleep(self.config["scan_interval"])
                
            except Exception as e:
                error_msg = f"Loop Error: {e}"
                self.log(error_msg, is_error=True)
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(traceback.format_exc() + "\n")
                time.sleep(5)

    def handle_match_waiting(self):
        """Handles the sequence after clicking Solo Mode."""
        self.log("Entering 'Wait for Match' state...")
        match_started = False
        ultimate_triggered = False
        self.status_label.config(text="Status: WAITING FOR MATCH", foreground="orange")
        
        start_wait = time.time()
        self.match_start_time = time.time() # Start timing for Discord report
        last_log_time = time.time()
        
        # Get the correct image path for the start signal
        img_key = "return_to_lobby_alone"
        asset_path = self.config["images"].get(img_key, "missing")
        self.log(f"Waiting for game load signal (Searching for: {os.path.basename(asset_path)})")
        
        # Wait up to 10 minutes for a match
        while time.time() - start_wait < 600 and self.is_running:
            if time.time() - last_log_time > 30:
                elapsed = int(time.time() - start_wait)
                self.log(f"Still waiting for match... ({elapsed}s elapsed)")
                last_log_time = time.time()

            # Check for 'return_to_lobby_alone' button (using slightly lower confidence 0.7 for better detection)
            if self.is_image_visible("return_to_lobby_alone", confidence=0.7):
                self.log("Game loaded: 'Return to lobby' detected.")
                match_started = True
                break
            
            if self.is_image_visible("ultimate"):
                self.log("Game loaded: 'Ultimate' button detected!")
                match_started = True
                ultimate_triggered = True
                break
            
            # Check if we were kicked back to lobby (change cancelled)
            if self.is_image_visible("change"):
                self.log("Lobby detected (Queue cancelled). Retrying sequence.")
                return

            time.sleep(0.5)
        
        if match_started:
            self.match_count += 1
            self.lbl_match.config(text=f"Matches: {self.match_count}")
            self.log(f"Match #{self.match_count} STARTED!")
            
            # 3. State: In Game / Movement
            if ultimate_triggered:
                self.status_label.config(text="Status: AUTO-PUNCHING", foreground="green")
                self.auto_punch()
            else:
                self.status_label.config(text="Status: IN GAME (MOVING)", foreground="green")
                self.random_move()
            
            # 4. State: Post-Match / Waiting for Results
            self.handle_post_match()

    def handle_post_match(self):
        """Processes the 'Open' and 'Continue' buttons after a match."""
        self.log("Post-match phase. Looking for 'Open' or 'Continue'...")
        self.status_label.config(text="Status: MATCH ENDED", foreground="purple")
        
        results_found = False
        start_results_wait = time.time()
        while not results_found and self.is_running:
            # Timeout if result screen never shows up (e.g. disconnected)
            if time.time() - start_results_wait > 300:
                self.log("Results screen timeout. Returning to lobby.")
                break

            if self.find_and_click("open"):
                elapsed_match = int(time.time() - self.match_start_time)
                mins = elapsed_match // 60
                secs = elapsed_match % 60
                time_str = f"{mins} min {secs} sec"
                self.log(f"'Open' clicked. Total Process Time: {time_str}")
                self.send_discord(f"Queue #{self.match_count} Finish time: {time_str}")
                time.sleep(3)
            
            if self.find_and_click("continue") or self.find_and_click("return_to_lobby_alone"):
                self.log("Exit button clicked. Returning to Lobby.")
                results_found = True
                time.sleep(5)
                break
            
            time.sleep(4)

class ScreenCaptureTool:
    def __init__(self, parent, screenshot, key):
        self.parent = parent
        self.screenshot = screenshot
        self.key = key
        self.result_path = None
        
        # Overlay Window
        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.config(cursor="cross")
        
        # Display Screenshot
        self.tk_img = ImageTk.PhotoImage(self.screenshot)
        self.canvas = tk.Canvas(self.top, cursor="cross", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        # Selection Box
        self.start_x = None
        self.start_y = None
        self.rect = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        
        # Help Text
        self.canvas.create_text(20, 20, text="Drag to select your button. Press ESC to cancel.", 
                                anchor=tk.NW, fill="white", font=("Arial", 14, "bold"))

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect: self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline='red', width=2)

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        
        # Ensure correct coordinates if dragging backwards
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)
        
        if right - left < 5 or bottom - top < 5:
            return # Too small

        # Crop and Save
        cropped = self.screenshot.crop((left, top, right, bottom))
        asset_name = f"{self.key}.png"
        save_path = os.path.join(ASSETS_DIR, asset_name)
        os.makedirs(ASSETS_DIR, exist_ok=True)
        cropped.save(save_path)
        
        self.result_path = os.path.join(ASSETS_DIR, asset_name)
        self.top.destroy()

class CoordinatePicker:
    """A tool to pick a single x, y coordinate from the screen."""
    def __init__(self, parent, screenshot):
        self.parent = parent
        self.screenshot = screenshot
        self.result = None
        
        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.config(cursor="cross")
        
        self.tk_img = ImageTk.PhotoImage(self.screenshot)
        self.canvas = tk.Canvas(self.top, cursor="cross", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        
        self.canvas.create_text(20, 20, text="Click ANYWHERE to set the coordinate. Press ESC to cancel.", 
                                anchor=tk.NW, fill="red", font=("Arial", 16, "bold"))
        
        self.canvas.bind("<Button-1>", self.on_click)
        self.top.bind("<Escape>", lambda e: self.top.destroy())

    def on_click(self, event):
        self.result = [event.x_root, event.y_root] # Use root coordinates for screen accuracy
        self.top.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = SCGMAutoBR(root)
    root.mainloop()
