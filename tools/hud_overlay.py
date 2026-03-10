#!/usr/bin/env python3
"""
Poker HUD overlay for Wayland (Hyprland) using gtk-layer-shell.

Captures screenshots with grim, parses game state, runs equity analysis,
and renders a transparent overlay with stats on top of the poker table.

Requires this Hyprland config line to prevent grim from capturing the overlay:
    layerrule = noanim, poker-hud

Usage:
    python3 tools/hud_overlay.py [--interval 1500]
"""

import argparse
import math
import os
import subprocess
import sys
import tempfile
import threading

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GtkLayerShell, GLib, Gdk, Pango, PangoCairo
import cairo

# Add tools dir to path so we can import siblings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screen_parser import parse_game_state, load_config
from advisor import analyze

# Colors (r, g, b, a)
COLOR_BG = (0.0, 0.0, 0.0, 0.55)
COLOR_TEXT = (1.0, 1.0, 1.0, 1.0)
COLOR_FOLD = (0.5, 0.5, 0.5, 0.7)
COLOR_HERO = (0.3, 0.9, 1.0, 1.0)
COLOR_EQUITY = (1.0, 0.85, 0.0, 1.0)
COLOR_POT = (1.0, 1.0, 1.0, 0.9)

REC_COLORS = {
    "FOLD": (1.0, 0.3, 0.3, 1.0),
    "CALL": (1.0, 0.9, 0.2, 1.0),
    "RAISE": (0.2, 1.0, 0.4, 1.0),
    "BET": (0.2, 1.0, 0.4, 1.0),
    "CHECK": (0.4, 0.7, 1.0, 1.0),
}


def take_screenshot():
    """Capture screen with grim, return path to temp PNG."""
    fd, path = tempfile.mkstemp(suffix=".png", prefix="pud_hud_")
    os.close(fd)
    try:
        subprocess.run(["grim", path], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return path
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


class PokerHUD(Gtk.Window):
    def __init__(self, config, interval_ms=1500):
        super().__init__()
        self.config = config
        self.interval_ms = interval_ms
        self.game_state = None
        self.analysis = None

        # Layer shell setup
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "poker-hud")
        GtkLayerShell.set_exclusive_zone(self, -1)

        # Anchor to all edges = fullscreen overlay
        for edge in (GtkLayerShell.Edge.TOP, GtkLayerShell.Edge.BOTTOM,
                     GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self, edge, True)

        # No keyboard input
        GtkLayerShell.set_keyboard_mode(
            self, GtkLayerShell.KeyboardMode.NONE)

        # Transparent background
        self.set_app_paintable(True)
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)

        # Drawing area
        self.draw_area = Gtk.DrawingArea()
        self.draw_area.connect("draw", self.on_draw)
        self.add(self.draw_area)

        # Click passthrough via empty input region
        self.connect("realize", self.on_realize)
        self.connect("size-allocate", self.on_size_allocate)

        self.show_all()

        # Start polling
        GLib.timeout_add(self.interval_ms, self.poll)

    def _apply_input_passthrough(self):
        gdk_window = self.get_window()
        if gdk_window:
            empty = cairo.Region()
            gdk_window.input_shape_combine_region(empty, 0, 0)

    def on_realize(self, widget):
        self._apply_input_passthrough()

    def on_size_allocate(self, widget, allocation):
        self._apply_input_passthrough()

    def poll(self):
        """Kick off screenshot+parse in a background thread."""
        thread = threading.Thread(target=self._capture_and_parse, daemon=True)
        thread.start()
        return True

    def _capture_and_parse(self):
        """Run grim + OCR in background, then schedule redraw on main thread."""
        path = take_screenshot()
        if not path:
            print("grim failed - no screenshot", file=sys.stderr)
            return

        try:
            from PIL import Image
            img = Image.open(path)
            print(f"Screenshot: {img.size}", file=sys.stderr)
            state = parse_game_state(img, self.config)
            print(f"Parsed: hero={state.get('hero_hand')} "
                  f"board={state.get('community_cards')} "
                  f"pot={state.get('pot')} "
                  f"players={len(state.get('players', []))}",
                  file=sys.stderr)

            analysis = None
            if (state.get("hero_hand")
                    and len(state["hero_hand"]) >= 2):
                analysis = analyze(state)

            # Update state and trigger redraw on GTK main thread
            GLib.idle_add(self._apply_state, state, analysis)
        except Exception as e:
            import traceback
            traceback.print_exc()
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    def _apply_state(self, state, analysis):
        """Called on GTK main thread to update state and redraw."""
        self.game_state = state
        self.analysis = analysis
        self.draw_area.queue_draw()
        return False  # don't repeat

    def on_draw(self, widget, cr):
        # Clear to fully transparent
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        alloc = self.draw_area.get_allocation()
        pad = 10
        spacing = 4
        bx = 12

        lines = []  # list of (text, r, g, b, a, size, bold)

        state = self.game_state
        if state is None:
            lines.append(("HUD: waiting...", 0.7, 0.7, 0.7, 1, 11, False))
        else:
            # Line 1: game state summary
            hero = " ".join(state.get("hero_hand", [])) or "?"
            board = " ".join(state.get("community_cards", [])) or "-"
            pot = state.get("pot", 0)
            stage = state.get("stage", "?")
            pos = state.get("hero_position", "?")
            players = state.get("players", [])
            active = sum(1 for p in players if not p.get("folded"))
            lines.append((
                f"{pos}  {hero}  |  {board}  |  pot:{pot}  {stage}  {active}p",
                1, 1, 1, 0.9, 11, False
            ))

            # Lines 2+: advisor output
            a = self.analysis
            if a:
                d = a.get("decision", {})
                eq = d.get("hero_equity", 0)
                rec = d.get("recommendation", "?")
                rc = REC_COLORS.get(rec, COLOR_TEXT)

                # Equity line
                lines.append((
                    f"Equity: {eq:.1f}%  vs  {a.get('villain_range', '?')}",
                    *COLOR_EQUITY, 10, False
                ))

                # Recommendation line
                rec_text = rec
                if rec in ("BET", "RAISE"):
                    size = d.get("bet_size") or d.get("raise_size")
                    label = d.get("bet_label", "")
                    if size:
                        rec_text += f" {size}"
                    if label:
                        rec_text += f" ({label})"
                elif rec == "CALL":
                    call_amt = d.get("call_amount", 0)
                    if call_amt:
                        rec_text += f" {call_amt}"

                ev_call = d.get("ev_call")
                ev_bet = d.get("bet_ev")
                ev_raise = d.get("ev_raise")
                ev_str = ""
                if rec == "CALL" and ev_call is not None:
                    ev_str = f"  EV={ev_call:+.1f}"
                elif rec in ("BET",) and ev_bet is not None:
                    ev_str = f"  EV={ev_bet:+.1f}"
                elif rec == "RAISE" and ev_raise is not None:
                    ev_str = f"  EV={ev_raise:+.1f}"

                lines.append((f">>> {rec_text}{ev_str}", *rc, 14, True))

                # Reason line
                reason = d.get("reason", "")
                if reason:
                    lines.append((reason, 0.7, 0.7, 0.7, 0.8, 9, False))

        # Measure all lines to compute box size
        layouts = []
        total_h = 0
        max_w = 0
        for text, r, g, b, a, size, bold in lines:
            layout = self._make_layout(cr, text, size=size, bold=bold)
            _, log = layout.get_pixel_extents()
            layouts.append((layout, log, r, g, b, a))
            total_h += log.height + spacing
            max_w = max(max_w, log.width)
        total_h -= spacing  # no trailing spacing

        box_w = max_w + pad * 2
        box_h = total_h + pad * 2
        by = alloc.height - box_h - 12

        # Background
        cr.set_source_rgba(0, 0, 0, 0.75)
        self._rounded_rect(cr, bx, by, box_w, box_h, 6)
        cr.fill()

        # Render lines
        cy = by + pad
        for layout, log, r, g, b, a in layouts:
            cr.set_source_rgba(r, g, b, a)
            cr.move_to(bx + pad, cy)
            PangoCairo.show_layout(cr, layout)
            cy += log.height + spacing

        return False

    def _make_layout(self, cr, text, size=12, bold=False):
        layout = PangoCairo.create_layout(cr)
        layout.set_text(text, -1)
        weight = "bold" if bold else "normal"
        font = Pango.FontDescription(f"monospace {weight} {size}")
        layout.set_font_description(font)
        return layout

    def _rounded_rect(self, cr, x, y, w, h, r):
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()


def setup_hyprland_rules():
    """Add layerrule to exclude poker-hud from screenshots."""
    try:
        # Check if rule already exists
        result = subprocess.run(
            ["hyprctl", "layers", "-j"],
            capture_output=True, text=True)
        # Add rules: noanim prevents flicker, and we need the
        # screenshot exclusion
        rules = [
            "layerrule noanim, poker-hud",
            "layerrule noshadow, poker-hud",
        ]
        for rule in rules:
            subprocess.run(
                ["hyprctl", "keyword", rule],
                capture_output=True, text=True)
        print("Hyprland layerrules applied")
    except FileNotFoundError:
        print("Warning: hyprctl not found, can't set layerrules",
              file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Poker HUD overlay for Wayland")
    parser.add_argument("--interval", type=int, default=1500,
                        help="Poll interval in ms (default: 1500)")
    args = parser.parse_args()

    config = load_config()
    if not config:
        print("Error: pud_config.json not found. Run calibration first.",
              file=sys.stderr)
        sys.exit(1)

    setup_hyprland_rules()

    print(f"Starting HUD overlay (poll every {args.interval}ms)")
    print("Press Ctrl+C to stop")

    hud = PokerHUD(config, interval_ms=args.interval)
    try:
        Gtk.main()
    except KeyboardInterrupt:
        print("\nHUD stopped.")


if __name__ == "__main__":
    main()
