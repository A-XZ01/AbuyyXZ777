#!/bin/bash
# Force restart ASBLOX bot on DigitalOcean

echo "🔄 Restarting ASBLOX bot with latest code..."
echo ""

# Pull latest code
echo "1️⃣  Pulling latest code from GitHub..."
cd /home/botuser/AbuyyXZ777
git pull origin main

# Force stop bot
echo ""
echo "2️⃣  Stopping bot (force)..."
sudo supervisorctl stop asblox-bot
sleep 2

# Make sure it's stopped
echo ""
echo "3️⃣  Checking if bot is fully stopped..."
sleep 2

# Start bot
echo ""
echo "4️⃣  Starting bot with fresh code..."
sudo supervisorctl start asblox-bot
sleep 3

# Check status
echo ""
echo "5️⃣  Bot status:"
sudo supervisorctl status asblox-bot

echo ""
echo "✅ Done! Bot restarted with latest code."
echo ""
echo "💡 If you still see errors, check logs with:"
echo "   sudo tail -f /var/log/asblox/bot.log"
