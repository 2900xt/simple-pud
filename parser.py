import cv2
import pytesseract
import numpy as np

# Config for Tesseract - assumes it's in PATH
# If not, use pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

class GameState:
    def __init__(self):
        self.players = [] # List of dicts: {name, stack, seat_idx}
        self.community_cards = []
        self.pot_size = 0
        self.dealer_button_idx = -1

class TableParser:
    def __init__(self):
        pass

    def parse_frame(self, frame):
        """
        Main entry point to parse a frame.
        Returns a GameState object.
        """
        if frame is None:
            return None
        
        state = GameState()
        
        # 1. Convert to grayscale for OCR
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # TODO: Define regions of interest (ROI) for players based on table geometry
        # For now, we will just implement a placeholder for full screen OCR to sanity check
        # In a real impl, we would crop to specific player label locations
        
        # Debug: Save frame occasionally to check validity if needed
        # cv2.imwrite("debug_frame.png", frame)
        
        return state

    def extract_text(self, image_region):
        """
        Wrapper for pytesseract
        """
        # Pre-processing for better OCR
        # Thresholding
        _, thumb = cv2.threshold(image_region, 150, 255, cv2.THRESH_BINARY_INV)
        text = pytesseract.image_to_string(thumb, config='--psm 7') # PSM 7: Treat as single text line
        return text.strip()

    def detect_cards(self, table_region):
        # Implementation for card detection
        # Could use template matching or trained YOLO model
        # For simplicity in this plan, we'll start with basic color/contour detection hooks
        pass
