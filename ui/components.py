import tkinter as tk
from PIL import ImageTk

class CoordinatePicker:
    """A tool to pick a single x, y coordinate from the screen."""
    def __init__(self, parent, screenshot, on_complete):
        self.parent = parent
        self.screenshot = screenshot
        self.on_complete = on_complete
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
        self.result = [event.x_root, event.y_root]
        self.on_complete(self.result)
        self.top.destroy()
