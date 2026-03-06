"""
Screen parser for PUD - extracts poker game state from screenshots.
Uses OCR (pytesseract) for text + color analysis for card suits. No LLM needed.

All region coordinates in config are relative to the cropped table image.
Region format: [x, y, w, h]
"""

import json
import os
import re

from PIL import Image

try:
    import pytesseract
except ImportError:
    pytesseract = None

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pud_config.json")

RANK_MAP = {
    "10": "T",
    "2": "2", "3": "3", "4": "4", "5": "5", "6": "6",
    "7": "7", "8": "8", "9": "9",
    "T": "T", "J": "J", "Q": "Q", "K": "K", "A": "A",
}

POSITIONS_9 = ["BTN", "SB", "BB", "UTG", "UTG1", "UTG2", "LJ", "HJ", "CO"]
POSITIONS_6 = ["BTN", "SB", "BB", "UTG", "HJ", "CO"]


def load_config():
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH) as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def crop_region(img, region):
    """Crop image to [x, y, w, h] region."""
    x, y, w, h = region
    return img.crop((x, y, x + w, y + h))


def ocr_text(img, psm=7):
    """Run OCR on a cropped image region."""
    if pytesseract is None:
        return ""
    try:
        return pytesseract.image_to_string(img, config=f"--psm {psm}").strip()
    except Exception:
        return ""


def parse_number(text):
    """Extract a float from OCR text like '2.4 BB', '$150', '16.8'."""
    text = text.replace(",", ".")
    cleaned = re.sub(r"[^\d.]", "", text)
    match = re.search(r"\d+\.?\d*", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def detect_suit(card_img):
    """Detect card suit by color analysis.

    PokerStars suit colors: spades=black, hearts=red, diamonds=blue, clubs=green.
    """
    img_rgb = card_img.convert("RGB")
    pixels = list(img_rgb.getdata())
    if not pixels:
        return None

    colored = []
    dark_count = 0
    for r, g, b in pixels:
        brightness = (r + g + b) / 3
        if brightness < 60:
            dark_count += 1
        elif 40 < brightness < 210:
            colored.append((r, g, b))

    if not colored:
        if dark_count > len(pixels) * 0.15:
            return "s"
        return None

    avg_r = sum(p[0] for p in colored) / len(colored)
    avg_g = sum(p[1] for p in colored) / len(colored)
    avg_b = sum(p[2] for p in colored) / len(colored)

    if avg_r > avg_g * 1.3 and avg_r > avg_b * 1.3 and avg_r > 100:
        return "h"  # hearts (red)
    elif avg_g > avg_r * 1.2 and avg_g > avg_b and avg_g > 70:
        return "c"  # clubs (green)
    elif avg_b > avg_r * 1.2 and avg_b > avg_g and avg_b > 90:
        return "d"  # diamonds (blue)
    else:
        return "s"  # spades (dark/neutral)


def card_present(card_img):
    """Check if a card is actually visible (not empty table felt)."""
    gray = card_img.convert("L")
    pixels = list(gray.getdata())
    if not pixels:
        return False
    avg = sum(pixels) / len(pixels)
    variance = sum((p - avg) ** 2 for p in pixels) / len(pixels)
    return avg > 80 and variance > 500


def detect_card(card_img):
    """Detect rank and suit of a single card image. Returns e.g. 'Ah' or None."""
    if not card_present(card_img):
        return None

    w, h = card_img.size

    # Rank: OCR the top-left corner
    rank_crop = card_img.crop((0, 0, max(1, int(w * 0.55)), max(1, int(h * 0.40))))
    rank_bw = rank_crop.convert("L").point(lambda x: 0 if x < 140 else 255, "1")
    rank_text = ocr_text(rank_bw, psm=10).upper().strip()

    # Clean common OCR errors
    rank_text = rank_text.replace("O", "0").replace("I", "1").replace("L", "1")
    rank = None
    for key, val in RANK_MAP.items():
        if key in rank_text:
            rank = val
            break
    if not rank and len(rank_text) == 1 and rank_text in "23456789TJQKA":
        rank = rank_text

    if not rank:
        return None

    # Suit: color analysis on the suit symbol area
    suit_crop = card_img.crop((0, max(1, int(h * 0.30)), max(1, int(w * 0.65)), max(2, int(h * 0.75))))
    suit = detect_suit(suit_crop)

    if not suit:
        return None

    return rank + suit


def detect_cards_in_region(img, region, num_slots):
    """Detect cards by splitting a region into equal-width slots."""
    region_img = crop_region(img, region)
    cards = []
    slot_w = region_img.size[0] // num_slots
    for i in range(num_slots):
        card_img = region_img.crop((i * slot_w, 0, (i + 1) * slot_w, region_img.size[1]))
        card = detect_card(card_img)
        if card:
            cards.append(card)
    return cards


def _button_score(btn_img):
    """Score how likely a region contains the dealer button (bright white/yellow circle)."""
    pixels = list(btn_img.convert("RGB").getdata())
    if not pixels:
        return 0.0
    bright = sum(
        1 for r, g, b in pixels
        if r > 180 and g > 160 and b > 80 and (r + g + b) / 3 > 170
    )
    return bright / len(pixels)


def find_button_seat(table_img, config):
    """Find which seat has the dealer button. Returns seat index, 'hero', or None."""
    best_idx = None
    best_score = 0.0

    for i, seat in enumerate(config.get("seats", [])):
        if not seat.get("button"):
            continue
        score = _button_score(crop_region(table_img, seat["button"]))
        if score > best_score:
            best_score = score
            best_idx = i

    if config.get("hero_button"):
        score = _button_score(crop_region(table_img, config["hero_button"]))
        if score > best_score:
            best_score = score
            best_idx = "hero"

    return best_idx if best_score > 0.08 else None


def assign_positions(n_seats, button_idx):
    """Assign poker position names clockwise from the button.

    Returns list of position names indexed by seat.
    """
    pos_list = POSITIONS_9[:n_seats] if n_seats > 6 else POSITIONS_6[:n_seats]
    positions = [None] * n_seats
    for i, pos in enumerate(pos_list):
        seat = (button_idx + i) % n_seats
        positions[seat] = pos
    return positions


def parse_game_state(table_img, config):
    """Parse a cropped table screenshot into a game state dict.

    table_img: PIL Image already cropped to the table region.
    config: parsed pud_config.json (regions are relative to table).

    Returns: game state dict compatible with advisor.analyze().
    """
    state = {
        "community_cards": [],
        "hero_hand": [],
        "hero_position": config.get("hero_position", "BTN"),
        "pot": 0,
        "stage": "preflop",
        "players": [],
        "current_bet": 0,
        "big_blind": config.get("big_blind", 1),
    }

    # Hero cards
    if config.get("hero_cards"):
        state["hero_hand"] = detect_cards_in_region(table_img, config["hero_cards"], 2)

    # Board cards
    if config.get("board"):
        state["community_cards"] = detect_cards_in_region(table_img, config["board"], 5)

    n_community = len(state["community_cards"])
    state["stage"] = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}.get(n_community, "postflop")

    # Pot
    if config.get("pot"):
        pot_text = ocr_text(crop_region(table_img, config["pot"]))
        pot_val = parse_number(pot_text)
        if pot_val is not None:
            state["pot"] = pot_val

    # Hero stack
    hero_stack = 0
    if config.get("hero_stack"):
        stack_text = ocr_text(crop_region(table_img, config["hero_stack"]))
        stack_val = parse_number(stack_text)
        if stack_val is not None:
            hero_stack = stack_val

    # Hero bet
    hero_bet = 0
    if config.get("hero_bet"):
        bet_text = ocr_text(crop_region(table_img, config["hero_bet"]))
        bet_val = parse_number(bet_text)
        if bet_val is not None:
            hero_bet = bet_val

    # Seat ordering: opponents are seats 0..n-1, hero is seat n
    seats = config.get("seats", [])
    n_total = 1 + len(seats)
    hero_seat_idx = len(seats)

    # Button detection -> position assignment
    button_raw = find_button_seat(table_img, config)
    if button_raw == "hero":
        button_seat_idx = hero_seat_idx
    elif button_raw is not None:
        button_seat_idx = button_raw
    else:
        button_seat_idx = None

    if button_seat_idx is not None:
        pos_names = assign_positions(n_total, button_seat_idx)
        hero_position = pos_names[hero_seat_idx]
    else:
        hero_position = config.get("hero_position", "BTN")
        pos_names = None

    state["hero_position"] = hero_position

    # Opponent seats
    max_bet = hero_bet
    for i, seat in enumerate(seats):
        if pos_names:
            pos = pos_names[i]
        else:
            pos = seat.get("position", f"S{i+1}")

        player = {"position": pos, "folded": False, "bet": 0, "stack": 0}

        if seat.get("stack"):
            stack_text = ocr_text(crop_region(table_img, seat["stack"]))
            stack_val = parse_number(stack_text)
            if stack_val is not None:
                player["stack"] = stack_val
            else:
                player["folded"] = True

        if seat.get("bet"):
            bet_text = ocr_text(crop_region(table_img, seat["bet"]))
            bet_val = parse_number(bet_text)
            if bet_val is not None:
                player["bet"] = bet_val
                max_bet = max(max_bet, bet_val)

        state["players"].append(player)

    # Hero player entry
    state["players"].append({
        "position": hero_position,
        "stack": hero_stack,
        "bet": hero_bet,
        "folded": False,
    })

    state["current_bet"] = max_bet
    return state
