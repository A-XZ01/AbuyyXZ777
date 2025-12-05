# Simple Deploy Script
Write-Host "Deploying to DigitalOcean..." -ForegroundColor Cyan

# Git commands
git add .
git commit -m "update bot"
git push origin main

# SSH deploy
ssh root@159.223.71.87 "cd /root/AbuyyXZ777; git pull; supervisorctl restart discordbot; supervisorctl status discordbot"

Write-Host "Done!" -ForegroundColor Green
