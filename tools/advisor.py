#!/usr/bin/env python3
"""
Poker Advisor - Estimates villain range, calculates equity, recommends action.

Takes a parsed game state (from screen_parser.py) and:
1. Estimates villain's range based on position, action, and bet sizing
2. Runs equity calculation via the equity_calc binary
3. Computes pot odds and EV for each action
4. Recommends fold / call / raise

Can be used standalone with a JSON file or integrated into screen_parser.py.

Usage:
    python3 tools/advisor.py state.json
    python3 tools/advisor.py --hand "AsKh" --board "Ah 7d 2c" --pot 50 --bet 25 --villain-pos BTN
"""

import argparse
import json
import os
import subprocess
import sys

EQUITY_CALC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "equity_calc")

# ─── Position-based range estimates ──────────────────────────────────────────
# These are approximate ranges for a typical low-mid stakes game.
# Format: {action: {position: range_string}}

# RFI (raise first in) ranges by position
RFI_RANGES = {
    "UTG":  "AA-88,AKs-AJs,AKo,KQs",
    "UTG1": "AA-77,AKs-ATs,AKo-AQo,KQs,KJs",
    "UTG2": "AA-77,AKs-ATs,AKo-AJo,KQs-KTs,QJs",
    "LJ":   "AA-66,AKs-A9s,AKo-ATo,KQs-KTs,QJs-QTs,JTs",
    "HJ":   "AA-55,AKs-A8s,AKo-ATo,KQs-K9s,QJs-Q9s,JTs-J9s,T9s",
    "CO":   "AA-44,AKs-A5s,AKo-A9o,KQs-K8s,KQo-KTo,QJs-Q8s,QJo,JTs-J8s,T9s-T8s,98s,87s,76s",
    "BTN":  "AA-22,AKs-A2s,AKo-A7o,KQs-K5s,KQo-K9o,QJs-Q7s,QJo-Q9o,JTs-J7s,JTo,T9s-T7s,98s-97s,87s-86s,76s-75s,65s,54s",
    "SB":   "AA-66,AKs-A8s,AKo-ATo,KQs-KTs,QJs-QTs,JTs,T9s",
    "BB":   "AA-22,AKs-A2s,AKo-A5o,KQs-K6s,KQo-KTo,QJs-Q8s,QJo-QTo,JTs-J8s,JTo,T9s-T8s,98s-97s,87s,76s,65s",
}

# 3-bet ranges (vs an open raise)
THREEBET_RANGES = {
    "UTG":  "AA-QQ,AKs",
    "UTG1": "AA-QQ,AKs",
    "UTG2": "AA-QQ,AKs,AKo",
    "LJ":   "AA-JJ,AKs,AKo,AQs",
    "HJ":   "AA-TT,AKs,AKo,AQs",
    "CO":   "AA-TT,AKs-AQs,AKo,AQo",
    "BTN":  "AA-99,AKs-AJs,AKo-AQo,KQs",
    "SB":   "AA-TT,AKs-AQs,AKo",
    "BB":   "AA-99,AKs-AJs,AKo-AQo,KQs,A5s-A4s",
}

# Cold call ranges (calling an open)
CALL_RANGES = {
    "UTG":  "99-77,AQs-ATs,KQs",
    "UTG1": "TT-77,AQs-ATs,KQs,KJs",
    "UTG2": "TT-66,AQs-ATs,AQo,KQs-KTs,QJs",
    "LJ":   "TT-55,AQs-A9s,AQo-AJo,KQs-KTs,QJs-QTs,JTs",
    "HJ":   "TT-44,AQs-A8s,AQo-AJo,KQs-K9s,QJs-Q9s,JTs-J9s,T9s",
    "CO":   "TT-33,AQs-A5s,AQo-ATo,KQs-K8s,KQo-KJo,QJs-Q8s,JTs-J8s,T9s-T8s,98s,87s",
    "BTN":  "TT-22,AQs-A2s,AQo-A8o,KQs-K5s,KQo-KTo,QJs-Q7s,QJo,JTs-J7s,T9s-T8s,98s-97s,87s,76s,65s",
    "SB":   "99-66,AQs-ATs,AQo,KQs-KTs,QJs,JTs",
    "BB":   "TT-22,AQs-A2s,AQo-A7o,KQs-K4s,KQo-K9o,QJs-Q6s,QJo-QTo,JTs-J7s,JTo,T9s-T7s,98s-96s,87s-86s,76s-75s,65s,54s",
}

# Postflop continuation bet ranges (as fraction of preflop range)
# Villain c-bets ~60-70% of their range on most flops
# When they check, they have the weaker ~30-40%
# When they bet big (>66% pot), they polarize: strong hands + bluffs
# When they bet small (<33% pot), they use a wide range

DEFAULT_POS = "CO"  # fallback if position unknown


def estimate_villain_range(state):
    """
    Estimate villain's likely range based on game state.
    Returns (range_string, explanation).
    """
    stage = state.get("stage", "preflop")
    players = state.get("players", [])
    pot = state.get("pot") or 0
    current_bet = state.get("current_bet") or 0
    community = state.get("community_cards", [])

    # Find the active villain (non-folded, non-hero player who bet/raised)
    villain = None
    villain_pos = state.get("villain_pos", None)

    active_villains = [p for p in players if not p.get("folded", False)
                       and p.get("position") != state.get("hero_position")]

    if active_villains:
        # Pick the one who bet most (likely aggressor)
        villain = max(active_villains, key=lambda p: p.get("bet", 0))
        if not villain_pos:
            villain_pos = villain.get("position", DEFAULT_POS)

    if not villain_pos:
        villain_pos = DEFAULT_POS

    villain_pos = villain_pos.upper()
    if villain_pos not in RFI_RANGES:
        villain_pos = DEFAULT_POS

    explanation_parts = []

    # ─── Preflop range estimation ────────────────────────────────────────
    if stage == "preflop":
        villain_bet = villain.get("bet", 0) if villain else current_bet

        if villain_bet == 0 or current_bet == 0:
            # Limped or checked
            range_str = CALL_RANGES.get(villain_pos, CALL_RANGES[DEFAULT_POS])
            explanation_parts.append(f"Villain ({villain_pos}) limped/checked preflop")
        elif current_bet > 0:
            # Did anyone raise before villain?
            # Simple heuristic: if bet > 4BB, likely a 3-bet
            bb = _estimate_bb(state)
            if bb > 0 and current_bet >= 4 * bb:
                range_str = THREEBET_RANGES.get(villain_pos, THREEBET_RANGES[DEFAULT_POS])
                explanation_parts.append(f"Villain ({villain_pos}) 3-bet ({current_bet / bb:.0f}BB)")
            else:
                range_str = RFI_RANGES.get(villain_pos, RFI_RANGES[DEFAULT_POS])
                explanation_parts.append(f"Villain ({villain_pos}) open raised ({current_bet / bb:.0f}BB)" if bb > 0
                                         else f"Villain ({villain_pos}) raised")
        else:
            range_str = RFI_RANGES.get(villain_pos, RFI_RANGES[DEFAULT_POS])
            explanation_parts.append(f"Villain ({villain_pos}) opened")

        return range_str, "; ".join(explanation_parts)

    # ─── Postflop range estimation ───────────────────────────────────────
    # Start with preflop range, then narrow based on postflop actions
    preflop_range = RFI_RANGES.get(villain_pos, RFI_RANGES[DEFAULT_POS])
    explanation_parts.append(f"Villain ({villain_pos}) preflop range: {preflop_range}")

    villain_bet = villain.get("bet", 0) if villain else current_bet

    if villain_bet == 0 and current_bet == 0:
        # Villain checked - weaker portion of range
        # Use calling range as proxy for "checked back" range
        range_str = CALL_RANGES.get(villain_pos, CALL_RANGES[DEFAULT_POS])
        explanation_parts.append("Checked postflop -> weaker range")
    else:
        # Villain bet - estimate sizing relative to pot
        if pot > 0 and villain_bet > 0:
            sizing = villain_bet / pot
            if sizing >= 0.75:
                # Big bet = polarized (premium hands + bluffs)
                # Use a tighter range for value, but include some bluffs
                range_str = THREEBET_RANGES.get(villain_pos, THREEBET_RANGES[DEFAULT_POS])
                explanation_parts.append(f"Large bet ({sizing:.0%} pot) -> polarized/strong range")
            elif sizing >= 0.4:
                # Medium bet = standard continuation
                range_str = RFI_RANGES.get(villain_pos, RFI_RANGES[DEFAULT_POS])
                explanation_parts.append(f"Medium bet ({sizing:.0%} pot) -> standard range")
            else:
                # Small bet = wide/blocking
                range_str = CALL_RANGES.get(villain_pos, CALL_RANGES[DEFAULT_POS])
                explanation_parts.append(f"Small bet ({sizing:.0%} pot) -> wide range")
        else:
            range_str = RFI_RANGES.get(villain_pos, RFI_RANGES[DEFAULT_POS])
            explanation_parts.append("Bet postflop -> standard range")

    # Narrow on later streets (turn/river bets = stronger range)
    if stage == "turn" and villain_bet > 0:
        # Double-barrel = stronger
        range_str = THREEBET_RANGES.get(villain_pos, THREEBET_RANGES[DEFAULT_POS])
        explanation_parts.append("Double barrel on turn -> tighter range")
    elif stage == "river" and villain_bet > 0:
        # Triple-barrel = very strong or bluff
        range_str = THREEBET_RANGES.get(villain_pos, THREEBET_RANGES[DEFAULT_POS])
        explanation_parts.append("Triple barrel on river -> polarized (strong/bluff)")

    return range_str, "; ".join(explanation_parts)


def _estimate_bb(state):
    """Try to figure out the big blind size from the game state."""
    bb = state.get("big_blind")
    if bb and bb > 0:
        return bb
    # Heuristic: look at smallest non-zero bet from early positions
    players = state.get("players", [])
    bets = [p.get("bet", 0) for p in players if p.get("bet", 0) > 0]
    if bets:
        min_bet = min(bets)
        # BB is usually the smallest forced bet
        return min_bet
    return 2  # default


def run_equity_calc(hero_hand, villain_range, board_cards, num_sims=100000):
    """
    Call the equity_calc binary and return parsed results.
    hero_hand: "AsKh" (specific hand)
    villain_range: "AA,AKs,TT+" (range string)
    board_cards: ["Ah", "7d", "2c"] or []
    """
    hero_range = hero_hand[0] + hero_hand[1]  # "AsKh" format from 2-element list
    board_str = " ".join(board_cards) if board_cards else ""

    cmd = [EQUITY_CALC, hero_range, villain_range, board_str, str(num_sims)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except FileNotFoundError:
        print(f"Error: equity_calc not found at {EQUITY_CALC}")
        print("Build it with: make equity")
        return None
    except subprocess.TimeoutExpired:
        print("Equity calculation timed out.")
        return None

    if result.returncode != 0:
        print(f"equity_calc error: {result.stderr.strip()}")
        return None

    output = result.stdout
    json_marker = output.find("---JSON---")
    if json_marker == -1:
        print(f"No JSON in equity_calc output:\n{output}")
        return None

    json_str = output[json_marker + len("---JSON---"):].strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        print(f"Failed to parse equity_calc JSON: {json_str}")
        return None


def _bet_ev(equity, pot, bet_size, fold_pct, equity_when_called):
    """EV of betting a given size.
    fold_pct: how often villain folds to this size.
    equity_when_called: our equity vs villain's calling range (tighter = lower).
    """
    # When villain folds we win the pot
    # When villain calls we play for pot + 2*bet with adjusted equity
    ev_when_called = equity_when_called * (pot + 2 * bet_size) - bet_size
    return fold_pct * pot + (1 - fold_pct) * ev_when_called


def _estimate_fold_and_equity(base_equity, bet_frac):
    """Estimate villain fold % and our equity when called, based on bet sizing.
    Larger bets fold out more weak hands -> villain's calling range is stronger
    -> our equity when called drops. Rough heuristic model."""
    # Fold frequency by bet size (fraction of pot)
    fold_pct = min(0.75, max(0.0, 0.15 + bet_frac * 0.35))
    # Equity penalty when called (villain only calls with better portion of range)
    equity_penalty = min(0.20, bet_frac * 0.12)
    eq_when_called = max(0.05, base_equity - equity_penalty)
    return fold_pct, eq_when_called


BET_SIZINGS = [
    (0.33, "33%"),
    (0.50, "50%"),
    (0.66, "66%"),
    (1.00, "100%"),
    (1.50, "150%"),
]


def compute_decision(equity_result, state):
    """
    Given equity and game state, compute EV for each action and recommend.
    Includes detailed bet sizing analysis with EV for multiple sizes.
    """
    pot = state.get("pot") or 0
    current_bet = state.get("current_bet") or 0
    hero_equity = equity_result["equity1"] / 100.0

    hero_player = None
    for p in state.get("players", []):
        if p.get("position") == state.get("hero_position"):
            hero_player = p
            break

    hero_current_bet = hero_player.get("bet", 0) if hero_player else 0
    call_amount = max(0, current_bet - hero_current_bet)
    hero_stack = hero_player.get("stack", 200) if hero_player else 200

    result = {
        "hero_equity": hero_equity * 100,
        "pot": pot,
        "call_amount": call_amount,
        "hero_stack": hero_stack,
    }

    result["ev_fold"] = 0

    # ─── Compute bet sizing EVs ──────────────────────────────────────
    sizing_evs = []
    if pot > 0:
        for frac, label in BET_SIZINGS:
            bet_size = int(pot * frac)
            if bet_size > hero_stack:
                continue
            if bet_size < 1:
                continue
            fold_pct, eq_called = _estimate_fold_and_equity(hero_equity, frac)
            ev = _bet_ev(hero_equity, pot, bet_size, fold_pct, eq_called)
            sizing_evs.append({
                "frac": frac,
                "label": label,
                "size": bet_size,
                "ev": ev,
                "fold_pct": fold_pct,
                "eq_called": eq_called,
            })
    result["sizing_evs"] = sizing_evs

    # ─── No bet to face (check or bet) ──────────────────────────────
    if call_amount == 0:
        result["action_type"] = "no_bet"

        # Find best sizing
        best_sizing = max(sizing_evs, key=lambda s: s["ev"]) if sizing_evs else None

        if hero_equity >= 0.55 and best_sizing and best_sizing["ev"] > 0:
            result["recommendation"] = "BET"
            result["bet_size"] = best_sizing["size"]
            result["bet_label"] = best_sizing["label"]
            result["bet_ev"] = best_sizing["ev"]
            pct = best_sizing["label"]
            result["reason"] = (f"Equity {hero_equity*100:.1f}% - bet {best_sizing['size']} "
                               f"({pct} pot) for value, EV={best_sizing['ev']:+.1f}")
        elif hero_equity >= 0.45:
            result["recommendation"] = "CHECK"
            result["reason"] = f"Marginal equity ({hero_equity*100:.1f}%) - check to control pot"
        else:
            result["recommendation"] = "CHECK"
            result["reason"] = f"Weak equity ({hero_equity*100:.1f}%) - check"

        return result

    # ─── Facing a bet ────────────────────────────────────────────────
    result["action_type"] = "facing_bet"

    pot_odds = call_amount / (pot + call_amount) if (pot + call_amount) > 0 else 0
    result["pot_odds"] = pot_odds * 100

    ev_call = hero_equity * (pot + call_amount) - call_amount
    result["ev_call"] = ev_call

    # Raise sizing options (2.2x, 3x, all-in)
    raise_options = []
    for mult, rlabel in [(2.2, "min-raise"), (3.0, "3x"), (0, "all-in")]:
        if mult > 0:
            rsize = int(current_bet * mult)
        else:
            rsize = hero_stack
        if rsize > hero_stack:
            rsize = hero_stack
        if rsize <= current_bet:
            continue
        # Fold equity is higher for larger raises
        raise_frac = rsize / pot if pot > 0 else 1.0
        fold_pct = min(0.75, max(0.15, 0.20 + raise_frac * 0.25))
        eq_called = max(0.05, hero_equity - min(0.20, raise_frac * 0.10))
        ev_r = fold_pct * pot + (1 - fold_pct) * (eq_called * (pot + rsize + call_amount) - rsize)
        raise_options.append({
            "label": rlabel,
            "size": rsize,
            "ev": ev_r,
            "fold_pct": fold_pct,
        })

    result["raise_options"] = raise_options
    best_raise = max(raise_options, key=lambda r: r["ev"]) if raise_options else None
    result["ev_raise"] = best_raise["ev"] if best_raise else -999
    result["raise_size"] = best_raise["size"] if best_raise else 0

    # Decision
    if best_raise and best_raise["ev"] > ev_call and best_raise["ev"] > 0 and hero_equity >= 0.55:
        result["recommendation"] = "RAISE"
        result["reason"] = (f"Strong equity ({hero_equity*100:.1f}%). "
                           f"Raise to {best_raise['size']} ({best_raise['label']}). "
                           f"EV={best_raise['ev']:+.1f}")
    elif ev_call > 0:
        result["recommendation"] = "CALL"
        result["reason"] = (f"Equity ({hero_equity*100:.1f}%) > pot odds ({pot_odds*100:.1f}%). "
                           f"EV(call)={ev_call:+.1f}")
    elif best_raise and best_raise["ev"] > 0:
        # Can't profitably call but can bluff-raise
        result["recommendation"] = "RAISE"
        result["reason"] = (f"Can't call (EV={ev_call:+.1f}) but raise has fold equity. "
                           f"Raise to {best_raise['size']} EV={best_raise['ev']:+.1f}")
    else:
        result["recommendation"] = "FOLD"
        result["reason"] = (f"Equity ({hero_equity*100:.1f}%) < pot odds ({pot_odds*100:.1f}%). "
                           f"EV(call)={ev_call:+.1f}")

    return result


def analyze(state):
    """
    Full analysis pipeline: estimate range -> calculate equity -> recommend action.
    Returns analysis dict or None.
    """
    hero_hand = state.get("hero_hand", [])
    if not hero_hand or len(hero_hand) < 2:
        print("  Error: Hero hand not detected.")
        return None

    community = state.get("community_cards", [])

    # Estimate villain range
    villain_range, range_explanation = estimate_villain_range(state)

    # Run equity calculation
    equity_data = run_equity_calc(hero_hand, villain_range, community)
    if not equity_data:
        return None

    # Compute decision
    decision = compute_decision(equity_data, state)

    analysis = {
        "hero_hand": hero_hand,
        "community_cards": community,
        "stage": state.get("stage", "unknown"),
        "villain_range": villain_range,
        "range_explanation": range_explanation,
        "equity": equity_data,
        "decision": decision,
    }

    return analysis


def print_analysis(analysis):
    """Pretty-print the full analysis."""
    if not analysis:
        return

    d = analysis["decision"]
    eq = analysis["equity"]

    R = "\033[0m"   # reset
    DIM = "\033[2m"
    BOLD = "\033[1m"

    print(f"\n{BOLD}{'='*58}{R}")
    print(f"  {BOLD}POKER ADVISOR{R}")
    print(f"{BOLD}{'='*58}{R}")
    print(f"  Hero:      {' '.join(analysis['hero_hand'])}")
    board = analysis["community_cards"]
    print(f"  Board:     {' '.join(board) if board else '(preflop)'}")
    print(f"  Stage:     {analysis['stage']}")
    print(f"  Villain:   {analysis['villain_range']}")
    print(f"  {DIM}{analysis['range_explanation']}{R}")
    print(f"{'─'*58}")
    print(f"  Equity:    {BOLD}{d['hero_equity']:.1f}%{R} ({eq['sims']} sims)")
    print(f"  Win/Tie:   {eq['wins1']:.1f}% / {eq['ties']:.1f}%")

    if d["action_type"] == "facing_bet":
        print(f"  Pot:       {d['pot']}   Call: {d['call_amount']}   Stack: {d['hero_stack']}")
        print(f"  Pot Odds:  {d['pot_odds']:.1f}%")
        print(f"  EV(call):  {d['ev_call']:+.1f}")

        raise_opts = d.get("raise_options", [])
        if raise_opts:
            print(f"{'─'*58}")
            print(f"  {DIM}Raise options:{R}")
            for ro in raise_opts:
                marker = " *" if ro["size"] == d.get("raise_size") else "  "
                print(f"   {marker} {ro['label']:>10}  to {ro['size']:<6}  "
                      f"EV={ro['ev']:+.1f}  {DIM}(fold ~{ro['fold_pct']*100:.0f}%){R}")
    else:
        print(f"  Pot:       {d['pot']}   Stack: {d['hero_stack']}")

    # Bet sizing table
    sizing_evs = d.get("sizing_evs", [])
    if sizing_evs and d["action_type"] == "no_bet":
        print(f"{'─'*58}")
        print(f"  {DIM}Bet sizing analysis:{R}")
        best_ev = max(s["ev"] for s in sizing_evs)
        for s in sizing_evs:
            marker = " *" if s["ev"] == best_ev and s["ev"] > 0 else "  "
            print(f"   {marker} {s['label']:>5} pot = {s['size']:<6}  "
                  f"EV={s['ev']:+.1f}  {DIM}(fold ~{s['fold_pct']*100:.0f}%, "
                  f"eq called {s['eq_called']*100:.0f}%){R}")

    rec = d["recommendation"]
    color = {"FOLD": "\033[91m", "CALL": "\033[93m",
             "RAISE": "\033[92m", "BET": "\033[92m",
             "CHECK": "\033[94m"}.get(rec, "")

    print(f"{'─'*58}")
    bet_str = ""
    if rec == "BET" and d.get("bet_size"):
        bet_str = f" {d['bet_size']} ({d.get('bet_label', '?')} pot)"
    elif rec == "RAISE" and d.get("raise_size"):
        bet_str = f" to {d['raise_size']}"
    print(f"  >>> {color}{BOLD}{rec}{bet_str}{R}: {d['reason']}")
    print(f"{BOLD}{'='*58}{R}\n")


def main():
    parser = argparse.ArgumentParser(description="Poker advisor - range estimation & action recommendation")
    parser.add_argument("state_file", nargs="?", help="JSON file from screen_parser.py")
    parser.add_argument("--hand", type=str, help="Hero hand, e.g. AsKh")
    parser.add_argument("--board", type=str, default="", help="Board cards, e.g. 'Ah 7d 2c'")
    parser.add_argument("--pot", type=int, default=0, help="Pot size")
    parser.add_argument("--bet", type=int, default=0, help="Current bet to face")
    parser.add_argument("--villain-pos", type=str, default="CO", help="Villain position")
    parser.add_argument("--hero-pos", type=str, default="BTN", help="Hero position")
    parser.add_argument("--sims", type=int, default=100000, help="Monte Carlo simulations")
    args = parser.parse_args()

    if args.state_file:
        with open(args.state_file) as f:
            state = json.load(f)
    elif args.hand:
        # Build state from CLI args
        hand_str = args.hand.strip()
        hero_hand = [hand_str[0:2], hand_str[2:4]]
        board = args.board.split() if args.board.strip() else []
        stage = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}.get(len(board), "unknown")
        state = {
            "hero_hand": hero_hand,
            "community_cards": board,
            "stage": stage,
            "pot": args.pot,
            "current_bet": args.bet,
            "hero_position": args.hero_pos.upper(),
            "players": [
                {"position": args.hero_pos.upper(), "stack": 200, "bet": 0, "folded": False},
                {"position": args.villain_pos.upper(), "stack": 200, "bet": args.bet, "folded": False},
            ],
        }
    else:
        parser.print_help()
        sys.exit(1)

    analysis = analyze(state)
    if analysis:
        print_analysis(analysis)


if __name__ == "__main__":
    main()
