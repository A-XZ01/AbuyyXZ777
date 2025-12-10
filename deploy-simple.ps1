# Simple Deploy Script
Write-Host "Deploying to DigitalOcean..." -ForegroundColor Cyan

try {
    # Git commands
    Write-Host "1. Staging changes..." -ForegroundColor Yellow
    git add -A
    if ($LASTEXITCODE -ne 0) { throw "Git add failed" }
    
    Write-Host "2. Committing changes..." -ForegroundColor Yellow
    git commit -m "update bot"
    if ($LASTEXITCODE -ne 0) { throw "Git commit failed" }
    
    Write-Host "3. Pushing to GitHub..." -ForegroundColor Yellow
    git push origin main
    if ($LASTEXITCODE -ne 0) { throw "Git push failed" }
    
    Write-Host "4. Deploying to server..." -ForegroundColor Yellow
    ssh root@159.223.71.87 "cd /root/AbuyyXZ777; git pull; supervisorctl restart discordbot; sleep 2; supervisorctl status discordbot"
    if ($LASTEXITCODE -ne 0) { throw "SSH deployment failed" }
    
    Write-Host "Done! Bot deployed successfully." -ForegroundColor Green
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    exit 1
}
