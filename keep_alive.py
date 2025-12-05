from flask import Flask, jsonify
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

# Dashboard endpoint
@app.route('/dashboard')
def dashboard():
    try:
        import os
        import time
        from db import BotDatabase
        db = BotDatabase()
        user_count = db.get_user_count() if hasattr(db, 'get_user_count') else 'N/A'
        transaction_count = db.get_transaction_count() if hasattr(db, 'get_transaction_count') else 'N/A'
        uptime = time.time() - os.getpid()
        return jsonify({
            "status": "online",
            "user_count": user_count,
            "transaction_count": transaction_count,
            "uptime": uptime
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
