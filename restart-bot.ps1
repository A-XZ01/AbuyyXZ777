# Restart Bot on DigitalOcean
# Usage: .\restart-bot.ps1

Write-Host "Restarting bot..." -ForegroundColor Cyan
Write-Host ""

$cmd = "supervisorctl restart discordbot; supervisorctl status discordbot"
ssh root@159.223.71.87 $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Bot restarted successfully!" -ForegroundColor Green
}
