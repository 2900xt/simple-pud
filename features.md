Goal Description
Build a Python-based Poker HUD for PokerStars on Linux that uses screen capture to track game state and displays statistics on a Flask web dashboard.

User Review Required
IMPORTANT

Screen Capture on Linux (Wayland): The user is on Wayland. Standard window geometry detection (like XGetWindowAttributes) often fails or is blocked for security. Strategy: We will use mss to capture the monitor. We will implement a Calibration Mode where the user can click/select the PokerStars window region, or we will attempt to find the window visually using template matching. For now, we will default to a config file defining top, left, width, height which can be populated via a helper script.

Proposed Changes
Architecture
Capture Service: Runs in a background thread. On Wayland, this will likely capture the full desktop or a specific monitor. We will apply a crop based on a config.json setting.
Parser Service: Analyzes screenshots to extract game state (Players, Actions, Cards).
Stats Service: Updates local SQLite DB with new events and calculates aggregate stats.
Web Frontend: Flask app reading from the DB to serve the dashboard.
Dependencies
opencv-python: Image processing.
pytesseract / easyocr: Text recognition.
mss: Screen capture.
numpy: Data handling.
flask: Web server.
sqlalchemy: Database ORM.
Project Structure (New)
[NEW] 

capture.py
WindowCapture class to find window geometry and grab frames.
[NEW] 

parser.py
GameState class.
Functions to identify cards and Read player names/stacks.
[NEW] 

database.py
Models: Player, Hand, Action.
Methods to update stats.
[NEW] 

app.py
Flask routes for / (Dashboard) and /api/stats (JSON data).
[NEW] 

templates/dashboard.html
Main HTML for the interface.
Verification Plan
Automated Tests
Create a tests/ directory.
Mock screen inputs (save a few screenshots of PokerStars tables).
Run parser against mock images and assert that cards/names are correctly identified.
Manual Verification
Open PokerStars (Play Money table).
Run 

main.py
.
Verify console output shows correct game state detection.
Open localhost:5000 and verify stats update as the game progresses.

# Core Features
1. Window Capture & Processing
Target: Specific support for the PokerStars Linux client (or Wine-emulated window).
Technology: Uses mss for high-performance screen capture or X11 calls to locate the window geometry.
Frequency: Captures frames at a low interval (e.g., 1-2fps) to minimize system load while maintaining game state accuracy.
2. Game State Parsing (OCR & Vision)
Hand Recognition: Identifies hole cards and community cards (Flop, Turn, River).
Player Identification: OCRs player names and stack sizes.
Action Tracking:
Detects "Check", "Call", "Raise", "Fold" actions via chat box parsing or button highlighting.
Tracks Pot size.
3. Statistics Engine
Data Persistence: Stores hand history and player stats in a local database (SQLite).
Real-time Metrics:
VPIP (Voluntarily Put Money In Pot): % of hands player puts money in pre-flop.
PFR (Pre-Flop Raise): % of hands player raises pre-flop.
AF (Aggression Factor): (Bet + Raise) / Call.
Hands: Total number of hands tracked for the opponent.
4. Web Dashboard (Flask)
Live HUD: A specific page meant to be overlayed or viewed on a second monitor showing stats for current table opponents.
Session Review: Historical view of past hands and sessions.
Visuals: Simple, high-contrast, dark-mode UI for quick reading while playing.
Technical Constraints
OS: Linux (Ubuntu/Debian based).
Language: Python 3.10+.
Display: Web-based (Flask) to avoid complex overlay drawing issues on Linux (Wayland/X11 compatibility).

