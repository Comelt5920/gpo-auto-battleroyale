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

class AreaPicker:
    """A tool to pick a rectangular area (x1, y1, x2, y2) from the screen."""
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
        
        self.start_x = None
        self.start_y = None
        self.rect = None
        
        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", lambda e: self.top.destroy())
        
        self.canvas.create_text(20, 20, text="Drag to select the Capture Area. Press ESC to cancel.", 
                                anchor=tk.NW, fill="red", font=("Arial", 16, "bold"))

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

        self.result = (left, top, right, bottom)
        self.on_complete(self.result)
        self.top.destroy()
