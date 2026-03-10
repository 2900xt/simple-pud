"""
GTO Preflop Strategy Tables for 9-max NLHE (100bb deep).

Provides solver-approximate preflop frequencies for:
- RFI (Raise First In) by position
- Facing RFI (3-bet / call / fold) by opener group and hero position
- Facing 3-bet (4-bet / call / fold) by original raiser position

Each hand maps to a frequency 0.0-1.0. Hands not listed are pure folds (0.0).
Mixed strategies (e.g. 0.5) mean play that action ~50% of the time.
"""

RANKS = "23456789TJQKA"
RANK_INDEX = {r: i for i, r in enumerate(RANKS)}


def hand_to_canonical(card1, card2):
    """Convert two specific cards to canonical form.
    'As','Kh' -> 'AKo'   'Ah','Kh' -> 'AKs'   'Kd','Ks' -> 'KK'
    """
    r1, r2 = RANK_INDEX[card1[0]], RANK_INDEX[card2[0]]
    s1, s2 = card1[1], card2[1]
    if r1 < r2:
        r1, r2 = r2, r1
        s1, s2 = s2, s1
    high = RANKS[r1]
    low = RANKS[r2]
    if r1 == r2:
        return f"{high}{low}"
    elif s1 == s2:
        return f"{high}{low}s"
    else:
        return f"{high}{low}o"


def _expand_single(hand_str):
    """Expand a single hand notation to a list of canonical hands.
    'AA' -> ['AA'], 'AKs' -> ['AKs'], 'AK' -> ['AKs','AKo']
    """
    s = hand_str.strip()
    if len(s) == 2:
        r1, r2 = s[0], s[1]
        if r1 == r2:
            return [s]  # pair
        return [f"{r1}{r2}s", f"{r1}{r2}o"]
    elif len(s) == 3 and s[2] in ('s', 'o'):
        return [s]
    return [s]


def _expand_range(range_str):
    """Expand range notation to list of canonical hands.
    Supports: 'AA', 'AKs', 'TT+', 'ATs+', 'AA-TT', 'AKs-ATs', 'AKo-ATo'
    """
    s = range_str.strip()

    # Plus notation: 'TT+', 'ATs+', 'ATo+'
    if s.endswith('+'):
        base = s[:-1]
        if len(base) == 2 and base[0] == base[1]:
            # Pair+: TT+ means TT,JJ,QQ,KK,AA
            ri = RANK_INDEX[base[0]]
            return [f"{RANKS[i]}{RANKS[i]}" for i in range(ri, 13)]
        elif len(base) == 3:
            high_i = RANK_INDEX[base[0]]
            low_i = RANK_INDEX[base[1]]
            suit = base[2]
            return [f"{RANKS[high_i]}{RANKS[i]}{suit}" for i in range(low_i, high_i)]
        return _expand_single(s[:-1])

    # Dash notation: 'AA-TT', 'AKs-ATs', 'AKo-ATo'
    if '-' in s:
        parts = s.split('-')
        if len(parts) == 2:
            start, end = parts[0].strip(), parts[1].strip()

            # Pair range: AA-TT
            if len(start) == 2 and start[0] == start[1] and len(end) == 2 and end[0] == end[1]:
                hi = RANK_INDEX[start[0]]
                lo = RANK_INDEX[end[0]]
                if hi < lo:
                    hi, lo = lo, hi
                return [f"{RANKS[i]}{RANKS[i]}" for i in range(lo, hi + 1)]

            # Suited/offsuit range: AKs-ATs or AKo-ATo
            if len(start) == 3 and len(end) == 3 and start[2] == end[2]:
                suit = start[2]
                high_rank = start[0]
                # The high card should be the same
                if high_rank != end[0]:
                    # Different high cards - just return both endpoints
                    return _expand_single(start) + _expand_single(end)
                lo_i = RANK_INDEX[end[1]]
                hi_i = RANK_INDEX[start[1]]
                if lo_i > hi_i:
                    lo_i, hi_i = hi_i, lo_i
                return [f"{high_rank}{RANKS[i]}{suit}" for i in range(lo_i, hi_i + 1)]

        return _expand_single(s)

    return _expand_single(s)


def _t(*specs):
    """Build a {hand: frequency} table from (range_notation, freq) pairs.
    Later entries override earlier ones for the same hand.
    """
    result = {}
    for range_str, freq in specs:
        for hand in _expand_range(range_str):
            result[hand] = freq
    return result


# =============================================================================
# RFI (Raise First In) - raise frequency when folded to hero
# =============================================================================

GTO_RFI = {
    # ── UTG (~14%) ──────────────────────────────────────────────────────
    "UTG": _t(
        ("AA-77", 1.0), ("66", 0.6), ("55", 0.25),
        ("AKs-ATs", 1.0), ("A9s", 0.4), ("A5s", 1.0), ("A4s", 0.45),
        ("KQs", 1.0), ("KJs", 1.0), ("KTs", 0.55),
        ("QJs", 1.0), ("QTs", 0.35),
        ("JTs", 0.6), ("T9s", 0.2),
        ("AKo", 1.0), ("AQo", 1.0), ("AJo", 0.4),
    ),

    # ── UTG1 (~16%) ────────────────────────────────────────────────────
    "UTG1": _t(
        ("AA-66", 1.0), ("55", 0.55),
        ("AKs-A9s", 1.0), ("A8s", 0.3), ("A5s", 1.0), ("A4s", 0.8), ("A3s", 0.25),
        ("KQs-KTs", 1.0), ("K9s", 0.25),
        ("QJs", 1.0), ("QTs", 0.65),
        ("JTs", 1.0), ("T9s", 0.4),
        ("AKo", 1.0), ("AQo", 1.0), ("AJo", 0.7), ("KQo", 0.25),
    ),

    # ── UTG2 (~18%) ────────────────────────────────────────────────────
    "UTG2": _t(
        ("AA-55", 1.0), ("44", 0.4),
        ("AKs-A8s", 1.0), ("A7s", 0.5), ("A5s-A4s", 1.0), ("A3s", 0.6), ("A2s", 0.25),
        ("KQs-KTs", 1.0), ("K9s", 0.5),
        ("QJs-QTs", 1.0), ("Q9s", 0.25),
        ("JTs", 1.0), ("J9s", 0.3), ("T9s", 0.65), ("98s", 0.25),
        ("AKo-AJo", 1.0), ("ATo", 0.3), ("KQo", 0.55),
    ),

    # ── LJ (~21%) ──────────────────────────────────────────────────────
    "LJ": _t(
        ("AA-44", 1.0), ("33", 0.5),
        ("AKs-A7s", 1.0), ("A6s", 0.65), ("A5s-A3s", 1.0), ("A2s", 0.55),
        ("KQs-K9s", 1.0), ("K8s", 0.45), ("K7s", 0.25),
        ("QJs-Q9s", 1.0), ("Q8s", 0.35),
        ("JTs-J9s", 1.0), ("J8s", 0.25),
        ("T9s", 1.0), ("98s", 0.55), ("87s", 0.35),
        ("AKo-ATo", 1.0), ("A9o", 0.25), ("KQo", 1.0), ("KJo", 0.45),
    ),

    # ── HJ (~25%) ──────────────────────────────────────────────────────
    "HJ": _t(
        ("AA-33", 1.0), ("22", 0.5),
        ("AKs-A5s", 1.0), ("A4s-A2s", 0.8),
        ("KQs-K8s", 1.0), ("K7s", 0.55), ("K6s", 0.35),
        ("QJs-Q8s", 1.0), ("Q7s", 0.35),
        ("JTs-J8s", 1.0), ("J7s", 0.25),
        ("T9s-T8s", 1.0), ("98s", 1.0), ("87s", 0.65), ("76s", 0.45), ("65s", 0.3),
        ("AKo-A9o", 1.0), ("A8o", 0.35), ("KQo-KJo", 1.0), ("KTo", 0.45), ("QJo", 0.35),
    ),

    # ── CO (~30%) ──────────────────────────────────────────────────────
    "CO": _t(
        ("AA-22", 1.0),
        ("AKs-A2s", 1.0),
        ("KQs-K5s", 1.0), ("K4s", 0.65), ("K3s", 0.45), ("K2s", 0.25),
        ("QJs-Q6s", 1.0), ("Q5s", 0.55), ("Q4s", 0.3),
        ("JTs-J7s", 1.0), ("J6s", 0.35),
        ("T9s-T7s", 1.0), ("T6s", 0.25),
        ("98s-97s", 1.0), ("87s-86s", 1.0), ("76s-75s", 1.0), ("65s", 1.0), ("54s", 0.75),
        ("AKo-A7o", 1.0), ("A6o", 0.55), ("A5o", 0.45),
        ("KQo-KTo", 1.0), ("K9o", 0.45),
        ("QJo-QTo", 1.0), ("Q9o", 0.25),
        ("JTo", 0.55),
    ),

    # ── BTN (~45%) ─────────────────────────────────────────────────────
    "BTN": _t(
        ("AA-22", 1.0),
        ("AKs-A2s", 1.0),
        ("KQs-K2s", 1.0),
        ("QJs-Q3s", 1.0), ("Q2s", 0.65),
        ("JTs-J5s", 1.0), ("J4s", 0.55), ("J3s", 0.25),
        ("T9s-T6s", 1.0), ("T5s", 0.35),
        ("98s-96s", 1.0), ("95s", 0.35),
        ("87s-85s", 1.0), ("84s", 0.25),
        ("76s-74s", 1.0), ("73s", 0.25),
        ("65s-63s", 1.0), ("62s", 0.25),
        ("54s-53s", 1.0), ("52s", 0.25),
        ("43s", 0.75),
        ("AKo-A2o", 1.0),
        ("KQo-K7o", 1.0), ("K6o", 0.65), ("K5o", 0.35),
        ("QJo-Q8o", 1.0), ("Q7o", 0.45),
        ("JTo-J8o", 1.0), ("J7o", 0.35),
        ("T9o-T8o", 1.0), ("T7o", 0.25),
        ("98o", 1.0), ("97o", 0.35),
        ("87o", 0.65), ("76o", 0.35), ("65o", 0.25),
    ),

    # ── SB (~40% raise, GTO is raise-or-fold from SB) ─────────────────
    "SB": _t(
        ("AA-22", 1.0),
        ("AKs-A2s", 1.0),
        ("KQs-K3s", 1.0), ("K2s", 0.55),
        ("QJs-Q4s", 1.0), ("Q3s", 0.45), ("Q2s", 0.25),
        ("JTs-J6s", 1.0), ("J5s", 0.45), ("J4s", 0.25),
        ("T9s-T6s", 1.0), ("T5s", 0.25),
        ("98s-95s", 1.0), ("94s", 0.25),
        ("87s-84s", 1.0), ("83s", 0.25),
        ("76s-73s", 1.0),
        ("65s-63s", 1.0),
        ("54s-52s", 1.0),
        ("43s", 0.75), ("42s", 0.25),
        ("32s", 0.35),
        ("AKo-A3o", 1.0), ("A2o", 0.65),
        ("KQo-K7o", 1.0), ("K6o", 0.55), ("K5o", 0.25),
        ("QJo-Q9o", 1.0), ("Q8o", 0.45),
        ("JTo-J9o", 1.0), ("J8o", 0.35),
        ("T9o", 1.0), ("T8o", 0.45),
        ("98o", 0.65), ("87o", 0.45), ("76o", 0.25),
    ),

    # ── BB: not applicable for RFI (BB posts blind, doesn't open) ─────
    # BB acts after facing an open or can check if limped to (rare in GTO)
    "BB": {},
}


# =============================================================================
# Facing RFI - 3-bet and call frequencies
# Indexed by opener group -> hero position -> {hand: freq}
# Opener groups: EP (UTG/UTG1/UTG2), MP (LJ/HJ), CO, BTN, SB
# =============================================================================

GTO_FACING_RFI_3BET = {
    # ── Facing EP open ──────────────────────────────────────────────────
    "EP": {
        "MP": _t(
            ("AA-QQ", 1.0), ("JJ", 0.45),
            ("AKs", 1.0), ("AQs", 0.25),
            ("AKo", 0.65),
            ("A5s", 0.55), ("A4s", 0.4),
        ),
        "LJ": _t(
            ("AA-QQ", 1.0), ("JJ", 0.45),
            ("AKs", 1.0), ("AQs", 0.25),
            ("AKo", 0.65),
            ("A5s", 0.55), ("A4s", 0.4),
        ),
        "HJ": _t(
            ("AA-QQ", 1.0), ("JJ", 0.5),
            ("AKs", 1.0), ("AQs", 0.35),
            ("AKo", 0.7),
            ("A5s", 0.6), ("A4s", 0.45),
        ),
        "CO": _t(
            ("AA-JJ", 1.0), ("TT", 0.35),
            ("AKs", 1.0), ("AQs", 0.5),
            ("AKo", 1.0), ("AQo", 0.2),
            ("A5s", 0.65), ("A4s", 0.5),
        ),
        "BTN": _t(
            ("AA-JJ", 1.0), ("TT", 0.4),
            ("AKs", 1.0), ("AQs", 0.55),
            ("AKo", 1.0), ("AQo", 0.25),
            ("A5s", 0.7), ("A4s", 0.55),
            ("KQs", 0.25),
        ),
        "SB": _t(
            ("AA-QQ", 1.0), ("JJ", 0.5),
            ("AKs", 1.0),
            ("AKo", 0.6),
            ("A5s", 0.5), ("A4s", 0.35),
        ),
        "BB": _t(
            ("AA-QQ", 1.0), ("JJ", 0.4),
            ("AKs", 1.0), ("AQs", 0.2),
            ("AKo", 0.5),
            ("A5s", 0.55), ("A4s", 0.4),
        ),
    },

    # ── Facing MP open (LJ/HJ) ─────────────────────────────────────────
    "MP": {
        "CO": _t(
            ("AA-JJ", 1.0), ("TT", 0.5),
            ("AKs", 1.0), ("AQs", 0.65),
            ("AKo", 1.0), ("AQo", 0.3),
            ("A5s", 0.65), ("A4s", 0.5),
            ("KQs", 0.3),
        ),
        "BTN": _t(
            ("AA-TT", 1.0), ("99", 0.3),
            ("AKs-AQs", 1.0), ("AJs", 0.45),
            ("AKo", 1.0), ("AQo", 0.45),
            ("A5s-A4s", 0.6),
            ("KQs", 0.45), ("KJs", 0.2),
        ),
        "SB": _t(
            ("AA-JJ", 1.0), ("TT", 0.4),
            ("AKs", 1.0), ("AQs", 0.45),
            ("AKo", 1.0), ("AQo", 0.2),
            ("A5s", 0.55), ("A4s", 0.4),
        ),
        "BB": _t(
            ("AA-JJ", 1.0), ("TT", 0.35),
            ("AKs", 1.0), ("AQs", 0.5),
            ("AKo", 0.75),
            ("A5s", 0.6), ("A4s", 0.5), ("A3s", 0.2),
            ("KQs", 0.25),
        ),
    },

    # ── Facing CO open ──────────────────────────────────────────────────
    "CO": {
        "BTN": _t(
            ("AA-TT", 1.0), ("99", 0.45),
            ("AKs-AJs", 1.0), ("ATs", 0.45),
            ("AKo-AQo", 1.0), ("AJo", 0.2),
            ("A5s-A4s", 0.6),
            ("KQs", 0.65), ("KJs", 0.3),
            ("QJs", 0.2),
        ),
        "SB": _t(
            ("AA-TT", 1.0), ("99", 0.35),
            ("AKs-AQs", 1.0), ("AJs", 0.4),
            ("AKo", 1.0), ("AQo", 0.45),
            ("A5s-A4s", 0.55),
            ("KQs", 0.4),
        ),
        "BB": _t(
            ("AA-TT", 1.0), ("99", 0.4),
            ("AKs-AQs", 1.0), ("AJs", 0.55),
            ("AKo", 1.0), ("AQo", 0.55),
            ("A5s-A4s", 0.65), ("A3s", 0.3),
            ("KQs", 0.45), ("KJs", 0.2),
            ("QJs", 0.15),
        ),
    },

    # ── Facing BTN open ─────────────────────────────────────────────────
    "BTN": {
        "SB": _t(
            ("AA-TT", 1.0), ("99", 0.55), ("88", 0.2),
            ("AKs-AJs", 1.0), ("ATs", 0.55), ("A9s", 0.2),
            ("AKo-AQo", 1.0), ("AJo", 0.45),
            ("A5s-A4s", 0.65), ("A3s", 0.3),
            ("KQs", 0.75), ("KJs", 0.4), ("KTs", 0.15),
            ("QJs", 0.3), ("QTs", 0.1),
        ),
        "BB": _t(
            ("AA-99", 1.0), ("88", 0.55), ("77", 0.2),
            ("AKs-ATs", 1.0), ("A9s", 0.55), ("A8s", 0.2),
            ("AKo-AJo", 1.0), ("ATo", 0.55),
            ("A5s-A3s", 0.7), ("A2s", 0.3),
            ("KQs-KJs", 1.0), ("KTs", 0.5), ("K9s", 0.15),
            ("QJs", 0.6), ("QTs", 0.3),
            ("JTs", 0.2),
        ),
    },

    # ── Facing SB open (BB only) ────────────────────────────────────────
    "SB": {
        "BB": _t(
            ("AA-88", 1.0), ("77", 0.6), ("66", 0.3),
            ("AKs-A9s", 1.0), ("A8s", 0.65), ("A7s", 0.35),
            ("AKo-ATo", 1.0), ("A9o", 0.55), ("A8o", 0.2),
            ("A5s-A2s", 0.7),
            ("KQs-KTs", 1.0), ("K9s", 0.55), ("K8s", 0.2),
            ("KQo", 1.0), ("KJo", 0.55), ("KTo", 0.2),
            ("QJs-QTs", 1.0), ("Q9s", 0.45), ("Q8s", 0.15),
            ("QJo", 0.5),
            ("JTs", 1.0), ("J9s", 0.45),
            ("T9s", 0.55), ("98s", 0.3), ("87s", 0.15),
        ),
    },
}

GTO_FACING_RFI_CALL = {
    # ── Facing EP open ──────────────────────────────────────────────────
    "EP": {
        "MP": _t(
            ("JJ", 0.55), ("TT-88", 1.0), ("77", 0.65),
            ("AQs", 0.75), ("AJs", 1.0), ("ATs", 0.7),
            ("AKo", 0.35), ("AQo", 0.35),
            ("KQs", 1.0), ("KJs", 0.55),
            ("QJs", 0.6), ("JTs", 0.55), ("T9s", 0.35),
        ),
        "LJ": _t(
            ("JJ", 0.55), ("TT-88", 1.0), ("77", 0.65),
            ("AQs", 0.75), ("AJs", 1.0), ("ATs", 0.7),
            ("AKo", 0.35), ("AQo", 0.35),
            ("KQs", 1.0), ("KJs", 0.55),
            ("QJs", 0.6), ("JTs", 0.55), ("T9s", 0.35),
        ),
        "HJ": _t(
            ("JJ", 0.5), ("TT-77", 1.0), ("66", 0.5),
            ("AQs", 0.65), ("AJs", 1.0), ("ATs", 0.8),
            ("AKo", 0.3), ("AQo", 0.45),
            ("KQs", 1.0), ("KJs", 0.7), ("KTs", 0.3),
            ("QJs", 0.75), ("QTs", 0.3),
            ("JTs", 0.7), ("T9s", 0.45), ("98s", 0.2),
        ),
        "CO": _t(
            ("TT", 0.65), ("99-66", 1.0), ("55", 0.6),
            ("AQs", 0.5), ("AJs-ATs", 1.0), ("A9s", 0.45),
            ("AQo", 0.55), ("AJo", 0.3),
            ("KQs", 1.0), ("KJs", 1.0), ("KTs", 0.55),
            ("QJs", 1.0), ("QTs", 0.6),
            ("JTs", 1.0), ("J9s", 0.35),
            ("T9s", 0.8), ("98s", 0.45), ("87s", 0.25),
        ),
        "BTN": _t(
            ("TT", 0.6), ("99-55", 1.0), ("44", 0.55),
            ("AQs", 0.45), ("AJs-A9s", 1.0), ("A8s", 0.35),
            ("AQo", 0.5), ("AJo", 0.45), ("ATo", 0.2),
            ("KQs", 1.0), ("KJs", 1.0), ("KTs", 0.7), ("K9s", 0.25),
            ("QJs", 1.0), ("QTs", 0.75), ("Q9s", 0.2),
            ("JTs", 1.0), ("J9s", 0.5),
            ("T9s", 1.0), ("98s", 0.6), ("87s", 0.35), ("76s", 0.15),
        ),
        "SB": _t(
            # SB mostly 3bets or folds vs EP, very narrow call range
            ("JJ", 0.3), ("TT-99", 0.5),
            ("AQs", 0.35), ("AJs", 0.4),
            ("KQs", 0.3),
        ),
        "BB": _t(
            ("JJ", 0.6), ("TT-22", 1.0),
            ("AQs", 0.8), ("AJs-A7s", 1.0), ("A6s", 0.65), ("A5s", 0.45), ("A4s", 0.6), ("A3s-A2s", 0.5),
            ("AQo", 0.75), ("AJo", 1.0), ("ATo", 0.75), ("A9o", 0.35),
            ("KQs", 1.0), ("KJs", 1.0), ("KTs", 1.0), ("K9s", 0.7), ("K8s", 0.35),
            ("KQo", 0.8), ("KJo", 0.5),
            ("QJs", 1.0), ("QTs", 1.0), ("Q9s", 0.65), ("Q8s", 0.25),
            ("JTs", 1.0), ("J9s", 0.8), ("J8s", 0.25),
            ("T9s", 1.0), ("T8s", 0.55),
            ("98s", 0.85), ("97s", 0.25),
            ("87s", 0.65), ("76s", 0.45), ("65s", 0.35), ("54s", 0.25),
        ),
    },

    # ── Facing MP open ──────────────────────────────────────────────────
    "MP": {
        "CO": _t(
            ("TT", 0.5), ("99-66", 1.0), ("55", 0.55),
            ("AQs", 0.35), ("AJs-ATs", 1.0), ("A9s", 0.5),
            ("AQo", 0.45), ("AJo", 0.35),
            ("KQs", 0.7), ("KJs", 1.0), ("KTs", 0.6),
            ("QJs", 1.0), ("QTs", 0.65),
            ("JTs", 1.0), ("J9s", 0.35),
            ("T9s", 0.85), ("98s", 0.5), ("87s", 0.3),
        ),
        "BTN": _t(
            ("99", 0.7), ("88-44", 1.0), ("33", 0.55),
            ("AJs", 0.55), ("ATs", 1.0), ("A9s", 0.7), ("A8s", 0.25),
            ("AQo", 0.55), ("AJo", 0.55), ("ATo", 0.25),
            ("KQs", 0.55), ("KJs", 1.0), ("KTs", 0.8), ("K9s", 0.3),
            ("QJs", 1.0), ("QTs", 0.85), ("Q9s", 0.25),
            ("JTs", 1.0), ("J9s", 0.55),
            ("T9s", 1.0), ("T8s", 0.35),
            ("98s", 0.75), ("87s", 0.5), ("76s", 0.3), ("65s", 0.15),
        ),
        "SB": _t(
            ("TT", 0.35), ("99", 0.5),
            ("AQs", 0.3), ("AJs", 0.45),
            ("KQs", 0.25),
        ),
        "BB": _t(
            ("TT", 0.65), ("99-22", 1.0),
            ("AQs", 0.5), ("AJs-A6s", 1.0), ("A5s", 0.4), ("A4s", 0.5), ("A3s-A2s", 0.55),
            ("AQo", 0.65), ("AJo", 1.0), ("ATo", 0.85), ("A9o", 0.45), ("A8o", 0.15),
            ("KQs", 0.75), ("KJs", 1.0), ("KTs", 1.0), ("K9s", 0.8), ("K8s", 0.4), ("K7s", 0.15),
            ("KQo", 0.85), ("KJo", 0.65), ("KTo", 0.2),
            ("QJs", 1.0), ("QTs", 1.0), ("Q9s", 0.75), ("Q8s", 0.3),
            ("QJo", 0.45), ("QTo", 0.15),
            ("JTs", 1.0), ("J9s", 0.85), ("J8s", 0.35),
            ("T9s", 1.0), ("T8s", 0.65), ("T7s", 0.15),
            ("98s", 0.9), ("97s", 0.35),
            ("87s", 0.75), ("86s", 0.15),
            ("76s", 0.55), ("65s", 0.45), ("54s", 0.35),
        ),
    },

    # ── Facing CO open ──────────────────────────────────────────────────
    "CO": {
        "BTN": _t(
            ("99", 0.55), ("88-33", 1.0), ("22", 0.65),
            ("ATs", 0.55), ("A9s-A6s", 1.0), ("A5s", 0.4),
            ("AJo", 0.8), ("ATo", 1.0), ("A9o", 0.4),
            ("KQs", 0.35), ("KJs-K9s", 1.0), ("K8s", 0.45),
            ("KQo", 0.75), ("KJo", 0.75), ("KTo", 0.35),
            ("QJs", 0.8), ("QTs", 1.0), ("Q9s", 0.75), ("Q8s", 0.25),
            ("QJo", 0.45),
            ("JTs", 1.0), ("J9s", 0.85), ("J8s", 0.3),
            ("T9s", 1.0), ("T8s", 0.6),
            ("98s", 0.85), ("97s", 0.25),
            ("87s", 0.7), ("76s", 0.45), ("65s", 0.35), ("54s", 0.2),
        ),
        "SB": _t(
            ("99", 0.4), ("88", 0.55), ("77", 0.35),
            ("AJs", 0.4), ("ATs", 0.55), ("A9s", 0.25),
            ("AQo", 0.3), ("AJo", 0.35),
            ("KQs", 0.3), ("KJs", 0.35),
            ("QJs", 0.2),
        ),
        "BB": _t(
            ("99", 0.6), ("88-22", 1.0),
            ("AJs", 0.45), ("ATs-A2s", 1.0),
            ("AQo", 0.45), ("AJo", 1.0), ("ATo", 1.0), ("A9o", 0.65), ("A8o", 0.3),
            ("KQs", 0.55), ("KJs-K7s", 1.0), ("K6s", 0.55), ("K5s", 0.25),
            ("KQo", 0.9), ("KJo", 0.85), ("KTo", 0.55), ("K9o", 0.15),
            ("QJs", 1.0), ("QTs", 1.0), ("Q9s", 0.85), ("Q8s", 0.45), ("Q7s", 0.1),
            ("QJo", 0.65), ("QTo", 0.3),
            ("JTs", 1.0), ("J9s", 0.9), ("J8s", 0.45), ("J7s", 0.1),
            ("JTo", 0.3),
            ("T9s", 1.0), ("T8s", 0.75), ("T7s", 0.2),
            ("98s", 1.0), ("97s", 0.5), ("96s", 0.1),
            ("87s", 0.85), ("86s", 0.3),
            ("76s", 0.7), ("75s", 0.15),
            ("65s", 0.6), ("64s", 0.1),
            ("54s", 0.5), ("43s", 0.15),
        ),
    },

    # ── Facing BTN open ─────────────────────────────────────────────────
    "BTN": {
        "SB": _t(
            # SB vs BTN is mostly 3bet-or-fold, narrow call range
            ("88", 0.45), ("77", 0.5), ("66", 0.25),
            ("ATs", 0.3), ("A9s", 0.35),
            ("AJo", 0.3), ("ATo", 0.25),
            ("KJs", 0.3), ("KTs", 0.35),
            ("QJs", 0.25), ("QTs", 0.3),
            ("JTs", 0.3), ("J9s", 0.15),
            ("T9s", 0.35), ("98s", 0.2),
        ),
        "BB": _t(
            ("88", 0.45), ("77-22", 1.0),
            ("ATs", 0.4), ("A9s-A2s", 1.0),
            ("AJo", 0.5), ("ATo", 1.0), ("A9o", 0.8), ("A8o", 0.45), ("A7o", 0.2),
            ("KJs", 0.5), ("KTs-K5s", 1.0), ("K4s", 0.55), ("K3s", 0.25),
            ("KQo", 0.6), ("KJo", 1.0), ("KTo", 0.85), ("K9o", 0.35),
            ("QJs", 0.4), ("QTs-Q6s", 1.0), ("Q5s", 0.35),
            ("QJo", 0.75), ("QTo", 0.5), ("Q9o", 0.15),
            ("JTs", 0.8), ("J9s-J6s", 1.0), ("J5s", 0.2),
            ("JTo", 0.45), ("J9o", 0.15),
            ("T9s", 1.0), ("T8s-T6s", 1.0), ("T5s", 0.1),
            ("T9o", 0.25),
            ("98s", 1.0), ("97s-95s", 1.0),
            ("98o", 0.15),
            ("87s", 1.0), ("86s-84s", 1.0),
            ("76s", 1.0), ("75s-73s", 1.0),
            ("65s", 1.0), ("64s-63s", 0.8), ("62s", 0.25),
            ("54s", 1.0), ("53s-52s", 0.6),
            ("43s", 0.65), ("42s", 0.2),
            ("32s", 0.3),
        ),
    },

    # ── Facing SB open ──────────────────────────────────────────────────
    "SB": {
        "BB": _t(
            ("77", 0.4), ("66-22", 1.0),
            ("A8s", 0.35), ("A7s-A2s", 1.0),
            ("A9o", 0.45), ("A8o", 0.8), ("A7o", 0.55), ("A6o", 0.3),
            ("KTs", 0.45), ("K9s-K4s", 1.0), ("K3s", 0.55), ("K2s", 0.25),
            ("KJo", 0.45), ("KTo", 0.75), ("K9o", 0.45), ("K8o", 0.15),
            ("QTs", 0.45), ("Q9s-Q5s", 1.0), ("Q4s", 0.45), ("Q3s", 0.15),
            ("QJo", 0.35), ("QTo", 0.55), ("Q9o", 0.25),
            ("JTs", 0.55), ("J9s-J6s", 1.0), ("J5s", 0.35),
            ("JTo", 0.3), ("J9o", 0.2),
            ("T9s", 0.75), ("T8s-T6s", 1.0), ("T5s", 0.2),
            ("T9o", 0.2),
            ("98s", 0.85), ("97s-95s", 1.0), ("94s", 0.15),
            ("87s", 0.9), ("86s-84s", 1.0), ("83s", 0.1),
            ("76s", 0.85), ("75s-73s", 1.0),
            ("65s", 0.85), ("64s-62s", 1.0),
            ("54s", 0.85), ("53s-52s", 0.75),
            ("43s", 0.65), ("42s", 0.35),
            ("32s", 0.35),
        ),
    },
}


# =============================================================================
# Facing 3-bet after hero opened
# Indexed by hero's open position -> {hand: freq} for 4-bet and call
# =============================================================================

GTO_FACING_3BET_4BET = {
    "UTG": _t(
        ("AA", 1.0), ("KK", 1.0), ("QQ", 0.55),
        ("AKs", 0.65),
        ("AKo", 0.3),
    ),
    "UTG1": _t(
        ("AA", 1.0), ("KK", 1.0), ("QQ", 0.6),
        ("AKs", 0.7),
        ("AKo", 0.35),
    ),
    "UTG2": _t(
        ("AA", 1.0), ("KK", 1.0), ("QQ", 0.65),
        ("AKs", 0.75),
        ("AKo", 0.4),
    ),
    "LJ": _t(
        ("AA-KK", 1.0), ("QQ", 0.7),
        ("AKs", 0.8), ("AQs", 0.15),
        ("AKo", 0.5),
    ),
    "HJ": _t(
        ("AA-KK", 1.0), ("QQ", 0.8),
        ("AKs", 0.85), ("AQs", 0.2),
        ("AKo", 0.55),
    ),
    "CO": _t(
        ("AA-KK", 1.0), ("QQ", 0.85), ("JJ", 0.2),
        ("AKs", 1.0), ("AQs", 0.3),
        ("AKo", 0.65),
        ("A5s", 0.2),
    ),
    "BTN": _t(
        ("AA-QQ", 1.0), ("JJ", 0.35),
        ("AKs", 1.0), ("AQs", 0.45),
        ("AKo", 0.75),
        ("A5s", 0.35), ("A4s", 0.2),
    ),
    "SB": _t(
        ("AA-QQ", 1.0), ("JJ", 0.4),
        ("AKs", 1.0), ("AQs", 0.35),
        ("AKo", 0.65),
        ("A5s", 0.3),
    ),
}

GTO_FACING_3BET_CALL = {
    "UTG": _t(
        ("QQ", 0.45), ("JJ", 1.0), ("TT", 0.65),
        ("AKs", 0.35), ("AQs", 1.0), ("AJs", 0.55),
        ("AKo", 0.55),
        ("KQs", 0.45),
    ),
    "UTG1": _t(
        ("QQ", 0.4), ("JJ", 1.0), ("TT", 0.7),
        ("AKs", 0.3), ("AQs", 1.0), ("AJs", 0.65),
        ("AKo", 0.5),
        ("KQs", 0.5),
    ),
    "UTG2": _t(
        ("QQ", 0.35), ("JJ", 1.0), ("TT", 0.8),
        ("AKs", 0.25), ("AQs", 1.0), ("AJs", 0.75), ("ATs", 0.2),
        ("AKo", 0.45),
        ("KQs", 0.6), ("KJs", 0.15),
    ),
    "LJ": _t(
        ("QQ", 0.3), ("JJ", 1.0), ("TT", 0.85),
        ("AKs", 0.2), ("AQs", 1.0), ("AJs", 0.8), ("ATs", 0.3),
        ("AKo", 0.35),
        ("KQs", 0.7), ("KJs", 0.2),
        ("QJs", 0.15),
    ),
    "HJ": _t(
        ("QQ", 0.2), ("JJ", 1.0), ("TT", 0.9),
        ("AQs", 1.0), ("AJs", 0.85), ("ATs", 0.4),
        ("AKo", 0.3),
        ("KQs", 0.75), ("KJs", 0.3),
        ("QJs", 0.2),
    ),
    "CO": _t(
        ("JJ", 0.8), ("TT", 1.0), ("99", 0.4),
        ("AQs", 1.0), ("AJs", 1.0), ("ATs", 0.55),
        ("AKo", 0.35), ("AQo", 0.2),
        ("KQs", 0.85), ("KJs", 0.45),
        ("QJs", 0.35), ("JTs", 0.15),
    ),
    "BTN": _t(
        ("JJ", 0.65), ("TT", 1.0), ("99", 0.55),
        ("AQs", 0.55), ("AJs", 1.0), ("ATs", 0.7),
        ("AKo", 0.25), ("AQo", 0.3),
        ("KQs", 0.8), ("KJs", 0.55), ("KTs", 0.2),
        ("QJs", 0.5), ("QTs", 0.15),
        ("JTs", 0.25), ("T9s", 0.1),
    ),
    "SB": _t(
        ("JJ", 0.6), ("TT", 1.0), ("99", 0.45),
        ("AQs", 0.65), ("AJs", 1.0), ("ATs", 0.55),
        ("AKo", 0.25), ("AQo", 0.2),
        ("KQs", 0.75), ("KJs", 0.4),
        ("QJs", 0.35),
    ),
}


# =============================================================================
# Position group mapping
# =============================================================================

def _pos_to_opener_group(pos):
    """Map a specific position to an opener group for table lookup."""
    pos = pos.upper()
    if pos in ("UTG", "UTG1", "UTG2"):
        return "EP"
    if pos in ("LJ", "HJ"):
        return "MP"
    return pos  # CO, BTN, SB are their own groups


# Position order for 9-max (earlier = tighter)
POS_ORDER = ["UTG", "UTG1", "UTG2", "LJ", "HJ", "CO", "BTN", "SB", "BB"]


def _is_position_after(pos_a, pos_b):
    """Return True if pos_a acts after pos_b in preflop order."""
    try:
        return POS_ORDER.index(pos_a) > POS_ORDER.index(pos_b)
    except ValueError:
        return False


# =============================================================================
# Main lookup API
# =============================================================================

def lookup_preflop_gto(hero_hand, hero_pos, action_state):
    """
    Look up GTO preflop strategy for hero's hand.

    Args:
        hero_hand: list of 2 cards, e.g. ["As", "Kh"]
        hero_pos: hero's position, e.g. "BTN"
        action_state: dict with keys:
            - "scenario": one of "rfi", "facing_rfi", "facing_3bet", "facing_4bet"
            - "opener_pos": position of the original raiser (for facing_rfi / facing_3bet)

    Returns:
        dict with action frequencies and recommendation:
        {
            "hand": "AKo",
            "scenario": "rfi",
            "actions": {"raise": 1.0, "call": 0.0, "fold": 0.0},
            "recommendation": "RAISE",
            "frequency": 1.0,
            "source": "gto_table"
        }
    """
    canonical = hand_to_canonical(hero_hand[0], hero_hand[1])
    hero_pos = hero_pos.upper()
    scenario = action_state.get("scenario", "rfi")
    opener_pos = action_state.get("opener_pos", "CO").upper()

    result = {
        "hand": canonical,
        "scenario": scenario,
        "hero_pos": hero_pos,
        "actions": {"raise": 0.0, "call": 0.0, "fold": 1.0},
        "recommendation": "FOLD",
        "frequency": 1.0,
        "source": "gto_table",
    }

    if scenario == "rfi":
        # Raise first in
        table = GTO_RFI.get(hero_pos, {})
        raise_freq = table.get(canonical, 0.0)
        result["actions"] = {
            "raise": raise_freq,
            "call": 0.0,  # GTO doesn't limp (except BB check)
            "fold": 1.0 - raise_freq,
        }
        if raise_freq >= 0.5:
            result["recommendation"] = "RAISE"
            result["frequency"] = raise_freq
        else:
            result["recommendation"] = "FOLD"
            result["frequency"] = 1.0 - raise_freq

    elif scenario == "facing_rfi":
        opener_group = _pos_to_opener_group(opener_pos)
        bet3_tables = GTO_FACING_RFI_3BET.get(opener_group, {})
        call_tables = GTO_FACING_RFI_CALL.get(opener_group, {})

        bet3_freq = bet3_tables.get(hero_pos, {}).get(canonical, 0.0)
        call_freq = call_tables.get(hero_pos, {}).get(canonical, 0.0)

        # If hero position not found exactly, try nearby positions
        if bet3_freq == 0.0 and call_freq == 0.0:
            # Try MP as fallback for LJ/HJ
            for fallback_pos in [hero_pos, "BTN", "CO", "BB"]:
                b = bet3_tables.get(fallback_pos, {}).get(canonical, 0.0)
                c = call_tables.get(fallback_pos, {}).get(canonical, 0.0)
                if b > 0 or c > 0:
                    bet3_freq, call_freq = b, c
                    break

        fold_freq = max(0.0, 1.0 - bet3_freq - call_freq)
        result["actions"] = {
            "raise": bet3_freq,  # 3-bet
            "call": call_freq,
            "fold": fold_freq,
        }

        if bet3_freq >= call_freq and bet3_freq >= fold_freq:
            result["recommendation"] = "RAISE"
            result["frequency"] = bet3_freq
        elif call_freq >= fold_freq:
            result["recommendation"] = "CALL"
            result["frequency"] = call_freq
        else:
            result["recommendation"] = "FOLD"
            result["frequency"] = fold_freq

    elif scenario == "facing_3bet":
        bet4_table = GTO_FACING_3BET_4BET.get(hero_pos, {})
        call_table = GTO_FACING_3BET_CALL.get(hero_pos, {})

        bet4_freq = bet4_table.get(canonical, 0.0)
        call_freq = call_table.get(canonical, 0.0)
        fold_freq = max(0.0, 1.0 - bet4_freq - call_freq)

        result["actions"] = {
            "raise": bet4_freq,  # 4-bet
            "call": call_freq,
            "fold": fold_freq,
        }

        if bet4_freq >= call_freq and bet4_freq >= fold_freq:
            result["recommendation"] = "RAISE"
            result["frequency"] = bet4_freq
        elif call_freq >= fold_freq:
            result["recommendation"] = "CALL"
            result["frequency"] = call_freq
        else:
            result["recommendation"] = "FOLD"
            result["frequency"] = fold_freq

    elif scenario == "facing_4bet":
        # vs 4-bet: very tight, only continue with premiums
        premiums_5bet = _t(("AA", 1.0), ("KK", 0.8), ("AKs", 0.3))
        premiums_call = _t(("KK", 0.2), ("QQ", 0.75), ("AKs", 0.55), ("AKo", 0.25))

        bet5_freq = premiums_5bet.get(canonical, 0.0)
        call_freq = premiums_call.get(canonical, 0.0)
        fold_freq = max(0.0, 1.0 - bet5_freq - call_freq)

        result["actions"] = {
            "raise": bet5_freq,
            "call": call_freq,
            "fold": fold_freq,
        }

        if bet5_freq >= call_freq and bet5_freq >= fold_freq:
            result["recommendation"] = "RAISE"
            result["frequency"] = bet5_freq
        elif call_freq >= fold_freq:
            result["recommendation"] = "CALL"
            result["frequency"] = call_freq
        else:
            result["recommendation"] = "FOLD"
            result["frequency"] = fold_freq

    return result


def detect_preflop_scenario(state):
    """
    Detect the preflop scenario from a game state dict.
    Uses position-aware logic to distinguish blinds, limps, opens, and 3bets.

    Returns:
        dict: {"scenario": ..., "opener_pos": ..., "action_log": [...]}
              suitable for lookup_preflop_gto()
    """
    players = state.get("players", [])
    hero_pos = state.get("hero_position", "BTN").upper()
    bb = _estimate_bb(state)

    # Build action log: classify each player's bet
    action_log = []
    raise_levels = []  # (pos, bet) for bets that are actual raises (> previous raise)

    for p in players:
        pos = p.get("position", "?").upper()
        bet = p.get("bet", 0) or 0
        folded = p.get("folded", False)

        if pos == hero_pos:
            action_log.append({"pos": pos, "bet": bet, "action": "hero", "is_hero": True})
            continue

        if folded:
            action_log.append({"pos": pos, "bet": 0, "action": "fold", "is_hero": False})
            continue

        if bet <= 0:
            action_log.append({"pos": pos, "bet": 0, "action": "waiting", "is_hero": False})
            continue

        # Classify the bet based on position and size
        action = _classify_bet(pos, bet, bb)
        action_log.append({"pos": pos, "bet": bet, "action": action, "is_hero": False})

        if action in ("open", "3bet", "4bet"):
            raise_levels.append((pos, bet))

    # Sort raises by size to find the aggressor chain
    raise_levels.sort(key=lambda x: x[1])

    # Now determine the scenario from hero's perspective
    # Look at non-hero, non-folded players with actual raises
    raises = [(pos, bet) for pos, bet in raise_levels]

    if not raises:
        # No raises detected - either all limps/folds or folded to hero
        has_limps = any(e["action"] == "limp" for e in action_log)
        return {"scenario": "rfi", "action_log": action_log,
                "note": "limps ahead" if has_limps else "folded to hero"}

    # Count distinct raise levels
    # A raise is > 1.5x the previous raise level (or > 1.5x BB if first)
    distinct_raises = []
    prev_level = bb
    for pos, bet in raises:
        if bet > prev_level * 1.4:
            distinct_raises.append((pos, bet))
            prev_level = bet

    n_raises = len(distinct_raises)

    if n_raises == 0:
        return {"scenario": "rfi", "action_log": action_log}
    elif n_raises == 1:
        opener_pos = distinct_raises[0][0]
        return {"scenario": "facing_rfi", "opener_pos": opener_pos,
                "action_log": action_log}
    elif n_raises == 2:
        # Two raise levels: open + 3bet
        # If hero was the opener, hero faces a 3bet
        # Otherwise hero faces the latest raiser
        latest_pos = distinct_raises[-1][0]
        return {"scenario": "facing_3bet", "opener_pos": latest_pos,
                "action_log": action_log}
    else:
        # 3+ raise levels: there's a 4bet
        latest_pos = distinct_raises[-1][0]
        return {"scenario": "facing_4bet", "opener_pos": latest_pos,
                "action_log": action_log}


def _classify_bet(pos, bet, bb):
    """Classify a player's bet amount into an action type."""
    if bb <= 0:
        bb = 1

    # Small blind
    if pos == "SB":
        if bet <= bb * 0.6:
            return "sb_blind"
        elif bet <= bb * 1.1:
            return "limp"  # SB completed
        else:
            return _classify_raise_size(bet, bb)

    # Big blind
    if pos == "BB":
        if bet <= bb * 1.1:
            return "bb_blind"
        else:
            return _classify_raise_size(bet, bb)

    # Non-blind positions
    if bet <= bb * 1.1:
        return "limp"
    else:
        return _classify_raise_size(bet, bb)


def _classify_raise_size(bet, bb):
    """Classify a raise by its BB multiple."""
    mult = bet / bb if bb > 0 else 999
    if mult <= 5:
        return "open"
    elif mult <= 14:
        return "3bet"
    else:
        return "4bet"


def _estimate_bb(state):
    """Estimate big blind from state, using multiple heuristics."""
    # 1. Explicit big_blind in state
    bb = state.get("big_blind")
    if bb and bb > 0:
        return bb

    players = state.get("players", [])

    # 2. Look for the BB position's bet (most reliable)
    for p in players:
        pos = p.get("position", "").upper()
        bet = p.get("bet", 0) or 0
        if pos == "BB" and bet > 0:
            return bet

    # 3. Look for SB's bet and double it
    for p in players:
        pos = p.get("position", "").upper()
        bet = p.get("bet", 0) or 0
        if pos == "SB" and bet > 0:
            return bet * 2

    # 4. Fallback: smallest non-zero bet from any player
    bets = [p.get("bet", 0) for p in players if (p.get("bet", 0) or 0) > 0]
    if bets:
        return min(bets)

    return 2  # absolute fallback


def format_gto_action(gto_result):
    """Format a GTO lookup result for display."""
    hand = gto_result["hand"]
    rec = gto_result["recommendation"]
    actions = gto_result["actions"]
    scenario = gto_result["scenario"]

    scenario_label = {
        "rfi": "RFI",
        "facing_rfi": "vs Open",
        "facing_3bet": "vs 3-Bet",
        "facing_4bet": "vs 4-Bet",
    }.get(scenario, scenario)

    # Build frequency string
    parts = []
    action_names = {"raise": "Raise", "call": "Call", "fold": "Fold"}
    for action in ["raise", "call", "fold"]:
        freq = actions.get(action, 0.0)
        if freq > 0.01:
            parts.append(f"{action_names[action]} {freq:.0%}")

    freq_str = " / ".join(parts)
    return f"GTO {scenario_label} [{hand}]: {rec} ({freq_str})"


def format_action_log(action_log):
    """Format the action log for debug display. Returns list of (text, action_type) tuples."""
    ACTION_LABELS = {
        "sb_blind": "SB",
        "bb_blind": "BB",
        "limp": "LIMP",
        "open": "OPEN",
        "3bet": "3BET",
        "4bet": "4BET",
        "fold": "fold",
        "waiting": "...",
        "hero": "HERO",
    }
    lines = []
    for entry in action_log:
        pos = entry["pos"]
        bet = entry["bet"]
        action = entry["action"]
        label = ACTION_LABELS.get(action, action)

        if entry.get("is_hero"):
            lines.append((f"{pos:<5} {'':>6}  HERO", "hero"))
        elif action == "fold":
            lines.append((f"{pos:<5} {'':>6}  fold", "fold"))
        elif action == "waiting":
            lines.append((f"{pos:<5} {'':>6}  ...", "waiting"))
        elif bet > 0:
            lines.append((f"{pos:<5} {bet:>6.1f}  {label}", action))
        else:
            lines.append((f"{pos:<5} {'':>6}  {label}", action))

    return lines
