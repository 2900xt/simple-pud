import mss
import numpy as np
import cv2
import json
import time
import threading
import subprocess
import os
import tempfile

class WindowCapture:
    def __init__(self, config_path='config.json'):
        self.config_path = config_path
        self.running = False
        self.lock = threading.Lock()
        self.screenshot = None
        self.load_config()
        # Don't create mss instance here - it must be created in the capture thread

    def load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                # Support both monitor index and custom coordinates
                self.monitor_index = config.get('monitor', None)
                self.window_rect = config.get('window', None)
        except Exception as e:
            print(f"Error loading config: {e}")
            self.monitor_index = 1  # Default to monitor 1
            self.window_rect = None

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.capture_loop)
        self.thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()

    def capture_loop(self):
        # Try mss first (works on X11)
        use_mss = True
        try:
            with mss.mss() as sct:
                # Test if mss works
                test_grab = sct.grab(sct.monitors[0])
                print("Using mss for screen capture (X11)")
        except Exception as e:
            print(f"mss failed ({e}), falling back to flameshot (Wayland)")
            use_mss = False

        if use_mss:
            self._capture_loop_mss()
        else:
            self._capture_loop_flameshot()

    def _capture_loop_mss(self):
        """Capture loop using mss (X11)"""
        with mss.mss() as sct:
            # Determine capture region
            if self.monitor_index is not None:
                capture_region = sct.monitors[self.monitor_index]
                print(f"Capturing monitor {self.monitor_index}: {capture_region}")
            elif self.window_rect is not None:
                capture_region = self.window_rect
                print(f"Capturing custom region: {capture_region}")
            else:
                capture_region = sct.monitors[1]
                print(f"Capturing default monitor 1: {capture_region}")

            while self.running:
                start_time = time.time()

                with self.lock:
                    img = sct.grab(capture_region)
                    self.screenshot = np.array(img)
                    self.screenshot = cv2.cvtColor(self.screenshot, cv2.COLOR_BGRA2BGR)

                elapsed = time.time() - start_time
                sleep_time = max(0, 0.5 - elapsed)
                time.sleep(sleep_time)

    def _capture_loop_flameshot(self):
        """Capture loop using flameshot (Wayland fallback)"""
        print("Using flameshot for screen capture (headless mode)")

        while self.running:
            start_time = time.time()

            try:
                # Run flameshot in raw mode (no UI, outputs PNG to stdout)
                result = subprocess.run([
                    'flameshot', 'full',
                    '--raw'
                ], capture_output=True, timeout=2)

                if result.returncode == 0 and result.stdout:
                    # Decode PNG from stdout
                    nparr = np.frombuffer(result.stdout, np.uint8)
                    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                    if img is not None:
                        with self.lock:
                            self.screenshot = img

            except subprocess.TimeoutExpired:
                print("flameshot timeout")
            except Exception as e:
                print(f"flameshot error: {e}")

            # Limit framerate to ~2 FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, 0.5 - elapsed)
            time.sleep(sleep_time)

    def get_latest_frame(self):
        with self.lock:
            return self.screenshot.copy() if self.screenshot is not None else None
