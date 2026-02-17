import time
import random
import pydirectinput

def human_click(x, y, is_running_check, move=True):
    """Moves mouse smoothly and clicks. If move=False, just clicks at current pos."""
    if not is_running_check():
        return
    
    if move:
        # Randomize target slightly within a reasonable button area
        target_x = int(x + random.randint(-8, 8))
        target_y = int(y + random.randint(-8, 8))
        
        pydirectinput.moveTo(target_x, target_y, duration=random.uniform(0.3, 0.5))
        time.sleep(0.2) # Pause for game to register position
        # Hover Wiggle - Only to the left
        pydirectinput.moveRel(random.randint(-4, -1), 0, relative=True)
        time.sleep(0.3) # Stabilization before click
    
    # Click and Hold (More deliberate)
    pydirectinput.mouseDown()
    time.sleep(random.uniform(0.15, 0.25))
    pydirectinput.mouseUp()
    time.sleep(0.5) # Wait for UI response
