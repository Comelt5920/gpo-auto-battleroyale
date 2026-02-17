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
                        # Full Match AFK Prevention: Click 2 times every 60s at current pos
                        pydirectinput.click()
                        time.sleep(0.2)
                        pydirectinput.click()
                        self.last_leave_click_time = time.time()

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
                self.log(f"Still waiting for match... ({elapsed}s elapsed)")
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
        
        keys = ['w', 'a', 's', 'd']
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
                    pydirectinput.click()
                    time.sleep(0.2)
                    pydirectinput.click()
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
            pydirectinput.press('m')
            time.sleep(1.0)
            
            pos1 = self.app.config.get("pos_1", [0, 0])
            human_click(pos1[0], pos1[1], self.is_running)
            time.sleep(1.5)
            
            pos2 = self.app.config.get("pos_2", [0, 0])
            for i in range(11):
                if not self.is_running(): break
                human_click(pos2[0], pos2[1], self.is_running, move=(i==0))
                if i > 0: time.sleep(0.2)
            
            pydirectinput.press('m')
            time.sleep(1.0)
            pydirectinput.press('1')
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
                        key = random.choice(['w', 'a', 's', 'd'])
                        pydirectinput.keyDown(key)
                        time.sleep(0.2)
                        pydirectinput.keyUp(key)
                
                if is_image_visible("open", self.app.config) or is_image_visible("continue", self.app.config):
                    self.log("Match end detected via results screen.")
                    break
                
                if is_leave_v and (time.time() - self.last_leave_click_time > 60):
                    if self.app.config.get("match_mode") == "quick":
                        if find_and_click("return_to_lobby_alone", self.app.config, self.is_running, self.log):
                            self.last_leave_click_time = time.time()
                    else:
                        self.last_leave_click_time = time.time()
                
                time.sleep(0.05)
        except Exception as e:
            self.log(f"Auto-punch Error: {e}", is_error=True)

    def handle_post_match(self):
        self.log("Post-match phase. Looking for 'Open' or 'Continue'...")
        self.app.update_status("MATCH ENDED", "purple")
        
        results_found = False
        start_wait = time.time()
        while not results_found and self.is_running():
            if time.time() - start_wait > 300:
                self.log("Results screen timeout. Returning to lobby.")
                break

            if find_and_click("open", self.app.config, self.is_running, self.log):
                # Phase 4: Capture Match Outcome Screenshot
                screenshot_path = "match_finish.png"
                try:
                    pyautogui.screenshot(screenshot_path)
                except:
                    screenshot_path = None

                elapsed = int(time.time() - self.match_start_time)
                time_str = f"{elapsed // 60} min {elapsed % 60} sec"
                self.log(f"'Open' clicked. Time: {time_str}")
                
                msg = f"Queue #{self.app.match_count} Finish time: {time_str}"
                send_discord(self.app.config.get("discord_webhook"), msg, file_path=screenshot_path)
                time.sleep(3)
            
            if find_and_click("continue", self.app.config, self.is_running, self.log) or \
               find_and_click("return_to_lobby_alone", self.app.config, self.is_running, self.log):
                self.log("Exit button clicked. Returning to Lobby.")
                results_found = True
                time.sleep(5)
                break
            
            time.sleep(4)
