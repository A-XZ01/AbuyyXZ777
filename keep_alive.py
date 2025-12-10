from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def index():
    """Health check endpoint for DigitalOcean"""
    return 'Bot is running', 200

def keep_alive():
    """Start Flask server for health checks on port 8080"""
    def run_flask():
        port = int(os.getenv('PORT', 8080))
        app.run(host='0.0.0.0', port=port, debug=False)
    
    # Start Flask in background thread
    server_thread = Thread(target=run_flask, daemon=True)
    server_thread.start()
    print(f"[KEEP_ALIVE] Flask health check server started on port 8080")
