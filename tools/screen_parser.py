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


def ocr_text(img, psm=7, extra_config=""):
    """Run OCR on a cropped image region."""
    if pytesseract is None:
        return ""
    try:
        config = f"--psm {psm} {extra_config}".strip()
        return pytesseract.image_to_string(img, config=config).strip()
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


def suit_from_rgb(r, g, b):
    """Determine suit from an RGB color sample.

    Suit colors: spades=black, hearts=red, diamonds=blue, clubs=green.
    """
    brightness = (r + g + b) / 3

    if brightness < 10:
        return "s"  # spades (black/dark)

    if r > g * 1.3 and r > b * 1.3:
        return "h"  # hearts (red)
    elif g > r * 1.2 and g > b:
        return "c"  # clubs (green)
    elif b > r * 1.2 and b > g:
        return "d"  # diamonds (blue)
    else:
        return "s"  # spades (dark/neutral)


def detect_suit_at_pixel(img, pixel_xy):
    """Detect suit by sampling a single pixel at absolute [x, y] coordinates."""
    rgb = img.convert("RGB")
    x, y = pixel_xy
    r, g, b = rgb.getpixel((x, y))
    return suit_from_rgb(r, g, b)


def card_present(card_img):
    """Check if a card is actually visible (not empty table felt)."""
    gray = card_img.convert("L")
    pixels = list(gray.getdata())
    if not pixels:
        return False
    avg = sum(pixels) / len(pixels)
    variance = sum((p - avg) ** 2 for p in pixels) / len(pixels)
    return avg > 50 and variance > 200


def detect_card(card_img, debug=False, rank_crop_mode="top_left", suit_pixel=None, full_img=None):
    """Detect rank and suit of a single card image. Returns e.g. 'Ah' or None.

    rank_crop_mode: "top_left" for full cards (board), "left_half" for partial cards (hero).
    suit_pixel: optional [x, y] absolute coords to sample suit color from full_img.
    If debug=True, returns (result, debug_info) tuple instead.
    """
    info = {}

    if not card_present(card_img):
        gray = card_img.convert("L")
        pixels = list(gray.getdata())
        avg = sum(pixels) / len(pixels) if pixels else 0
        var = sum((p - avg) ** 2 for p in pixels) / len(pixels) if pixels else 0
        info["fail"] = f"no_card(avg={avg:.0f},var={var:.0f})"
        if debug:
            return None, info
        return None

    # Rank: OCR a crop of the card
    w, h = card_img.size
    if rank_crop_mode == "left_half":
        rank_crop = card_img.crop((0, 0, max(1, int(w * 0.4)), max(1, int(h * 0.6))))
    else:
        rank_crop = card_img.crop((0, 0, max(1, int(w * 0.4)), max(1, int(h * 0.4))))
    rank_gray = rank_crop.convert("L")
    ocr_whitelist = "-c tessedit_char_whitelist=23456789TJQKA10"
    rank = None
    rank_text = ""

    for thresh in (140, 110, 170):
        rank_bw = rank_gray.point(lambda x, t=thresh: 0 if x < t else 255, "1")
        candidate = ocr_text(rank_bw, psm=10, extra_config=ocr_whitelist).upper().strip()
        # Clean common OCR errors
        candidate = candidate.replace("O", "0").replace("I", "1").replace("L", "1").replace("C", "K").replace("@", "Q").replace("B", "8")
        for key, val in RANK_MAP.items():
            if key in candidate:
                rank = val
                rank_text = candidate
                break
        if not rank and len(candidate) == 1 and candidate in "23456789TJQKA":
            rank = candidate
            rank_text = candidate
        if rank:
            break
        if not rank_text:
            rank_text = candidate

    info["ocr"] = repr(rank_text)

    if not rank:
        info["fail"] = f"no_rank(ocr={info['ocr']})"
        if debug:
            return None, info
        return None

    # Suit: sample a specific pixel if configured, otherwise skip
    if suit_pixel and full_img:
        x, y = suit_pixel
        r, g, b = full_img.convert("RGB").getpixel((x, y))
        info["suit_rgb"] = f"({r},{g},{b})"
        suit = suit_from_rgb(r, g, b)
    else:
        info["fail"] = f"no_suit_pixel"
        suit = None

    if not suit:
        if debug:
            return None, info
        return None

    result = rank + suit
    info["result"] = result
    if debug:
        return result, info
    return result


def detect_cards_in_region(img, region, num_slots, rank_crop_mode="top_left", suit_pixels=None):
    """Detect cards by splitting a region into equal-width slots.

    suit_pixels: optional list of [x, y] absolute coords, one per slot.
    """
    region_img = crop_region(img, region)
    cards = []
    slot_w = region_img.size[0] // num_slots
    for i in range(num_slots):
        card_img = region_img.crop((i * slot_w, 0, (i + 1) * slot_w, region_img.size[1]))
        sp = suit_pixels[i] if suit_pixels and i < len(suit_pixels) else None
        card = detect_card(card_img, rank_crop_mode=rank_crop_mode, suit_pixel=sp, full_img=img)
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


def _has_cards(cards_img):
    """Check if a villain's card region shows cards (not folded/empty).

    Folded players show empty felt or a dimmed/absent card area.
    Active players have visible card backs (distinct colored rectangles).
    """
    gray = cards_img.convert("L")
    pixels = list(gray.getdata())
    if not pixels:
        return False
    avg = sum(pixels) / len(pixels)
    variance = sum((p - avg) ** 2 for p in pixels) / len(pixels)
    # Card backs have moderate brightness and some contrast vs flat felt
    # Felt is usually uniform dark; card backs have edges/patterns
    return variance > 200 and avg > 50


def parse_game_state(screen_img, config):
    """Parse a screenshot into a game state dict.

    screen_img: PIL Image of the full screen.
    config: parsed pud_config.json (regions are absolute screen coordinates).

    Returns: game state dict.
    """
    table_img = screen_img
    state = {
        "community_cards": [],
        "hero_hand": [],
        "hero_position": "BTN",
        "pot": 0,
        "stage": "preflop",
        "players": [],
        "current_bet": 0,
        "big_blind": 1,
    }

    # Hero cards
    if config.get("hero_cards"):
        state["hero_hand"] = detect_cards_in_region(
            table_img, config["hero_cards"], 2,
            rank_crop_mode="left_half",
            suit_pixels=config.get("hero_suit_pixels"),
        )

    # Board cards
    if config.get("board"):
        state["community_cards"] = detect_cards_in_region(
            table_img, config["board"], 5,
            suit_pixels=config.get("board_suit_pixels"),
        )

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
        hero_position = "BTN"
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

        # Fold detection: check if villain's cards are visible
        if seat.get("cards"):
            cards_img = crop_region(table_img, seat["cards"])
            if not _has_cards(cards_img):
                player["folded"] = True

        if seat.get("stack"):
            stack_text = ocr_text(crop_region(table_img, seat["stack"]))
            stack_val = parse_number(stack_text)
            if stack_val is not None:
                player["stack"] = stack_val
            elif not seat.get("cards"):
                # No cards region configured, fall back to stack readability as fold signal
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
