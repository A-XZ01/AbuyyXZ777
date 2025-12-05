#!/bin/bash
# Script untuk update bot fix di DigitalOcean

echo "📦 Updating ASBLOX bot with approve-ticket fix..."

cd /home/botuser/AbuyyXZ777

# Pull latest changes
echo "🔄 Pulling latest changes from GitHub..."
git pull origin main

# Restart bot
echo "🔄 Restarting bot..."
sudo supervisorctl restart asblox-bot

echo "✅ Bot updated and restarted!"
echo "ℹ️  Check status with: sudo supervisorctl status asblox-bot"
