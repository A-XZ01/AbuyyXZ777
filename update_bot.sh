#!/bin/bash
# Update ASBLOX Bot dari GitHub

echo "🔄 Updating bot from GitHub..."
cd /home/botuser/AbuyyXZ777

# Pull latest changes
git pull origin main

# Restart bot
echo "▶️ Restarting bot..."
sudo supervisorctl restart asblox-bot

# Wait & check status
sleep 2
echo ""
echo "✅ Bot status:"
sudo supervisorctl status asblox-bot

echo ""
echo "✅ Update complete!"
echo "Command '/add' is now ADMIN ONLY"
