#!/usr/bin/env python3
"""
Test script to verify screen capture is working.
Captures a few frames and saves them as images for inspection.
"""

import time
import cv2
from capture import WindowCapture

def main():
    print("Testing screen capture...")

    # First, let's check what monitors are available
    import mss
    with mss.mss() as sct:
        print("\nAvailable monitors:")
        for i, monitor in enumerate(sct.monitors):
            print(f"  Monitor {i}: {monitor}")

    print("\nStarting capture service...")

    capture = WindowCapture()
    capture.start()

    # Wait a moment for the capture thread to grab first frame
    time.sleep(1)

    # Capture 5 frames over 5 seconds
    for i in range(5):
        frame = capture.get_latest_frame()
        if frame is not None:
            filename = f"test_frame_{i}.png"
            cv2.imwrite(filename, frame)
            print(f"✓ Saved {filename} (shape: {frame.shape})")
        else:
            print(f"✗ Frame {i} is None")

        time.sleep(1)

    capture.stop()
    print("\nCapture test complete. Check test_frame_*.png files.")

if __name__ == "__main__":
    main()
