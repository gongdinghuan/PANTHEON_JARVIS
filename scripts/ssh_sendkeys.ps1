# SSH自动密码输入脚本 (PowerShell SendKeys)
# 使用SendKeys自动输入SSH密码

Add-Type -AssemblyName System.Windows.Forms

$server = "47.97.113.144"
$port = "222"
$user = "root"
$password = "zXc363324112"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SSH Auto-Password Connector" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: $server:$port" -ForegroundColor Yellow
Write-Host "User: $user" -ForegroundColor Yellow
Write-Host "Password: ********" -ForegroundColor Yellow
Write-Host ""

# 启动SSH进程
Write-Host "Starting SSH connection..." -ForegroundColor Green

$sshProcess = Start-Process -FilePath "ssh" -ArgumentList "-o StrictHostKeyChecking=no -p $port $user@$server" -PassThru -NoNewWindow

# 等待3秒让SSH启动
Start-Sleep -Seconds 3

# 检查进程是否还在运行
if (!$sshProcess.HasExited) {
    Write-Host "SSH process is running, sending password..." -ForegroundColor Green
    
    # 发送密码并回车
    [System.Windows.Forms.SendKeys]::SendWait($password)
    Start-Sleep -Milliseconds 100
    [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
    
    Write-Host "Password sent!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You should now be connected to the server." -ForegroundColor Cyan
    Write-Host "Check the SSH window for the command prompt." -ForegroundColor Cyan
} else {
    Write-Host "SSH process exited unexpectedly." -ForegroundColor Red
    Write-Host "The connection may have failed." -ForegroundColor Red
}

Write-Host ""
Write-Host "Press Ctrl+C to exit (SSH window will remain open)"
Write-Host ""

# 保持脚本运行，不关闭SSH连接
while (!$sshProcess.HasExited) {
    Start-Sleep -Seconds 1
}
