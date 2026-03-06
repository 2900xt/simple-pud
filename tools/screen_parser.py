#!/usr/bin/env python3
"""
Poker Screen Parser - Screenshots the game and parses board state via Claude Vision.

Usage:
    ANTHROPIC_API_KEY=sk-... python3 tools/screen_parser.py [--region] [--key KEY]

Modes:
    Default:   Press Enter in terminal to capture
    --region:  Use slurp to select a screen region (first capture only, reused after)
    --key KEY: Global hotkey via evdev (e.g. --key PAUSE, --key F12). Needs input group.

Requires: grim, ANTHROPIC_API_KEY env var
Optional: slurp (for --region), evdev (for --key)
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time

import requests

from advisor import analyze, print_analysis

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"
SCREENSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "screenshots")

PARSE_PROMPT = """Analyze this poker game screenshot. Extract the board state as JSON with these fields:

{
  "community_cards": ["Ah", "Kd", "5c"],   // cards on the board, empty if preflop
  "hero_hand": ["As", "Ks"],               // hero's hole cards if visible
  "pot": 150,                                // pot size if visible, null otherwise
  "stage": "flop",                           // preflop/flop/turn/river
  "players": [                               // visible player info
    {"position": "BTN", "stack": 200, "bet": 0, "folded": false}
  ],
  "current_bet": 10,                         // current bet to call, null if unknown
  "notes": "any other relevant observations"
}

Use standard 2-char card notation: rank (23456789TJQKA) + suit (h/d/s/c).
If something is not visible or unclear, use null. Only return the JSON object, nothing else."""


def get_api_key():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        print("Export it:  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)
    return key


def take_screenshot(region=None):
    """Capture screen using grim. Returns path to PNG."""
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(SCREENSHOT_DIR, f"capture_{timestamp}.png")

    cmd = ["grim"]
    if region:
        cmd += ["-g", region]
    cmd.append(path)

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"grim failed: {result.stderr.strip()}")
        return None
    return path


def select_region():
    """Use slurp to let user select a screen region. Returns geometry string."""
    print("Select the poker game region with your mouse...")
    result = subprocess.run(["slurp"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"slurp cancelled or failed: {result.stderr.strip()}")
        return None
    return result.stdout.strip()


def parse_screenshot(image_path, api_key):
    """Send screenshot to Claude Vision API and parse the poker board state."""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": MODEL,
        "max_tokens": 1024,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {"type": "text", "text": PARSE_PROMPT},
                ],
            }
        ],
    }

    print("Sending to Claude Vision API...")
    resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)

    if resp.status_code != 200:
        print(f"API error ({resp.status_code}): {resp.text[:300]}")
        return None

    data = resp.json()
    text = data["content"][0]["text"]

    # Extract JSON from response (strip markdown fences if present)
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print(f"Failed to parse JSON from API response:\n{text}")
        return None


def print_board_state(state):
    """Pretty-print the parsed board state."""
    if not state:
        print("  (no state parsed)")
        return

    stage = state.get("stage", "unknown")
    community = state.get("community_cards", [])
    hero = state.get("hero_hand", [])
    pot = state.get("pot")
    current_bet = state.get("current_bet")

    print(f"  Stage:     {stage}")
    print(f"  Board:     {' '.join(community) if community else '(none)'}")
    print(f"  Hero:      {' '.join(hero) if hero else '(not visible)'}")
    if pot is not None:
        print(f"  Pot:       {pot}")
    if current_bet is not None:
        print(f"  To call:   {current_bet}")

    players = state.get("players", [])
    if players:
        print(f"  Players:")
        for p in players:
            pos = p.get("position", "?")
            stack = p.get("stack", "?")
            bet = p.get("bet", 0)
            folded = p.get("folded", False)
            status = "folded" if folded else f"bet {bet}"
            print(f"    {pos}: stack={stack}, {status}")

    notes = state.get("notes")
    if notes:
        print(f"  Notes:     {notes}")


def run_terminal_mode(api_key, use_region):
    """Capture on Enter keypress in terminal."""
    region = None
    if use_region:
        region = select_region()
        if not region:
            print("No region selected, capturing full screen.")

    print("\nPoker Screen Parser ready.")
    print("Press Enter to capture, 'q' + Enter to quit.\n")

    while True:
        try:
            line = input("> ")
        except (EOFError, KeyboardInterrupt):
            break
        if line.strip().lower() == "q":
            break

        path = take_screenshot(region)
        if not path:
            continue
        print(f"Screenshot: {path}")

        state = parse_screenshot(path, api_key)
        print_board_state(state)

        # Run advisor
        if state and state.get("hero_hand"):
            analysis = analyze(state)
            if analysis:
                print_analysis(analysis)

        # Also dump raw JSON
        if state:
            json_path = path.replace(".png", ".json")
            with open(json_path, "w") as f:
                json.dump(state, f, indent=2)
            print(f"  Saved:     {json_path}")
        print()


def run_evdev_mode(api_key, key_name, use_region):
    """Capture on global hotkey via evdev."""
    try:
        import evdev
        from evdev import ecodes
    except ImportError:
        print("evdev not available. Install with: pip install evdev")
        sys.exit(1)

    key_code = getattr(ecodes, f"KEY_{key_name.upper()}", None)
    if key_code is None:
        print(f"Unknown key: {key_name}")
        print("Examples: F12, PAUSE, SCROLLLOCK, F9")
        sys.exit(1)

    # Find keyboard devices
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    keyboards = [d for d in devices if ecodes.EV_KEY in d.capabilities()]

    if not keyboards:
        print("No keyboard devices found. You may need to be in the 'input' group:")
        print("  sudo usermod -aG input $USER")
        sys.exit(1)

    region = None
    if use_region:
        region = select_region()
        if not region:
            print("No region selected, capturing full screen.")

    print(f"\nPoker Screen Parser ready. Press {key_name.upper()} to capture.")
    print("Press Ctrl+C to quit.\n")

    try:
        import select as sel

        while True:
            r, _, _ = sel.select(keyboards, [], [], 1.0)
            for dev in r:
                for event in dev.read():
                    if event.type == ecodes.EV_KEY and event.value == 1:  # key down
                        if event.code == key_code:
                            print(f"[{time.strftime('%H:%M:%S')}] Capturing...")
                            path = take_screenshot(region)
                            if not path:
                                continue
                            print(f"Screenshot: {path}")

                            state = parse_screenshot(path, api_key)
                            print_board_state(state)

                            if state and state.get("hero_hand"):
                                analysis = analyze(state)
                                if analysis:
                                    print_analysis(analysis)

                            if state:
                                json_path = path.replace(".png", ".json")
                                with open(json_path, "w") as f:
                                    json.dump(state, f, indent=2)
                                print(f"  Saved:     {json_path}")
                            print()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        for d in keyboards:
            d.close()


def main():
    parser = argparse.ArgumentParser(description="Poker screen parser using Claude Vision")
    parser.add_argument("--region", action="store_true",
                        help="Use slurp to select a screen region")
    parser.add_argument("--key", type=str, default=None,
                        help="Global hotkey via evdev (e.g. F12, PAUSE)")
    args = parser.parse_args()

    api_key = get_api_key()

    if args.key:
        run_evdev_mode(api_key, args.key, args.region)
    else:
        run_terminal_mode(api_key, args.region)


if __name__ == "__main__":
    main()
