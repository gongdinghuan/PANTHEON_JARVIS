# SSH Connection Script for 47.97.113.144
# Created by JARVIS - 2026-02-13

# Server Connection Parameters
$Server = "47.97.113.144"
$Port = "222"
$Username = "root"
$Password = "zXc363324112"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SSH Connection to 47.97.113.144" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Server: $Server" -ForegroundColor Yellow
Write-Host "Port: $Port" -ForegroundColor Yellow
Write-Host "User: $Username" -ForegroundColor Yellow
Write-Host ""
Write-Host "Connecting..." -ForegroundColor Green

# Using plink if available
$plinkPath = "C:\Program Files\PuTTY\plink.exe"
if (Test-Path $plinkPath) {
    Write-Host "Using plink..." -ForegroundColor Cyan
    & $plinkPath -P $Port -pw $Password "$Username@$Server"
} else {
    # Using Windows OpenSSH
    Write-Host "Using Windows OpenSSH..." -ForegroundColor Cyan
    Write-Host "Note: Windows ssh may ask for password interactively" -ForegroundColor Yellow
    
    # Create temporary password file for sshpass-like functionality
    # Unfortunately, Windows ssh doesn't support password in command line
    # We'll use the standard ssh command which will prompt for password
    ssh -p $Port "$Username@$Server"
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Connection Closed" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
