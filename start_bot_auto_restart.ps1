# ASBLOX Discord Bot - Auto Restart
# Double-click file ini untuk jalankan bot dengan auto-restart

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   ASBLOX Discord Bot (Auto-Restart)   " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$restartCount = 0

while ($true) {
    $restartCount++
    
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] " -NoNewline -ForegroundColor Yellow
    Write-Host "Starting bot... (Run #$restartCount)" -ForegroundColor Green
    Write-Host ""
    
    # Jalankan bot
    python bot.py
    
    Write-Host ""
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] " -NoNewline -ForegroundColor Yellow
    Write-Host "Bot stopped! Auto-restart in 5 seconds..." -ForegroundColor Red
    Write-Host "Press Ctrl+C to exit" -ForegroundColor Gray
    Write-Host ""
    
    Start-Sleep -Seconds 5
}
