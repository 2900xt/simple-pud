#!/usr/bin/env python3
"""
Test GNOME Shell screenshot via D-Bus.
"""

import dbus
import time

try:
    # Connect to session bus
    bus = dbus.SessionBus()

    # Get GNOME Shell screenshot interface
    shell = bus.get_object('org.gnome.Shell.Screenshot', '/org/gnome/Shell/Screenshot')
    iface = dbus.Interface(shell, 'org.gnome.Shell.Screenshot')

    # Take a screenshot
    filename = f'/tmp/test_screenshot_{int(time.time())}.png'
    success, filename_result = iface.Screenshot(False, False, filename)

    if success:
        print(f"✓ Screenshot saved to: {filename_result}")
    else:
        print("✗ Screenshot failed")

except Exception as e:
    print(f"✗ Error: {e}")
    print("\nTrying to list available D-Bus services:")
    try:
        obj = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        dbus_iface = dbus.Interface(obj, 'org.freedesktop.DBus')
        services = dbus_iface.ListNames()
        screenshot_services = [s for s in services if 'screenshot' in s.lower() or 'shell' in s.lower()]
        print("Screenshot/Shell related services:")
        for service in screenshot_services:
            print(f"  - {service}")
    except Exception as e2:
        print(f"Could not list services: {e2}")
