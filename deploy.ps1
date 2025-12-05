# Auto Deploy Script ke DigitalOcean
# Usage: .\deploy.ps1 "commit message"

param([string]$message = "update bot")

Write-Host "Starting deployment..." -ForegroundColor Cyan
Write-Host ""

Write-Host "Adding files to git..." -ForegroundColor Yellow
git add .

Write-Host "Committing changes: $message" -ForegroundColor Yellow
git commit -m $message

Write-Host "Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "Git push failed!" -ForegroundColor Red
    exit 1
}

Write-Host "Code pushed to GitHub" -ForegroundColor Green
Write-Host ""

Write-Host "Deploying to DigitalOcean..." -ForegroundColor Cyan
$cmd = "cd /root/AbuyyXZ777; git pull origin main; supervisorctl restart discordbot; supervisorctl status discordbot"
ssh root@159.223.71.87 $cmd

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "DEPLOYMENT SUCCESS!" -ForegroundColor Green
} else {
    Write-Host "Deployment failed!" -ForegroundColor Red
}
