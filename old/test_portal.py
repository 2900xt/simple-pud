#!/usr/bin/env python3
"""
Test XDG Desktop Portal for screen capture.
This is the proper way to do screen capture on Wayland.
"""

import dbus
import time

try:
    # Connect to session bus
    bus = dbus.SessionBus()

    # Get org.freedesktop.portal.Desktop
    portal = bus.get_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')

    # Get Screenshot interface
    screenshot_iface = dbus.Interface(portal, 'org.freedesktop.portal.Screenshot')

    # Request a screenshot (this will show a user permission dialog)
    print("Requesting screenshot permission from portal...")
    print("Note: This may show a dialog asking for permission")

    options = {
        'modal': dbus.Boolean(True),
        'interactive': dbus.Boolean(False)  # Don't show the screenshot UI
    }

    # parent_window = '' means no parent
    result = screenshot_iface.Screenshot('', options)
    print(f"Result: {result}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
