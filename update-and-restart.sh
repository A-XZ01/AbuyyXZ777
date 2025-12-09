#!/usr/bin/env bash
# Simple deployment helper for the Discord bot.
# Usage (run from your laptop):
#   ssh root@YOUR_DROPLET_IP "cd /root/AbuyyXZ777 && ./update-and-restart.sh"

set -euo pipefail

cd /root/AbuyyXZ777

echo "[1/4] Pulling latest code..."
git pull

echo "[2/4] Installing dependencies..."
/root/AbuyyXZ777/.venv/bin/pip install -r requirements.txt

echo "[3/4] Restarting supervisor program..."
sudo supervisorctl restart discordbot

echo "[4/4] Recent logs:"
sudo supervisorctl tail -50 discordbot
