# ============================================
# Bot Restart Script
# ============================================
# Restart bot tanpa update code
# Usage: .\restart-bot.ps1
# ============================================

Write-Host "🔄 Restarting bot on DigitalOcean..." -ForegroundColor Cyan
Write-Host ""

$sshCommand = "supervisorctl restart discordbot && echo 'Bot restarted successfully' && supervisorctl status discordbot"

ssh root@159.223.71.87 $sshCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Bot restarted successfully!" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "❌ Restart failed!" -ForegroundColor Red
}
