#!/usr/bin/env python3
"""
Test poker table parsing.
Loads a screenshot and attempts to detect table elements.
"""

import cv2
import numpy as np
import pytesseract
from parser import TableParser

def main():
    # Load a test frame
    print("Loading test frame...")
    frame = cv2.imread('test_frame_0.png')

    if frame is None:
        print("Could not load test frame. Run test_capture.py first.")
        return

    print(f"Frame shape: {frame.shape}")

    # Create parser
    parser = TableParser()

    # Parse the frame
    print("\nParsing frame...")
    state = parser.parse_frame(frame)

    if state:
        print(f"Players: {len(state.players)}")
        print(f"Community cards: {len(state.community_cards)}")
        print(f"Pot size: {state.pot_size}")
    else:
        print("No state returned")

    # Test OCR on the full frame (just to see what text is detected)
    print("\nRunning OCR on full frame...")
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Resize for better OCR (if needed)
    # gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    text = pytesseract.image_to_string(gray)
    print("Detected text:")
    print(text)

    # Save annotated frame
    print("\nSaving debug output...")
    cv2.imwrite('debug_parser.png', frame)
    print("Saved debug_parser.png")

if __name__ == "__main__":
    main()
