# Quick Deploy (No Commit Message Required)
# Usage: .\quick-deploy.ps1

Write-Host "Quick Deploy Mode" -ForegroundColor Cyan
Write-Host ""

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$message = "Quick update - $timestamp"

& "$PSScriptRoot\deploy.ps1" -message $message
