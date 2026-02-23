# SSH远程运维脚本
Add-Type -AssemblyName System.Windows.Forms

$Server = "47.97.113.144"
$Port = "222"
$User = "root"
$Password = "zXc363324112"

Write-Host "`n[INFO] 正在连接到 $Server:$Port ..." -ForegroundColor Cyan

# 构建SSH命令
$Commands = @(
    "uname -a",
    "uptime",
    "echo '=== MEMORY ==='",
    "free -h",
    "echo '=== DISK ==='",
    "df -h",
    "echo '=== LOAD ==='",
    "top -bn1 | head -15",
    "echo '=== NETWORK ==='",
    "ss -tulnp | head -20",
    "echo '=== SERVICES ==='",
    "systemctl list-units --type=service --state=running | head -20",
    "echo '=== SSH STATUS ==='",
    "systemctl status sshd | head -10"
)

$ScriptBlock = $Commands -join " && "

# 使用SSH执行
$Result = & ssh -p $Port -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null ${User}@${Server} $ScriptBlock 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[SUCCESS] 命令执行成功！" -ForegroundColor Green
    Write-Host "`n$Result"
    
    # 保存结果
    $OutputPath = "C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\reports\server_ops_result.txt"
    $Result | Out-File -FilePath $OutputPath -Encoding UTF8
    Write-Host "`n[INFO] 结果已保存到: $OutputPath" -ForegroundColor Yellow
} else {
    Write-Host "`n[ERROR] 命令执行失败！" -ForegroundColor Red
    Write-Host "`n$Result"
}

Write-Host "`n按任意键退出..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
