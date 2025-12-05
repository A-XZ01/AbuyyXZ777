# ============================================
# Auto Deploy Script ke DigitalOcean
# ============================================
# Usage: .\deploy.ps1 "commit message"
# Example: .\deploy.ps1 "fix bug"
# ============================================

param(
    [string]$message = "update bot"
)

Write-Host "🚀 Starting deployment..." -ForegroundColor Cyan
Write-Host ""

# 1. Git Add All
Write-Host "📦 Adding files to git..." -ForegroundColor Yellow
git add .

# 2. Git Commit
Write-Host "💾 Committing changes: $message" -ForegroundColor Yellow
git commit -m $message

# 3. Git Push
Write-Host "⬆️  Pushing to GitHub..." -ForegroundColor Yellow
git push origin main

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Git push failed!" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Code pushed to GitHub" -ForegroundColor Green
Write-Host ""

# 4. SSH ke DigitalOcean & Update
Write-Host "🔄 Deploying to DigitalOcean..." -ForegroundColor Cyan

$sshCommand = "cd /root/AbuyyXZ777 && git pull origin main && supervisorctl restart discordbot && echo 'Bot restarted successfully' && supervisorctl status discordbot"

ssh root@159.223.71.87 $sshCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "🎉 DEPLOYMENT SUCCESS!" -ForegroundColor Green
    Write-Host "✅ Code updated on server" -ForegroundColor Green
    Write-Host "✅ Bot restarted" -ForegroundColor Green
    Write-Host ""
    Write-Host "Check your Discord bot - it should be running with latest code!" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    Write-Host "Check the error messages above." -ForegroundColor Yellow
}
