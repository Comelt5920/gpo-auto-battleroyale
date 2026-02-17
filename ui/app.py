import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import threading
import time
import os
import random
import traceback
from datetime import datetime
from PIL import Image, ImageTk
import pyautogui
import keyboard

from utils.config import load_config, save_config, ASSETS_DIR, LOG_FILE
from ui.components import CoordinatePicker, AreaPicker
from core.bot_engine import BotEngine
from core.vision import ScreenCaptureTool

class SCGMAutoBR:
    def __init__(self, root):
        self.root = root
        self.root.title("SCGM-Auto-Br (Advanced)")
        self.root.geometry("600x650")
        self.root.attributes('-topmost', True)
        
        self.is_running = False
        self.match_count = 0
        self.start_time = None
        self.config = load_config()
        self.asset_previews = {}
        
        self.engine = BotEngine(self)
        
        keyboard.add_hotkey('f1', self.toggle_bot_hotkey)
        
        self.setup_ui()
        self.log("Bot Initialized. Press F1 to Start/Stop!")

    def toggle_bot_hotkey(self):
        self.root.after(0, self.toggle_bot)

    def setup_ui(self):
        style = ttk.Style()
        style.configure("TButton", padding=6, font=('Segoe UI', 10))
        style.configure("Header.TLabel", font=('Segoe UI', 16, 'bold'))

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.main_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.main_tab, text=" Bot Control ")
        self.setup_main_tab()

        self.assets_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.assets_tab, text=" Asset Management ")
        self.setup_assets_tab()

        self.hotkeys_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.hotkeys_tab, text=" Hotkeys ")
        self.setup_hotkeys_tab()

    def setup_main_tab(self):
        ttk.Label(self.main_tab, text="SCGM-Auto-Br", style="Header.TLabel").pack(pady=10)

        stats_frame = ttk.LabelFrame(self.main_tab, text=" Match Stats ", padding="5")
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.lbl_match = ttk.Label(stats_frame, text="Matches: 0")
        self.lbl_match.pack(side=tk.LEFT, padx=10)
        
        self.lbl_timer = ttk.Label(stats_frame, text="Timer: 00:00:00")
        self.lbl_timer.pack(side=tk.RIGHT, padx=10)

        ttk.Label(self.main_tab, text="Discord Webhook:").pack(anchor=tk.W, pady=(10, 0))
        webhook_frame = ttk.Frame(self.main_tab)
        webhook_frame.pack(fill=tk.X, pady=5)
        self.ent_webhook = ttk.Entry(webhook_frame, show="*")
        self.ent_webhook.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ent_webhook.insert(0, self.config.get("discord_webhook", ""))
        self.btn_show_webhook = ttk.Button(webhook_frame, text="Show", width=6, command=self.toggle_webhook_visibility)
        self.btn_show_webhook.pack(side=tk.RIGHT, padx=(5, 0))
        
        self.btn_test_webhook = ttk.Button(webhook_frame, text="Test", width=6, command=self.test_webhook)
        self.btn_test_webhook.pack(side=tk.RIGHT, padx=(5, 0))

        conf_frame = ttk.LabelFrame(self.main_tab, text=" Detection Sensitivity ", padding="5")
        conf_frame.pack(fill=tk.X, pady=5)
        inner_conf = ttk.Frame(conf_frame)
        inner_conf.pack(fill=tk.X)
        ttk.Label(inner_conf, text="Value (0.1 - 1.0):").pack(side=tk.LEFT, padx=5)
        self.ent_conf = ttk.Entry(inner_conf, width=10)
        self.ent_conf.pack(side=tk.LEFT, padx=5)
        self.ent_conf.insert(0, str(self.config.get("confidence", 0.8)))
        ttk.Button(inner_conf, text="Set", width=8, command=self.on_conf_change).pack(side=tk.LEFT, padx=5)

        mode_frame = ttk.LabelFrame(self.main_tab, text=" Match Mode ", padding="5")
        mode_frame.pack(fill=tk.X, pady=10)
        self.mode_var = tk.StringVar(value=self.config.get("match_mode", "full"))
        ttk.Radiobutton(mode_frame, text="Full Match", variable=self.mode_var, value="full", command=self.on_mode_change).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Quick Leave", variable=self.mode_var, value="quick", command=self.on_mode_change).pack(side=tk.LEFT, padx=10)

        btn_frame = ttk.Frame(self.main_tab)
        btn_frame.pack(fill=tk.X, pady=10)
        self.status_label = ttk.Label(btn_frame, text="Status: IDLE", font=('Segoe UI', 10, 'bold'))
        self.status_label.pack(pady=5)
        self.btn_toggle = ttk.Button(btn_frame, text="START BOT", command=self.toggle_bot)
        self.btn_toggle.pack(fill=tk.X)

        self.console = scrolledtext.ScrolledText(self.main_tab, height=13, state='disabled', font=('Consolas', 9))
        self.console.pack(fill=tk.BOTH, expand=True, pady=5)

    def setup_assets_tab(self):
        canvas = tk.Canvas(self.assets_tab)
        scrollbar = ttk.Scrollbar(self.assets_tab, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for key in self.config["images"].keys():
            frame = ttk.LabelFrame(scroll_frame, text=f" {key.replace('_', ' ').title()} ", padding="5")
            frame.pack(fill=tk.X, pady=5, padx=5)
            
            info_frame = ttk.Frame(frame)
            info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            lbl_path = ttk.Label(info_frame, text=f"File: {self.config['images'][key]}", font=('Segoe UI', 8))
            lbl_path.pack(anchor=tk.W)
            
            ttk.Button(info_frame, text="Choose Image", width=15, command=lambda k=key, l=lbl_path: self.browse_asset(k, l)).pack(anchor=tk.W, pady=2)
            ttk.Button(info_frame, text="Capture Helper", width=15, command=lambda k=key, l=lbl_path: self.start_capture_helper(k, l)).pack(anchor=tk.W, pady=2)

            if key == "ultimate":
                ttk.Separator(info_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
                self.lbl_pos1 = ttk.Label(info_frame, text=f"Book: {self.config.get('pos_1')}", font=('Segoe UI', 8))
                self.lbl_pos1.pack(anchor=tk.W)
                ttk.Button(info_frame, text="Set Pos", width=8, command=lambda l=self.lbl_pos1: self.pick_coord("pos_1", l)).pack(anchor=tk.W)
                
                self.lbl_pos2 = ttk.Label(info_frame, text=f"Str+: {self.config.get('pos_2')}", font=('Segoe UI', 8))
                self.lbl_pos2.pack(anchor=tk.W)
                ttk.Button(info_frame, text="Set Pos", width=8, command=lambda l=self.lbl_pos2: self.pick_coord("pos_2", l)).pack(anchor=tk.W)
            
            preview_label = ttk.Label(frame)
            preview_label.pack(side=tk.RIGHT)
            self.update_preview(key, preview_label)

        # Outcome Capture Area Settings
        outcome_frame = ttk.LabelFrame(scroll_frame, text=" Discord Outcome Screenshot Area ", padding="5")
        outcome_frame.pack(fill=tk.X, pady=10, padx=5)
        
        self.lbl_area = ttk.Label(outcome_frame, text=f"Area: {self.config.get('outcome_area') or 'Full Screen'}", font=('Segoe UI', 8))
        self.lbl_area.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(outcome_frame, text="Set Capture Area", command=self.pick_area).pack(side=tk.RIGHT, padx=5)

        ttk.Button(scroll_frame, text="Open Debug Log File", command=self.open_log_file).pack(fill=tk.X, pady=10)

    def setup_hotkeys_tab(self):
        ttk.Label(self.hotkeys_tab, text="Keyboard Layout Remapping", style="Header.TLabel").pack(pady=10)
        
        container = ttk.Frame(self.hotkeys_tab)
        container.pack(fill=tk.BOTH, expand=True)

        self.key_entries = {}
        keys_to_map = [
            ("menu", "Menu Button (M)"),
            ("slot_1", "Slot 1 (1)"),
            ("forward", "Move Forward (W)"),
            ("backward", "Move Backward (S)"),
            ("left", "Move Left (A)"),
            ("right", "Move Right (D)")
        ]

        keys_cfg = self.config.get("keys", {})
        for key_id, label in keys_to_map:
            frame = ttk.Frame(container)
            frame.pack(fill=tk.X, pady=2)
            ttk.Label(frame, text=f"{label}:", width=25).pack(side=tk.LEFT)
            entry = ttk.Entry(frame, width=10)
            entry.pack(side=tk.LEFT, padx=5)
            entry.insert(0, keys_cfg.get(key_id, ""))
            self.key_entries[key_id] = entry

        ttk.Button(self.hotkeys_tab, text="Save Hotkeys", command=self.save_hotkeys).pack(pady=20)

    def save_hotkeys(self):
        new_keys = {}
        for key_id, entry in self.key_entries.items():
            val = entry.get().strip().lower()
            if val:
                new_keys[key_id] = val
        
        self.config["keys"] = new_keys
        save_config(self.config)
        self.log("Hotkeys updated and saved!")

    def log(self, msg, is_error=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.console.configure(state='normal')
        self.console.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.console.see(tk.END)
        self.console.configure(state='disabled')
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"[{full_ts}] {'[ERROR] ' if is_error else ''}{msg}\n")
        except: pass

    def update_status(self, text, color):
        self.status_label.config(text=f"Status: {text}", foreground=color)

    def update_match_count(self):
        self.lbl_match.config(text=f"Matches: {self.match_count}")

    def on_mode_change(self):
        self.config["match_mode"] = self.mode_var.get()
        save_config(self.config)
        self.log(f"Mode: {self.config['match_mode'].upper()}")

    def on_conf_change(self):
        try:
            val = float(self.ent_conf.get())
            if 0.1 <= val <= 1.0:
                self.config["confidence"] = val
                save_config(self.config)
                self.log(f"Confidence: {val:.2f}")
        except: pass

    def toggle_webhook_visibility(self):
        if self.ent_webhook.cget('show') == '*':
            self.ent_webhook.config(show='')
            self.btn_show_webhook.config(text="Hide")
        else:
            self.ent_webhook.config(show='*')
            self.btn_show_webhook.config(text="Show")

    def open_log_file(self):
        if os.path.exists(LOG_FILE): os.startfile(LOG_FILE)

    def browse_asset(self, key, label_widget):
        file_path = filedialog.askopenfilename(initialdir=ASSETS_DIR, filetypes=(("PNG", "*.png"), ("All", "*.*")))
        if file_path:
            rel = os.path.relpath(file_path, os.getcwd())
            self.config["images"][key] = rel
            label_widget.config(text=f"File: {os.path.basename(rel)}")
            save_config(self.config)
            self.update_preview(key, label_widget.master.master.winfo_children()[-1])

    def start_capture_helper(self, key, label_widget):
        self.root.iconify()
        self.log(f"Capturing {key} in 2.5s...")
        def run():
            time.sleep(2.5)
            screenshot = pyautogui.screenshot()
            def complete(path):
                self.config["images"][key] = path
                label_widget.config(text=f"File: {os.path.basename(path)}")
                save_config(self.config)
                self.update_preview(key, label_widget.master.master.winfo_children()[-1])
                self.root.deiconify()
            ScreenCaptureTool(self.root, screenshot, key, ASSETS_DIR, complete)
        threading.Thread(target=run, daemon=True).start()

    def pick_coord(self, key, label_widget):
        self.root.iconify()
        time.sleep(1)
        screenshot = pyautogui.screenshot()
        def complete(res):
            self.config[key] = res
            label_widget.config(text=f"{'Book' if key=='pos_1' else 'Str+'}: {res}")
            save_config(self.config)
            self.root.deiconify()
        CoordinatePicker(self.root, screenshot, complete)

    def pick_area(self):
        self.root.iconify()
        time.sleep(1)
        screenshot = pyautogui.screenshot()
        def complete(res):
            self.config["outcome_area"] = res
            status = f"Area: {res}"
            self.lbl_area.config(text=status)
            save_config(self.config)
            self.root.deiconify()
        AreaPicker(self.root, screenshot, complete)

    def update_preview(self, key, label_widget):
        path = self.config["images"][key]
        if not os.path.isabs(path): path = os.path.join(os.getcwd(), path)
        if os.path.exists(path):
            try:
                img = Image.open(path)
                img.thumbnail((60, 60))
                photo = ImageTk.PhotoImage(img)
                label_widget.config(image=photo)
                label_widget.image = photo
            except: label_widget.config(text="Error", image="")
        else: label_widget.config(text="Missing", image="")

    def toggle_bot(self):
        if not self.is_running:
            # 1. Sanitize Webhook (Clean spaces and check format)
            webhook = self.ent_webhook.get().strip()
            if webhook and not webhook.startswith("https://discord.com/api/webhooks/"):
                self.log("Invalid Webhook URL! Must start with discord.com/api/webhooks/", is_error=True)
                return
                
            self.config["discord_webhook"] = webhook
            save_config(self.config)
            
            # 2. Lock UI
            self.ent_webhook.config(state='disabled')
            self.ent_conf.config(state='disabled')
            
            self.is_running = True
            self.btn_toggle.config(text="STOP BOT")
            self.start_time = time.time()
            self.update_timer()
            self.log("Starting...")
            threading.Thread(target=self.engine.bot_loop, daemon=True).start()
        else:
            self.is_running = False
            self.btn_toggle.config(text="START BOT")
            
            # 3. Unlock UI
            self.ent_webhook.config(state='normal')
            self.ent_conf.config(state='normal')
            self.log("Stopping...")

    def test_webhook(self):
        webhook = self.ent_webhook.get().strip()
        if not webhook:
            self.log("Please enter a Webhook URL first.", is_error=True)
            return
        self.log("Sending test message to Discord...")
        from utils.discord import send_discord
        send_discord(webhook, "✅ [SCGM-Auto-Br] Webhook Test Successful!")

    def update_timer(self):
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            self.lbl_timer.config(text=f"Timer: {elapsed//3600:02}:{(elapsed%3600)//60:02}:{elapsed%60:02}")
            self.root.after(1000, self.update_timer)
