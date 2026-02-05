import mss
import numpy as np
import cv2
import json
import time
import threading

class WindowCapture:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.running = False
        self.lock = threading.Lock()
        self.screenshot = None
        self.load_config()
        self.sct = mss.mss()

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                self.window_rect = config.get('window', {'top': 0, 'left': 0, 'width': 1920, 'height': 1080})
        except Exception as e:
            print(f"Error loading config: {e}")
            self.window_rect = {'top': 0, 'left': 0, 'width': 1920, 'height': 1080}

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.capture_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()

    def capture_loop(self):
        while self.running:
            start_time = time.time()
            
            # Use mss to grab the screen region
            # mss requires the dict keys to be 'top', 'left', 'width', 'height'
            with self.lock:
                img = self.sct.grab(self.window_rect)
                # Convert to numpy array (BGRA)
                self.screenshot = np.array(img)
                # Convert to BGR for OpenCV
                self.screenshot = cv2.cvtColor(self.screenshot, cv2.COLOR_BGRA2BGR)

            # Limit framerate to ~2 FPS to save resources (Poker is slow)
            elapsed = time.time() - start_time
            sleep_time = max(0, 0.5 - elapsed)
            time.sleep(sleep_time)

    def get_latest_frame(self):
        with self.lock:
            return self.screenshot.copy() if self.screenshot is not None else None
