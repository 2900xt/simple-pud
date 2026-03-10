"""
Debug overlay - draws config rectangles on a table screenshot.

Takes a screenshot, draws all configured regions as labeled rectangles,
and opens the result in the default image viewer.
"""

import json
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pud_config.json")

# Colors for different region types
COLORS = {
    "table":       "#FF0000",
    "hero_cards":  "#00FF00",
    "board":       "#00AAFF",
    "pot":         "#FFFF00",
    "hero_stack":  "#FF8800",
    "hero_bet":    "#FF00FF",
    "hero_button": "#00FFAA",
}

SEAT_COLORS = [
    "#FF4444", "#44FF44", "#4444FF", "#FFAA00",
    "#AA00FF", "#00FFFF", "#FF66AA", "#AAFF00",
]

SEAT_PROPS = ["stack", "bet", "button", "cards"]


def draw_overlay(table_img, config):
    """Draw all config rectangles + detected card boundaries on the table image."""
    from screen_parser import crop_region, detect_card

    img = table_img.copy().convert("RGB")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf", 14)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except (OSError, IOError):
            font = ImageFont.load_default()

    def draw_rect(region, label, color, line_width=2):
        if not region:
            return
        x, y, w, h = region
        draw.rectangle([x, y, x + w, y + h], outline=color, width=line_width)
        # Label background
        bbox = font.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        lx, ly = x, max(0, y - th - 4)
        draw.rectangle([lx, ly, lx + tw + 6, ly + th + 4], fill=color)
        draw.text((lx + 3, ly + 1), label, fill="#000000", font=font)

    def draw_detected_cards(region, num_slots, label_prefix, color, rank_crop_mode="top_left", suit_pixels=None):
        """Split region into equal slots and draw each with detected card value + debug."""
        if not region:
            return
        region_img = crop_region(table_img, region)
        rx, ry, rw, rh = region
        slot_w = region_img.size[0] // num_slots
        for i in range(num_slots):
            card_img = region_img.crop((i * slot_w, 0, (i + 1) * slot_w, region_img.size[1]))
            sp = suit_pixels[i] if suit_pixels and i < len(suit_pixels) else None
            card, info = detect_card(card_img, debug=True, rank_crop_mode=rank_crop_mode, suit_pixel=sp, full_img=table_img)
            rgb_info = info.get("suit_rgb", "")
            if card:
                label = f"{label_prefix}[{i}]: {card} {rgb_info}"
            else:
                label = f"{label_prefix}[{i}]: {info.get('fail', '?')} {rgb_info}"
            card_region = [rx + i * slot_w, ry, slot_w, rh]
            draw_rect(card_region, label, color, line_width=3)

            # Draw OCR crop area as a yellow rect
            cw, ch = slot_w, rh
            if rank_crop_mode == "left_half":
                ocr_w, ocr_h = int(cw * 0.4), int(ch * 0.6)
            else:
                ocr_w, ocr_h = int(cw * 0.4), int(ch * 0.4)
            ox = rx + i * slot_w
            oy = ry
            draw.rectangle([ox, oy, ox + ocr_w, oy + ocr_h], outline="#FFFF00", width=1)

            # Draw suit pixel as a crosshair
            if sp:
                sx, sy = sp
                draw.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], outline="#FF0000", width=2)

    # Draw hero/global regions
    for key, color in COLORS.items():
        if key == "table":
            continue
        region = config.get(key)
        if region:
            draw_rect(region, key, color)

    # Draw detected cards for board and hero
    draw_detected_cards(config.get("board"), 5, "board", "#FF00FF",
                        suit_pixels=config.get("board_suit_pixels"))
    draw_detected_cards(config.get("hero_cards"), 2, "hero", "#00FF00",
                        rank_crop_mode="left_half",
                        suit_pixels=config.get("hero_suit_pixels"))

    # Draw seat regions
    for i, seat in enumerate(config.get("seats", [])):
        color = SEAT_COLORS[i % len(SEAT_COLORS)]
        for prop in SEAT_PROPS:
            region = seat.get(prop)
            if region:
                draw_rect(region, f"seat{i+1}.{prop}", color)

    return img


def debug_screenshot(config, screenshot_path):
    """Take a table screenshot, overlay config rects, and open it."""
    table_img = Image.open(screenshot_path)
    overlay = draw_overlay(table_img, config)

    fd, out_path = tempfile.mkstemp(suffix="_debug.png", prefix="pud_")
    os.close(fd)
    overlay.save(out_path)

    # Open with default viewer
    try:
        subprocess.Popen(["xdg-open", out_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print(f"  Debug overlay saved to: {out_path}")

    return out_path
