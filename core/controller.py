import time
import random
import pydirectinput

def human_click(x, y, is_running_check, move=True, offset=0):
    """Moves mouse smoothly and clicks exactly at target x, y with a small pre-click wiggle."""
    if not is_running_check():
        return
    
    if move:
        # Move to EXACT position (no randomization)
        pydirectinput.moveTo(int(x), int(y), duration=random.uniform(0.3, 0.5))
        time.sleep(0.3)
        
        # Wiggle slightly to the left (as requested)
        pydirectinput.moveRel(-random.randint(3, 6), 0, relative=True)
        time.sleep(0.2)
        
        # Deliberate click and hold
        pydirectinput.mouseDown()
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.mouseUp()
    else:
        # Just click and hold at current position
        pydirectinput.mouseDown()
        time.sleep(random.uniform(0.1, 0.2))
        pydirectinput.mouseUp()
    
    time.sleep(0.3)
