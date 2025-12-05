# ============================================
# Bot Status Checker
# ============================================
# Cek status bot di DigitalOcean
# Usage: .\check-bot.ps1
# ============================================

Write-Host "🔍 Checking bot status on DigitalOcean..." -ForegroundColor Cyan
Write-Host ""

$sshCommand = "echo 'BOT STATUS:' && supervisorctl status discordbot && echo '' && echo 'LAST 20 LOG LINES:' && tail -20 /var/log/discordbot.out.log"

ssh root@159.223.71.87 $sshCommand
