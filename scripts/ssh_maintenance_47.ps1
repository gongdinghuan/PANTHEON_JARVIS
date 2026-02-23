# SSH Automated Maintenance Script for 47.97.113.144
# Created by JARVIS - 2026-02-13

param(
    [string]$Server = "47.97.113.144",
    [int]$Port = 222,
    [string]$Username = "root",
    [string]$Password = "zXc363324112"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SSH Automated Connection Script" -ForegroundColor Cyan
Write-Host "  Created by JARVIS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Target Server:" -ForegroundColor Yellow
Write-Host "  IP: $Server" -ForegroundColor White
Write-Host "  Port: $Port" -ForegroundColor White
Write-Host "  User: $Username" -ForegroundColor White
Write-Host ""

# Check if plink is available
$plinkPaths = @(
    "C:\Program Files\PuTTY\plink.exe",
    "C:\Program Files (x86)\PuTTY\plink.exe",
    "$env:LOCALAPPDATA\Programs\PuTTY\plink.exe"
)

$plinkExe = $null
foreach ($path in $plinkPaths) {
    if (Test-Path $path) {
        $plinkExe = $path
        break
    }
}

if ($plinkExe) {
    Write-Host "Using plink: $plinkExe" -ForegroundColor Green
    Write-Host ""
    
    # Define commands to run on remote server
    $commands = @"
echo '========================================'
echo '  System Information'
echo '========================================'
echo ''
echo 'Date:'
date
echo ''
echo 'Uptime:'
uptime
echo ''
echo 'Hostname:'
hostname
echo ''
echo 'Kernel:'
uname -r
echo ''
echo '========================================'
echo '  CPU Usage'
echo '========================================'
top -bn1 | head -20
echo ''
echo '========================================'
echo '  Memory Usage'
echo '========================================'
free -h
echo ''
echo '========================================'
echo '  Disk Usage'
echo '========================================'
df -h
echo ''
echo '========================================'
echo '  Network Status'
echo '========================================'
netstat -tunlp | head -20
echo ''
echo '========================================'
echo '  Running Services'
echo '========================================'
systemctl list-units --type=service --state=running | head -20
echo ''
"@

    # Execute commands using plink
    Write-Host "Executing remote commands..." -ForegroundColor Cyan
    & $plinkExe -P $Port -pw $Password -batch "$Username@$Server" $commands
    
} else {
    Write-Host "plink not found. Using Windows OpenSSH..." -ForegroundColor Yellow
    Write-Host ""
    
    # For Windows OpenSSH, we need to manually enter password
    Write-Host "Please enter password when prompted: $Password" -ForegroundColor Yellow
    Write-Host ""
    
    # Create a temporary script file
    $tempScript = "$env:TEMP\ssh_commands_$(Get-Date -Format 'yyyyMMddHHmmss').sh"
    @"
echo '========================================'
echo '  System Information'
echo '========================================'
echo ''
echo 'Date:'
date
echo ''
echo 'Uptime:'
uptime 2>/dev/null || echo 'uptime command not available'
echo ''
echo 'Hostname:'
hostname
echo ''
echo 'Kernel:'
uname -r
echo ''
echo '========================================'
echo '  CPU Usage'
echo '========================================'
top -bn1 | head -20
echo ''
echo '========================================'
echo '  Memory Usage'
echo '========================================'
free -h
echo ''
echo '========================================'
echo '  Disk Usage'
echo '========================================'
df -h
echo ''
echo '========================================'
echo '  Network Status'
echo '========================================'
netstat -tunlp | head -20
echo ''
echo '========================================'
echo '  Running Services'
echo '========================================'
systemctl list-units --type=service --state=running | head -20
echo ''
"@ | Out-File -FilePath $tempScript -Encoding UTF8
    
    # Copy script to remote server and execute
    Write-Host "Copying script to remote server..." -ForegroundColor Cyan
    
    # Note: This requires manual password entry
    scp -P $Port $tempScript "$Username@${Server}:/tmp/system_check.sh" 2>$null
    
    # Execute the script
    ssh -p $Port "$Username@$Server" "bash /tmp/system_check.sh; rm -f /tmp/system_check.sh"
    
    # Clean up
    Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Maintenance Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
