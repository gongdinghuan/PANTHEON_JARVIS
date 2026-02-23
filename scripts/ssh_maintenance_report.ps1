# SSH Server Maintenance Report
$server = "47.97.113.144"
$port = "222"
$user = "root"
$output = "C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\reports\server_maintenance_47.txt"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Server Maintenance Report" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan

# Commands
$commands = @'
echo "========================================="
echo "        Server Maintenance Report"
echo "========================================="
echo ""
echo "=== 1. System Info ==="
uname -a
cat /etc/os-release | head -5
uptime

echo -e "\n=== 2. System Load ==="
top -bn1 | head -15

echo -e "\n=== 3. Memory Usage ==="
free -h

echo -e "\n=== 4. Disk Usage ==="
df -h

echo -e "\n=== 5. Network Connections ==="
ss -tulnp | head -20

echo -e "\n=== 6. SSH Service Status ==="
systemctl status sshd | head -15

echo -e "\n=== 7. Running Services ==="
systemctl list-units --type=service --state=running --no-pager | head -20

echo -e "\n=== 8. Online Users ==="
who -a

echo -e "\n=== 9. Login History ==="
last -n 10 | head -15

echo -e "\n=== 10. System Log ==="
journalctl -xe --no-pager | tail -20

echo -e "\n=== 11. Process Info ==="
ps aux --sort=-%cpu | head -20
'@

# Check plink
$plinkPath = "C:\Program Files\PuTTY\plink.exe"
if (-not (Test-Path $plinkPath)) {
    $plinkPath = "C:\Program Files (x86)\PuTTY\plink.exe"
}

if (Test-Path $plinkPath) {
    Write-Host "Using plink..." -ForegroundColor Green
    $commands | & $plinkPath -ssh -P $port -l $user -pw "zXc363324112" $server 2>&1 | Out-File -FilePath $output -Encoding UTF8
} else {
    Write-Host "Using OpenSSH..." -ForegroundColor Yellow
    $commands | ssh -p $port ${user}@${server} 2>&1 | Out-File -FilePath $output -Encoding UTF8
}

Write-Host "Reading report..." -ForegroundColor Yellow

# Read report
if (Test-Path $output) {
    Get-Content $output -Encoding UTF8
} else {
    Write-Host "Report not found" -ForegroundColor Red
}
