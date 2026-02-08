#!/usr/bin/env python3
"""
List available monitors/screens using mss.
"""

import mss

with mss.mss() as sct:
    print("Available monitors:")
    for i, monitor in enumerate(sct.monitors):
        print(f"  Monitor {i}: {monitor}")
