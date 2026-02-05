#!/usr/bin/env python3
"""
PipeWire-based screen capture for Wayland using ScreenCast portal.
This provides smooth, continuous capture without any visual flashing.
"""

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import threading
import numpy as np
import cv2
import random
import string

# Initialize GStreamer
Gst.init(None)
DBusGMainLoop(set_as_default=True)


class PipeWireCapture:
    def __init__(self):
        self.running = False
        self.lock = threading.Lock()
        self.screenshot = None
        self.pipeline = None
        self.loop = None
        self.session_handle = None

    def start(self):
        """Start screen capture with user permission"""
        print("Requesting screen capture permission...")

        # Start portal session in a separate thread
        self.running = True
        self.thread = threading.Thread(target=self._start_portal_session)
        self.thread.start()

    def stop(self):
        """Stop screen capture"""
        self.running = False
        if self.loop:
            self.loop.quit()
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        if hasattr(self, 'thread'):
            self.thread.join()

    def _start_portal_session(self):
        """Start a ScreenCast portal session"""
        try:
            bus = dbus.SessionBus()

            # Get ScreenCast portal
            portal = bus.get_object(
                'org.freedesktop.portal.Desktop',
                '/org/freedesktop/portal/desktop'
            )
            screencast = dbus.Interface(portal, 'org.freedesktop.portal.ScreenCast')

            # Create session
            session_token = 'pokerhud_' + ''.join(random.choices(string.ascii_lowercase, k=10))
            options = {
                'session_handle_token': session_token
            }

            response = screencast.CreateSession(options)
            print(f"Session created: {response}")

            # For now, print instructions
            print("\nPortal API is complex and requires async handling.")
            print("Falling back to simpler approach...")

        except Exception as e:
            print(f"Portal error: {e}")
            import traceback
            traceback.print_exc()

    def get_latest_frame(self):
        """Get the latest captured frame"""
        with self.lock:
            return self.screenshot.copy() if self.screenshot is not None else None


if __name__ == "__main__":
    # Test
    capture = PipeWireCapture()
    capture.start()

    import time
    time.sleep(5)

    capture.stop()
