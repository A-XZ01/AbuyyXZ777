# Check Bot Status on DigitalOcean
# Usage: .\check-bot.ps1

Write-Host "Checking bot status..." -ForegroundColor Cyan
Write-Host ""

$cmd = "supervisorctl status discordbot; tail -20 /var/log/discordbot.out.log"
ssh root@159.223.71.87 $cmd
