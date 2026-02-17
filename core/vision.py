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
            
            # Calculate a safe offset (25% of the image size, max 8)
            safe_offset_x = min(8, max(1, pos.width // 4))
            safe_offset_y = min(8, max(1, pos.height // 4))
            safe_offset = min(safe_offset_x, safe_offset_y)
            
            human_click(center.x, center.y, is_running_check, offset=safe_offset)
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
        
        # Prepare Dimmed Background
        from PIL import ImageEnhance
        enhancer = ImageEnhance.Brightness(self.screenshot)
        self.dimmed_screenshot = enhancer.enhance(0.4) # Darken to 40%
        self.tk_dimmed = ImageTk.PhotoImage(self.dimmed_screenshot)
        
        self.canvas = tk.Canvas(self.top, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_dimmed)

        # Magnifier setup
        self.mag_size = 180
        self.mag_zoom = 4
        self.mag_canvas = tk.Canvas(self.top, width=self.mag_size, height=self.mag_size, 
                                     highlightthickness=2, highlightbackground="red")
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.spotlight_item = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.update_magnifier)
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        
        self.canvas.create_text(20, 20, text=f"Capturing: {key.upper()} | Drag to snip. ESC to cancel.", 
                                anchor=tk.NW, fill="white", font=("Segoe UI", 16, "bold"))

    def update_magnifier(self, event):
        x, y = event.x, event.y
        mag_x = x + 30 if x + self.mag_size + 60 < self.top.winfo_screenwidth() else x - self.mag_size - 30
        mag_y = y + 30 if y + self.mag_size + 60 < self.top.winfo_screenheight() else y - self.mag_size - 30
        self.mag_canvas.place(x=mag_x, y=mag_y)
        
        box_size = self.mag_size // self.mag_zoom
        left = max(0, x - box_size // 2)
        top = max(0, y - box_size // 2)
        right = min(self.screenshot.width, left + box_size)
        bottom = min(self.screenshot.height, top + box_size)
        
        part = self.screenshot.crop((left, top, right, bottom))
        part = part.resize((self.mag_size, self.mag_size), Image.Resampling.NEAREST)
        
        self.photo = ImageTk.PhotoImage(part)
        self.mag_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.mag_canvas.create_line(self.mag_size//2, 0, self.mag_size//2, self.mag_size, fill="red")
        self.mag_canvas.create_line(0, self.mag_size//2, self.mag_size, self.mag_size//2, fill="red")

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect: self.canvas.delete(self.rect)
        if self.spotlight_item: self.canvas.delete(self.spotlight_item)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, 
                                                 outline='red', width=1)

    def on_drag(self, event):
        x, y = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, x, y)
        
        # Spotlight effect: Draw the original bright image in the rectangle
        left = min(self.start_x, x)
        top = min(self.start_y, y)
        right = max(self.start_x, x)
        bottom = max(self.start_y, y)
        
        if right - left > 2 and bottom - top > 2:
            bright_part = self.screenshot.crop((left, top, right, bottom))
            self.bright_tk = ImageTk.PhotoImage(bright_part)
            if self.spotlight_item: self.canvas.delete(self.spotlight_item)
            self.spotlight_item = self.canvas.create_image(left, top, anchor=tk.NW, image=self.bright_tk)
            self.canvas.tag_raise(self.rect) # Keep red border on top

        self.update_magnifier(event)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)
        
        if right - left < 3 or bottom - top < 3:
            return

        cropped = self.screenshot.crop((left, top, right, bottom))
        asset_name = f"{self.key}.png"
        save_path = os.path.join(self.assets_dir, asset_name)
        os.makedirs(self.assets_dir, exist_ok=True)
        cropped.save(save_path)
        
        self.result_path = save_path
        self.on_complete(self.result_path)
        self.top.destroy()
