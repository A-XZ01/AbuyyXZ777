import threading
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return 'OK', 200

def keep_alive():
    """Start Flask server on port 8080 for health checks."""
    def run_server():
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    print("[KEEP_ALIVE] Flask server started on port 8080")
