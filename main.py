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
from PIL import Image, ImageTk

# Basic Config
CONFIG_FILE = "config.json"
ASSETS_DIR = "assets"

class SCGMAutoBot:
    def __init__(self, root):
        self.root = root
        self.root.title("SCGM-Auto-Br (Advanced)")
        self.root.geometry("600x650")
        self.root.attributes('-topmost', True)
        
        # States
        self.is_running = False
        self.match_count = 0
        self.start_time = None
        self.config = self.load_config()
        self.asset_previews = {} # Stores PhotoImage objects
        
        # Hotkey (Global)
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
            "movement_duration": 300,  # 5 minutes in seconds
            "images": {
                "queue": "queue.png",
                "br_mode": "br_mode.png",
                "solo_mode": "solo_mode.png",
                "match_found": "match_found.png",
                "open": "open.png",
                "continue": "continue.png"
            }
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return {**default_config, **json.load(f)}
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

        # Stats Frame
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

        # Controls
        btn_frame = ttk.Frame(self.main_tab)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.status_label = ttk.Label(btn_frame, text="Status: IDLE", font=('Segoe UI', 10, 'bold'))
        self.status_label.pack(pady=5)

        self.btn_toggle = ttk.Button(btn_frame, text="START BOT", command=self.toggle_bot)
        self.btn_toggle.pack(fill=tk.X)

        # Console
        ttk.Label(self.main_tab, text="Activity Log:").pack(anchor=tk.W)
        self.console = scrolledtext.ScrolledText(self.main_tab, height=15, state='disabled', font=('Consolas', 9))
        self.console.pack(fill=tk.BOTH, expand=True, pady=5)

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
            
            # Right: Preview
            preview_label = ttk.Label(frame)
            preview_label.pack(side=tk.RIGHT)
            self.update_preview(key, preview_label)

    def start_capture_helper(self, key, label_widget):
        """Starts the capture countdown and overlay tool."""
        self.root.iconify() # Minimize main window
        self.log(f"Capture starting in 5 seconds for {key}...")
        
        def run_capture():
            time.sleep(5)
            screenshot = pyautogui.screenshot()
            
            # Show overlay tool
            cap_tool = ScreenCaptureTool(self.root, screenshot, key)
            self.root.wait_window(cap_tool.top) # Wait for it to finish
            
            if cap_tool.result_path:
                self.config["images"][key] = cap_tool.result_path
                label_widget.config(text=f"File: {os.path.basename(cap_tool.result_path)}")
                self.save_config()
                self.log(f"Captured and saved {key} asset.")
                
                # Update preview
                preview_label = label_widget.master.master.winfo_children()[-1] 
                self.update_preview(key, preview_label)
            
            self.root.deiconify() # Bring main window back

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

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console.configure(state='normal')
        self.console.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.console.see(tk.END)
        self.console.configure(state='disabled')

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
        
        # Randomize target slightly
        target_x = int(x + random.randint(-5, 5))
        target_y = int(y + random.randint(-5, 5))
        
        # pydirectinput move
        pydirectinput.moveTo(target_x, target_y, duration=random.uniform(0.3, 0.6))
        
        # Hover Wiggle
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.moveRel(random.randint(-2, 2), random.randint(-2, 2), relative=True)
        
        # Short pause before clicking
        time.sleep(random.uniform(0.1, 0.3))
        
        # Click and Hold
        pydirectinput.mouseDown()
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.mouseUp()

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
                self.log(f"Found {img_name}! Performing human click.")
                self.human_click(center.x, center.y)
                return True
        except Exception as e:
            pass
        return False

    def random_move(self):
        """Random WASD movement until the match ends."""
        self.log("Starting dynamic movement phase (WASD)...")
        keys = ['w', 'a', 's', 'd']
        
        while self.is_running:
            # Check for end-match buttons every few moves
            if self.is_image_visible("open") or self.is_image_visible("continue"):
                self.log("End-match screen detected! Stopping movement.")
                break
                
            # Perform a few random key taps
            for _ in range(random.randint(2, 5)):
                if not self.is_running: break
                key = random.choice(keys)
                duration = random.uniform(0.1, 0.4)
                pydirectinput.keyDown(key)
                time.sleep(duration)
                pydirectinput.keyUp(key)
                time.sleep(random.uniform(0.2, 0.8))
        
        self.log("Movement phase complete.")

    def is_image_visible(self, img_name):
        """Checks if an image is on screen without clicking it."""
        path = self.config["images"].get(img_name)
        if not path or not os.path.exists(path): return False
        try:
            return pyautogui.locateOnScreen(path, confidence=self.config["confidence"], grayscale=True) is not None
        except:
            return False

    def bot_loop(self):
        os.makedirs(ASSETS_DIR, exist_ok=True)
        
        while self.is_running:
            try:
                # 1. State: Lobby / Start Sequence
                self.status_label.config(text="Status: LOBBY / QUEUEING", foreground="blue")
                
                self.find_and_click("queue")
                self.find_and_click("br_mode")
                
                if self.find_and_click("solo_mode"):
                    self.log("Solo clicked. Entering 'Wait for Match' state...")
                    
                    # 2. State: Waiting for Match Found
                    match_started = False
                    self.status_label.config(text="Status: WAITING FOR MATCH", foreground="orange")
                    
                    start_wait = time.time()
                    while time.time() - start_wait < 300 and self.is_running:
                        if self.find_and_click("match_found"):
                            match_started = True
                            break
                        time.sleep(2)
                    
                    if match_started:
                        self.match_count += 1
                        self.lbl_match.config(text=f"Matches: {self.match_count}")
                        self.log(f"Match #{self.match_count} STARTED!")
                        self.send_discord(f"🚀 Match #{self.match_count} Found! Time: {datetime.now().strftime('%H:%M:%S')}")
                        
                        # 3. State: In Game / Movement
                        self.status_label.config(text="Status: IN GAME (MOVING)", foreground="green")
                        self.random_move()
                        
                        # 4. State: Post-Match / Waiting for Results
                        self.log("Match phase over. Looking for 'Open' or 'Continue'...")
                        self.status_label.config(text="Status: MATCH ENDED", foreground="purple")
                        
                        results_found = False
                        while not results_found and self.is_running:
                            if self.find_and_click("open"):
                                self.log("'Open' detected.")
                                time.sleep(2)
                            
                            if self.find_and_click("continue"):
                                self.log("'Continue' detected. Returning to Lobby.")
                                results_found = True
                                break
                            time.sleep(5)
                
                time.sleep(self.config["scan_interval"])
                
            except Exception as e:
                self.log(f"Loop Info: {e}")
                time.sleep(5)

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

if __name__ == "__main__":
    root = tk.Tk()
    app = SCGMAutoBot(root)
    root.mainloop()
