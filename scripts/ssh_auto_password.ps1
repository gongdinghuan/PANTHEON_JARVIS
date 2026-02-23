# SSH自动密码连接脚本 (PowerShell)
# 需要安装 plink (PuTTY命令行工具)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SSH Connection to 47.97.113.144" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$server = "47.97.113.144"
$port = "222"
$user = "root"
$password = "zXc363324112"

Write-Host "Server: $server" -ForegroundColor Yellow
Write-Host "Port: $port" -ForegroundColor Yellow
Write-Host "User: $user" -ForegroundColor Yellow
Write-Host "Password: ********" -ForegroundColor Yellow
Write-Host ""

# 检查plink是否安装
$plinkPath = Get-Command plink -ErrorAction SilentlyContinue

if ($plinkPath) {
    Write-Host "Using plink with auto-password..." -ForegroundColor Green
    
    # 使用plink连接（自动输入密码）
    & plink -ssh -P $port -pw $password "$user@$server"
    
} else {
    Write-Host "⚠ Plink not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Installing PuTTY/plink..." -ForegroundColor Yellow
    
    # 尝试使用winget安装
    winget install --id PuTTY.PuTTY --accept-source-agreements --accept-package-agreements 2>$null
    
    Write-Host ""
    Write-Host "Please install PuTTY from:" -ForegroundColor Cyan
    Write-Host "https://www.chiark.greenend.org.uk/~sgtatham/putty/" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
