import os
import pyautogui
from PIL import Image, ImageTk
import tkinter as tk
from core.controller import human_click

def is_image_visible(img_name, config, confidence=None):
    """Checks if an image is on screen without clicking it."""
    path = config["images"].get(img_name)
    if not path or not os.path.exists(path):
        return False
        
    conf = confidence if confidence is not None else config["confidence"]
    try:
        return pyautogui.locateOnScreen(path, confidence=conf, grayscale=True) is not None
    except Exception:
        return False

def find_and_click(img_name, config, is_running_check, log_func, clicks=1):
    if not is_running_check():
        return False
    
    path = config["images"][img_name]
    if not os.path.exists(path):
        return False
        
    try:
        pos = pyautogui.locateOnScreen(path, confidence=config["confidence"], grayscale=True)
        if pos:
            center = pyautogui.center(pos)
            log_func(f"Found {img_name}!")
            human_click(center.x, center.y, is_running_check)
            for _ in range(clicks - 1):
                human_click(center.x, center.y, is_running_check, move=False)
            return True
    except Exception:
        pass
    return False

class ScreenCaptureTool:
    def __init__(self, parent, screenshot, key, assets_dir, on_complete):
        self.parent = parent
        self.screenshot = screenshot
        self.key = key
        self.assets_dir = assets_dir
        self.on_complete = on_complete
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
        
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)
        
        if right - left < 5 or bottom - top < 5:
            return

        cropped = self.screenshot.crop((left, top, right, bottom))
        asset_name = f"{self.key}.png"
        save_path = os.path.join(self.assets_dir, asset_name)
        os.makedirs(self.assets_dir, exist_ok=True)
        cropped.save(save_path)
        
        self.result_path = save_path
        self.on_complete(self.result_path)
        self.top.destroy()
