import time
import random
import traceback
import pydirectinput
import pyautogui
from core.vision import is_image_visible, find_and_click
from core.controller import human_click
from utils.discord import send_discord

class BotEngine:
    def __init__(self, app):
        self.app = app # Reference to the main UI app for config and logging
        self.last_leave_click_time = 0
        self.last_punch_time = 0
        self.match_start_time = 0
        self.last_lobby_log_time = 0 # New: Track last log to prevent spam

    def is_running(self):
        return self.app.is_running

    def log(self, msg, is_error=False):
        self.app.log(msg, is_error)

    def bot_loop(self):
        while self.is_running():
            try:
                self.app.update_status("CHECK / STARTING", "blue")
                
                # Phase 1: New Check - If see Return button in Lobby state, handle it.
                if is_image_visible("return_to_lobby_alone", self.app.config, confidence=0.7):
                    if time.time() - self.last_lobby_log_time > 60: # Log only once every 60s
                        self.log("Return to lobby detected during Lobby phase.")
                        if self.app.config.get("match_mode") == "quick":
                            self.log("Quick Leave: Exiting match...")
                        else:
                            self.log("Found Return button, but mode is FULL. Wait for the end of the match...")
                        self.last_lobby_log_time = time.time()
                    
                    if self.app.config.get("match_mode") == "quick":
                        find_and_click("return_to_lobby_alone", self.app.config, self.is_running, self.log, clicks=2)
                    elif time.time() - self.last_leave_click_time > 60:
                        # Full Match AFK Prevention: Move to button but click at current pos to be safe
                        # or just click at current pos after a small move
                        pydirectinput.moveRel(1, 1, relative=True) # Small jitter
                        time.sleep(0.1)
                        pydirectinput.mouseDown()
                        time.sleep(0.1)
                        pydirectinput.mouseUp()
                        self.last_leave_click_time = time.time()
                
                # Phase 1: Ultimate Check - Jump to Setup Stats if found
                if is_image_visible("ultimate", self.app.config):
                    self.log("Ultimate bar detected during Lobby/Check phase! Jumping to Auto-Punch...")
                    self.app.match_count += 1
                    self.app.update_match_count()
                    self.app.update_status("AUTO-PUNCHING", "green")
                    self.match_start_time = time.time() # Start timing
                    self.auto_punch()
                    self.handle_post_match()
                    continue

                if is_image_visible("open", self.app.config) or is_image_visible("continue", self.app.config):
                    self.log("End-match screen detected! Jumping to results...")
                    self.handle_post_match()
                    continue

                if is_image_visible("solo_mode", self.app.config):
                    if find_and_click("solo_mode", self.app.config, self.is_running, self.log):
                        self.log("Solo clicked. Entering match sequence...")
                        self.handle_match_waiting()
                        continue
                elif is_image_visible("br_mode", self.app.config):
                    find_and_click("br_mode", self.app.config, self.is_running, self.log)
                else:
                    find_and_click("change", self.app.config, self.is_running, self.log)
                
                time.sleep(self.app.config["scan_interval"])
                
            except Exception as e:
                self.log(f"Loop Error: {e}", is_error=True)
                # traceback logic can stay in UI or here
                time.sleep(5)

    def handle_match_waiting(self):
        self.log("Waiting for Ultimate bar...")
        match_started = False
        ultimate_triggered = False
        self.app.update_status("WAITING FOR MATCH", "orange")
        
        start_wait = time.time()
        self.match_start_time = time.time()
        last_log_time = time.time()
        
        # Phase 2: Timeout reduced to 8 minutes (480s)
        while time.time() - start_wait < 480 and self.is_running():
            if time.time() - last_log_time > 30:
                elapsed = int(time.time() - start_wait)
                self.log(f"Still waiting for Ultimate... to trigger auto-punch ({elapsed}s elapsed)")
                last_log_time = time.time()

            if is_image_visible("return_to_lobby_alone", self.app.config, confidence=0.7):
                self.log("Game loaded: 'Return to lobby' detected.")
                match_started = True
                break
            
            if is_image_visible("ultimate", self.app.config):
                self.log("Game loaded: 'Ultimate' button detected!")
                match_started = True
                ultimate_triggered = True
                break
            
            if is_image_visible("change", self.app.config):
                self.log("Lobby detected (Queue cancelled). Retrying sequence.")
                return

            time.sleep(0.5)
        
        if match_started:
            self.app.match_count += 1
            self.app.update_match_count()
            self.log(f"Match #{self.app.match_count} STARTED!")
            
            if ultimate_triggered:
                self.app.update_status("AUTO-PUNCHING", "green")
                self.auto_punch()
            else:
                self.app.update_status("IN GAME (MOVING)", "green")
                self.random_move()
            
            self.handle_post_match()

    def random_move(self):
        mode = self.app.config.get("match_mode", "full")
        self.log(f"Starting phase: {mode.upper()} MODE")
        
        keys_cfg = self.app.config.get("keys", {})
        keys = [
            keys_cfg.get("forward", "w"),
            keys_cfg.get("left", "a"),
            keys_cfg.get("backward", "s"),
            keys_cfg.get("right", "d")
        ]
        start_game_time = time.time()
        
        while self.is_running():
            key = random.choice(keys)
            duration = random.uniform(0.2, 0.6)
            pydirectinput.keyDown(key)
            time.sleep(duration)
            pydirectinput.keyUp(key)

            if is_image_visible("open", self.app.config) or is_image_visible("continue", self.app.config):
                self.log("End-match screen detected! Stopping phase.")
                break
            
            is_leave_v = is_image_visible("return_to_lobby_alone", self.app.config, confidence=0.7)
            if is_leave_v and (time.time() - self.last_leave_click_time > 60):
                if self.app.config.get("match_mode") == "quick":
                    if find_and_click("return_to_lobby_alone", self.app.config, self.is_running, self.log, clicks=2):
                        self.log("Quick Leave: Exit button clicked (2x).")
                        self.last_leave_click_time = time.time()
                else: 
                    # AFK Prevention: Click with hold
                    pydirectinput.mouseDown()
                    time.sleep(0.1)
                    pydirectinput.mouseUp()
                    self.last_leave_click_time = time.time()
            
            if random.random() < 0.2:
                pydirectinput.moveRel(random.randint(-120, 120), 0, relative=True)
            
            if time.time() - start_game_time > 1080:
                self.log("Max match time reached (18m). Force checking for end buttons.")
                break
            
            time.sleep(random.uniform(0.5, 1.2))
        
        self.log("Match phase complete.")

    def auto_punch(self):
        try:
            # Phase 3: Wait 5 seconds before starting Setup Stats
            self.log("AUTO-PUNCH TRIGGERED! Waiting 5s before setup...")
            time.sleep(5.0)
            
            self.log("Setting up stats...")
            keys_cfg = self.app.config.get("keys", {})
            menu_key = keys_cfg.get("menu", "m")
            slot1_key = keys_cfg.get("slot_1", "1")

            pydirectinput.press(menu_key)
            time.sleep(1.0)
            
            pos1 = self.app.config.get("pos_1", [0, 0])
            human_click(pos1[0], pos1[1], self.is_running)
            time.sleep(1.5)
            
            pos2 = self.app.config.get("pos_2", [0, 0])
            for i in range(11):
                if not self.is_running(): break
                human_click(pos2[0], pos2[1], self.is_running, move=(i==0))
                if i > 0: time.sleep(0.2)
            
            pydirectinput.press(menu_key)
            time.sleep(1.0)
            pydirectinput.press(slot1_key)
            time.sleep(1.0)
            
            self.log("Auto-punching mode ACTIVE. Punching (0.5s interval)...")
            punch_start_time = time.time()
            while self.is_running():
                is_leave_v = is_image_visible("return_to_lobby_alone", self.app.config, confidence=0.7)
                
                # Phase 3: Punch interval changed to 0.5s (was 0.05s)
                punch_interval = 60 if is_leave_v else 0.5
                if time.time() - self.last_punch_time > punch_interval:
                    pydirectinput.click()
                    if is_leave_v:
                        time.sleep(0.2)
                        pydirectinput.click()
                    self.last_punch_time = time.time()
                
                if time.time() - punch_start_time > 120:
                    if random.random() < 0.2:
                        move_keys = [keys_cfg.get("forward", "w"), keys_cfg.get("left", "a"), 
                                     keys_cfg.get("backward", "s"), keys_cfg.get("right", "d")]
                        key = random.choice(move_keys)
                        pydirectinput.keyDown(key)
                        time.sleep(0.2)
                        pydirectinput.keyUp(key)
                
                if is_image_visible("open", self.app.config) or is_image_visible("continue", self.app.config):
                    self.log("Match end detected via results screen.")
                    break
                
                if is_leave_v and (time.time() - self.last_leave_click_time > 60):
                    if self.app.config.get("match_mode") == "quick":
                        if find_and_click("return_to_lobby_alone", self.app.config, self.is_running, self.log, clicks=2):
                            self.last_leave_click_time = time.time()
                    else:
                        # Full Mode AFK Prevention: Click current pos
                        pydirectinput.mouseDown()
                        time.sleep(0.1)
                        pydirectinput.mouseUp()
                        self.last_leave_click_time = time.time()
                
                time.sleep(0.05)
        except Exception as e:
            self.log(f"Auto-punch Error: {e}", is_error=True)

    def handle_post_match(self):
        self.log("Post-match phase. Looking for 'Open' or 'Continue'...")
        self.app.update_status("MATCH ENDED", "purple")
        
        notification_sent = False
        start_wait = time.time()
        last_progress_time = time.time() # 2-minute failsafe timer
        
        if self.match_start_time == 0:
            self.match_start_time = time.time() - 60

        while self.is_running():
            # Absolute timeout: 5 minutes max in post-match
            if time.time() - start_wait > 300:
                self.log("Results screen timeout. Returning to lobby.")
                break
            
            # Failsafe: If no progress (no buttons found) for 2 minutes (120s)
            if time.time() - last_progress_time > 120:
                self.log("Failsafe: No buttons detected for 2 minutes. Returning to Phase 1.")
                break

            # 1. Image Checks
            is_open_v = is_image_visible("open", self.app.config)
            is_continue_v = is_image_visible("continue", self.app.config)
            is_leave_v = is_image_visible("return_to_lobby_alone", self.app.config, confidence=0.7)

            if is_open_v or is_continue_v or is_leave_v:
                # We see a button, so we are not "stuck" in a black screen/unknown state
                last_progress_time = time.time() 

            # 2. Capture and Send Notification
            if (is_continue_v or is_leave_v) and not notification_sent:
                self.log("Continue screen detected! Sending Discord results...")
                screenshot_path = "match_finish.png"
                try:
                    full_screenshot = pyautogui.screenshot()
                    area = self.app.config.get("outcome_area")
                    if area:
                        cropped_img = full_screenshot.crop(area)
                        cropped_img.save(screenshot_path)
                    else:
                        full_screenshot.save(screenshot_path)
                except Exception as e:
                    self.log(f"Screenshot Error: {e}")
                    screenshot_path = None

                elapsed = int(time.time() - self.match_start_time)
                if elapsed > 3600 or elapsed < 0: elapsed = 0 
                
                time_str = f"{elapsed // 60} min {elapsed % 60} sec"
                msg = f"Queue #{self.app.match_count} Finish time: {time_str}"
                
                send_discord(self.app.config.get("discord_webhook"), msg, file_path=screenshot_path)
                self.log(f"Discord results sent. Time: {time_str}")
                notification_sent = True
                time.sleep(1)

            # 3. Handle Clicking
            if is_open_v:
                # If we see Open, click it and RESET the failsafe timer
                if find_and_click("open", self.app.config, self.is_running, self.log, clicks=2):
                    last_found_any_time = time.time()
                time.sleep(2)
            
            if is_continue_v:
                if find_and_click("continue", self.app.config, self.is_running, self.log, clicks=2):
                    self.log("Continue clicked. Exiting post-match.")
                    time.sleep(4)
                    break
            
            if is_leave_v:
                # Stronger Return to Lobby attempt
                self.log("Attempting to click 'Return to Lobby'...")
                if find_and_click("return_to_lobby_alone", self.app.config, self.is_running, self.log, clicks=3):
                    self.log("Return to Lobby clicked multiple times. Exiting.")
                    time.sleep(4)
                    break
            
            time.sleep(2)
