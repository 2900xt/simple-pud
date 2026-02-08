import time
import threading
from capture import WindowCapture
from parser import TableParser
from app import start_server
from database import get_session, Player

def main():
    print("Starting Poker HUD...")

    # 1. Start Capture Service
    capture = WindowCapture()
    capture.start()
    print("Capture service started.")

    # 2. Start Web Server in a separate thread
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    print("Web server started at http://localhost:5000")

    # 3. Main Loop: Parse frames
    parser = TableParser()
    
    # DEBUG: Create improper dummy data to verify visualization works
    session = get_session()
    if session.query(Player).count() == 0:
        dummy = Player(name="Hero", hands_played=100, vpip_count=25, pfr_count=20, aggression_factor=1.5)
        session.add(dummy)
        session.commit()
    session.close()

    try:
        while True:
            frame = capture.get_latest_frame()
            if frame is not None:
                # In the future, we pass this frame to the parser
                # game_state = parser.parse_frame(frame)
                # print("Parsing frame...")
                pass
            
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        capture.stop()

if __name__ == "__main__":
    main()
