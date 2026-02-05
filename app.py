from flask import Flask, render_template, jsonify
from database import get_session, Player
import threading

app = Flask(__name__)

# Global reference to stats (mock for now, will connect to real parser later)
current_stats = []

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/stats')
def get_stats():
    # In a real scenario, we query the DB or an in-memory cache of the current table
    session = get_session()
    players = session.query(Player).all()
    session.close()
    
    data = [p.to_dict() for p in players]
    return jsonify(data)

def start_server():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == '__main__':
    start_server()
