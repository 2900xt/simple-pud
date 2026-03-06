#!/usr/bin/env python3
"""Range vs Range Equity Calculator GUI - Debug/Testing Interface"""

import subprocess
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox

EQUITY_CALC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "equity_calc")

RANKS = "AKQJT98765432"
SUITS = "hdsc"
SUIT_COLORS = {"h": "#e74c3c", "d": "#3498db", "s": "#2c3e50", "c": "#27ae60"}
SUIT_SYMBOLS = {"h": "\u2665", "d": "\u2666", "s": "\u2660", "c": "\u2663"}


class CardSelector(tk.Toplevel):
    """Popup for selecting board cards."""

    def __init__(self, parent, used_cards, callback):
        super().__init__(parent)
        self.title("Select Card")
        self.resizable(False, False)
        self.callback = callback
        self.used_cards = set(used_cards)

        frame = ttk.Frame(self, padding=8)
        frame.pack()

        ttk.Label(frame, text="Select a card:", font=("monospace", 11, "bold")).grid(
            row=0, column=0, columnspan=4, pady=(0, 6)
        )

        for ri, rank in enumerate(RANKS):
            for si, suit in enumerate(SUITS):
                card_str = f"{rank}{suit}"
                btn = tk.Button(
                    frame,
                    text=f"{rank}{SUIT_SYMBOLS[suit]}",
                    width=4,
                    font=("monospace", 10),
                    fg=SUIT_COLORS[suit],
                    command=lambda c=card_str: self._select(c),
                )
                if card_str in self.used_cards:
                    btn.config(state="disabled", bg="#ddd")
                btn.grid(row=ri + 1, column=si, padx=1, pady=1)

        self.transient(parent)
        self.grab_set()

    def _select(self, card):
        self.callback(card)
        self.destroy()


class EquityGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Poker Equity Calculator")
        self.root.configure(bg="#1a1a2e")
        self.board_cards = []

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1a1a2e")
        style.configure(
            "TLabel", background="#1a1a2e", foreground="#e0e0e0", font=("Helvetica", 11)
        )
        style.configure(
            "Header.TLabel",
            background="#1a1a2e",
            foreground="#f0f0f0",
            font=("Helvetica", 14, "bold"),
        )
        style.configure(
            "TButton", font=("Helvetica", 10), padding=6
        )
        style.configure(
            "Calc.TButton", font=("Helvetica", 12, "bold"), padding=10
        )

        main = ttk.Frame(root, padding=20)
        main.pack(fill="both", expand=True)

        # Title
        ttk.Label(main, text="Range vs Range Equity", style="Header.TLabel").pack(
            pady=(0, 16)
        )

        # Ranges
        ranges_frame = ttk.Frame(main)
        ranges_frame.pack(fill="x", pady=4)

        # Range 1
        r1_frame = ttk.Frame(ranges_frame)
        r1_frame.pack(fill="x", pady=4)
        ttk.Label(r1_frame, text="Range 1:", width=10, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        self.range1_var = tk.StringVar(value="AA,KK,QQ,AKs")
        self.range1_entry = tk.Entry(
            r1_frame,
            textvariable=self.range1_var,
            font=("monospace", 12),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=2,
        )
        self.range1_entry.pack(side="left", fill="x", expand=True)

        # Range 2
        r2_frame = ttk.Frame(ranges_frame)
        r2_frame.pack(fill="x", pady=4)
        ttk.Label(r2_frame, text="Range 2:", width=10, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        self.range2_var = tk.StringVar(value="JJ,TT,AQs,AQo")
        self.range2_entry = tk.Entry(
            r2_frame,
            textvariable=self.range2_var,
            font=("monospace", 12),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=2,
        )
        self.range2_entry.pack(side="left", fill="x", expand=True)

        # Board
        board_frame = ttk.Frame(main)
        board_frame.pack(fill="x", pady=(12, 4))
        ttk.Label(board_frame, text="Board:", width=10, anchor="e").pack(
            side="left", padx=(0, 8)
        )

        self.board_display = ttk.Frame(board_frame)
        self.board_display.pack(side="left")

        self.card_labels = []
        for i in range(5):
            lbl = tk.Label(
                self.board_display,
                text="  ?  ",
                font=("monospace", 14, "bold"),
                bg="#16213e",
                fg="#555",
                relief="groove",
                width=5,
                height=2,
                cursor="hand2",
            )
            lbl.grid(row=0, column=i, padx=3)
            lbl.bind("<Button-1>", lambda e, idx=i: self._click_card(idx))
            self.card_labels.append(lbl)

        clear_btn = ttk.Button(
            board_frame, text="Clear", command=self._clear_board, width=6
        )
        clear_btn.pack(side="left", padx=(12, 0))

        # Simulations
        sim_frame = ttk.Frame(main)
        sim_frame.pack(fill="x", pady=(12, 4))
        ttk.Label(sim_frame, text="Sims:", width=10, anchor="e").pack(
            side="left", padx=(0, 8)
        )
        self.sims_var = tk.StringVar(value="100000")
        sim_entry = tk.Entry(
            sim_frame,
            textvariable=self.sims_var,
            font=("monospace", 12),
            bg="#16213e",
            fg="#e0e0e0",
            insertbackground="#e0e0e0",
            relief="flat",
            bd=2,
            width=12,
        )
        sim_entry.pack(side="left")

        # Calculate
        calc_btn = tk.Button(
            main,
            text="Calculate Equity",
            font=("Helvetica", 13, "bold"),
            bg="#0f3460",
            fg="#e0e0e0",
            activebackground="#1a508b",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._calculate,
            padx=20,
            pady=8,
        )
        calc_btn.pack(pady=16)

        # Results
        self.results_frame = ttk.Frame(main)
        self.results_frame.pack(fill="x", pady=8)

        # Equity bars
        self.bar_canvas = tk.Canvas(
            self.results_frame, height=50, bg="#16213e", highlightthickness=0
        )
        self.bar_canvas.pack(fill="x", pady=4)

        # Text results
        self.result_text = tk.Text(
            self.results_frame,
            height=6,
            font=("monospace", 11),
            bg="#16213e",
            fg="#e0e0e0",
            relief="flat",
            bd=2,
            state="disabled",
        )
        self.result_text.pack(fill="x", pady=4)

        # Status
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main, textvariable=self.status_var, foreground="#888").pack(
            anchor="w"
        )

        # Key bindings
        self.root.bind("<Return>", lambda e: self._calculate())

    def _click_card(self, idx):
        if idx < len(self.board_cards):
            # Remove this card and all after it
            self.board_cards = self.board_cards[:idx]
            self._refresh_board()
        elif idx == len(self.board_cards) and len(self.board_cards) < 5:
            CardSelector(self.root, self.board_cards, self._add_card)

    def _add_card(self, card_str):
        if len(self.board_cards) < 5:
            self.board_cards.append(card_str)
            self._refresh_board()

    def _clear_board(self):
        self.board_cards = []
        self._refresh_board()

    def _refresh_board(self):
        for i, lbl in enumerate(self.card_labels):
            if i < len(self.board_cards):
                c = self.board_cards[i]
                suit = c[1].lower()
                rank = c[0]
                lbl.config(
                    text=f" {rank}{SUIT_SYMBOLS[suit]} ",
                    fg=SUIT_COLORS[suit],
                    bg="#0a0a23",
                )
            else:
                lbl.config(text="  ?  ", fg="#555", bg="#16213e")

    def _calculate(self):
        r1 = self.range1_var.get().strip()
        r2 = self.range2_var.get().strip()
        if not r1 or not r2:
            messagebox.showwarning("Input Error", "Both ranges are required.")
            return

        board_str = " ".join(self.board_cards) if self.board_cards else ""
        sims = self.sims_var.get().strip() or "100000"

        self.status_var.set("Calculating...")
        self.root.update_idletasks()

        try:
            cmd = [EQUITY_CALC, r1, r2, board_str, sims]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if proc.returncode != 0:
                self.status_var.set("Error")
                self._show_result(f"Error:\n{proc.stderr}")
                return

            output = proc.stdout
            json_marker = output.find("---JSON---")
            if json_marker == -1:
                self._show_result(output)
                self.status_var.set("Done (no JSON)")
                return

            json_str = output[json_marker + len("---JSON---") :].strip()
            data = json.loads(json_str)

            self._draw_bars(data["equity1"], data["equity2"])
            self._show_result(
                f"  Range 1 equity:  {data['equity1']:.2f}%  ({data['combos1']} combos)\n"
                f"  Range 2 equity:  {data['equity2']:.2f}%  ({data['combos2']} combos)\n"
                f"\n"
                f"  Range 1 wins:    {data['wins1']:.2f}%\n"
                f"  Range 2 wins:    {data['wins2']:.2f}%\n"
                f"  Ties:            {data['ties']:.2f}%\n"
                f"  Simulations:     {data['sims']}"
            )
            self.status_var.set(f"Done - {data['sims']} simulations")

        except FileNotFoundError:
            self.status_var.set("Error: equity_calc not found")
            self._show_result(
                f"Could not find equity_calc binary.\n"
                f"Expected at: {EQUITY_CALC}\n\n"
                f"Build it with: make equity"
            )
        except subprocess.TimeoutExpired:
            self.status_var.set("Timeout")
            self._show_result("Calculation timed out (30s limit).")
        except Exception as e:
            self.status_var.set("Error")
            self._show_result(f"Error: {e}")

    def _draw_bars(self, eq1, eq2):
        c = self.bar_canvas
        c.delete("all")
        c.update_idletasks()
        w = c.winfo_width() or 500
        h = 50

        # Range 1 bar (green)
        w1 = max(1, int(w * eq1 / 100))
        c.create_rectangle(0, 0, w1, h, fill="#27ae60", outline="")
        # Range 2 bar (red)
        c.create_rectangle(w1, 0, w, h, fill="#e74c3c", outline="")

        # Labels
        if eq1 > 15:
            c.create_text(
                w1 // 2, h // 2, text=f"R1: {eq1:.1f}%", fill="white",
                font=("Helvetica", 12, "bold"),
            )
        if eq2 > 15:
            c.create_text(
                w1 + (w - w1) // 2, h // 2, text=f"R2: {eq2:.1f}%", fill="white",
                font=("Helvetica", 12, "bold"),
            )

    def _show_result(self, text):
        self.result_text.config(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.config(state="disabled")


def main():
    root = tk.Tk()
    root.geometry("560x520")
    root.minsize(480, 480)
    app = EquityGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
