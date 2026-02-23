# SSH密钥登录并执行运维命令
$ErrorActionPreference = "Stop"

# 配置信息
$Server = "47.97.113.144"
$Port = "222"
$User = "root"
$KeyPath = "C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa"

# 颜色输出函数
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Cyan "========================================"
Write-ColorOutput Cyan "  使用SSH密钥登录并执行运维命令"
Write-ColorOutput Cyan "========================================"
Write-Output ""

# 检查密钥文件
if (-not (Test-Path $KeyPath)) {
    Write-ColorOutput Red "❌ 密钥文件不存在: $KeyPath"
    exit 1
}

Write-ColorOutput Green "✅ 密钥文件找到"

# 运维命令集合
$Commands = @(
    "echo '=== 1. 系统基础信息 ==='",
    "uname -a",
    "cat /etc/os-release | head -3",
    "uptime",
    "",
    "echo '=== 2. CPU使用率 ==='",
    "top -bn1 | head -15",
    "",
    "echo '=== 3. 内存使用情况 ==='",
    "free -h",
    "",
    "echo '=== 4. 磁盘使用情况 ==='",
    "df -h",
    "",
    "echo '=== 5. 网络连接状态 ==='",
    "ss -tulnp | head -20",
    "",
    "echo '=== 6. 运行中的服务 ==='",
    "systemctl list-units --type=service --state=running | head -15",
    "",
    "echo '=== 7. SSH服务状态 ==='",
    "systemctl status sshd | head -10",
    "",
    "echo '=== 8. 在线用户 ==='",
    "who -a",
    "",
    "echo '=== 9. 最近登录记录 ==='",
    "last -n 10",
    "",
    "echo '=== 10. 系统日志（最近30行） ==='",
    "journalctl -xe --no-pager | tail -30"
)

# 执行远程命令
Write-Output ""
Write-ColorOutput Yellow "🚀 正在连接服务器并执行运维命令..."
Write-Output ""

foreach ($cmd in $Commands) {
    if ($cmd -ne "") {
        ssh -i $KeyPath -p $Port -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$User@$Server" "$cmd"
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput Red "❌ 命令执行失败: $cmd"
        }
    } else {
        Write-Output ""
    }
    Start-Sleep -Milliseconds 100
}

Write-Output ""
Write-ColorOutput Green "✅ 运维命令执行完成！"
