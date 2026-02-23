# PowerShell 自动化运维脚本
# 目标服务器: 47.97.113.144:22
# 账号: root / 密码: zXc363324112

Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  开始服务器运维任务" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host ""

$opsCommands = @'
echo "=== 服务器基础信息 ==="
uname -a
uptime
echo ""
echo "=== 系统版本 ==="
cat /etc/os-release | head -5
echo ""
echo "=== 内存使用情况 ==="
free -h
echo ""
echo "=== 磁盘使用情况 ==="
df -h
echo ""
echo "=== CPU负载 ==="
top -bn1 | head -15
echo ""
echo "=== 网络连接 ==="
ss -tulnp | head -20
echo ""
echo "=== SSH服务状态 ==="
systemctl status sshd | head -10
echo ""
echo "=== 运行中的服务 ==="
systemctl list-units --type=service --state=running | head -20
echo ""
echo "=== 在线用户 ==="
who -a
echo ""
echo "=== 最近登录 ==="
last -n 10
echo ""
echo "=== 防火墙状态 ==="
firewall-cmd --list-all 2>/dev/null || iptables -L -n | head -20
echo ""
echo "=== 系统日志（最后20行） ==="
journalctl -xe --no-pager | tail -20
'@

$tempScript = "$env:TEMP\server_ops_$(Get-Date -Format 'yyyyMMddHHmmss').sh"
$opsCommands | Out-File -FilePath $tempScript -Encoding UTF8

Write-Host "[√] 运维脚本已创建: $tempScript" -ForegroundColor Green
Write-Host ""
Write-Host "======================================================" -ForegroundColor Yellow
Write-Host "  快速开始" -ForegroundColor Yellow
Write-Host "======================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "请打开CMD或PowerShell，执行以下命令：" -ForegroundColor Cyan
Write-Host ""
Write-Host "  ssh root@47.97.113.144" -ForegroundColor Yellow
Write-Host ""
Write-Host "然后输入密码: zXc363324112" -ForegroundColor Yellow
Write-Host ""
Write-Host "登录成功后，复制以下命令执行：" -ForegroundColor Cyan
Write-Host ""
Write-Host $opsCommands
Write-Host ""
