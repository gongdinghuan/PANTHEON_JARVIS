# SSH自动密码输入脚本 (修复版)
# SSH在新窗口运行，SendKeys自动输入密码

Add-Type -AssemblyName System.Windows.Forms

$server = "47.97.113.144"
$port = "222"
$user = "root"
$password = "zXc363324112"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  SSH Auto-Password Connector (Fixed)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Server: ${server}:${port}" -ForegroundColor Yellow
Write-Host "User: $user" -ForegroundColor Yellow
Write-Host "Password: ********" -ForegroundColor Yellow
Write-Host ""

# 检查ssh命令是否可用
try {
    $null = Get-Command ssh -ErrorAction Stop
    Write-Host "✓ SSH command found" -ForegroundColor Green
} catch {
    Write-Host "✗ SSH command not found. Please install OpenSSH Client." -ForegroundColor Red
    exit 1
}

# 启动SSH进程（在新窗口）
Write-Host "Starting SSH connection in new window..." -ForegroundColor Green

# 使用WindowStyle=Normal在新窗口启动SSH
$sshProcess = Start-Process -FilePath "ssh" `
    -ArgumentList "-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -p $port $user@$server" `
    -PassThru `
    -WindowStyle Normal

# 等待窗口启动和SSH初始化
Write-Host "Waiting for SSH window to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 4

# 检查进程是否还在运行
if (!$sshProcess.HasExited) {
    Write-Host "✓ SSH process is running" -ForegroundColor Green
    Write-Host "Sending password..." -ForegroundColor Green
    
    try {
        # 激活SSH窗口
        $sshProcess.MainWindowHandle
        [System.Windows.Forms.SendKeys]::SendWait($password)
        Start-Sleep -Milliseconds 200
        [System.Windows.Forms.SendKeys]::SendWait("{ENTER}")
        
        Write-Host "✓ Password sent!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Check the SSH window for the command prompt." -ForegroundColor Cyan
    } catch {
        Write-Host "✗ Error sending password: $_" -ForegroundColor Red
        Write-Host "Please manually enter the password in the SSH window." -ForegroundColor Yellow
    }
} else {
    Write-Host "✗ SSH process exited unexpectedly." -ForegroundColor Red
    Write-Host "Possible reasons:" -ForegroundColor Yellow
    Write-Host "  - Port $port is not accessible" -ForegroundColor Yellow
    Write-Host "  - SSH server is not running" -ForegroundColor Yellow
    Write-Host "  - Network connection failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Press Ctrl+C to exit (SSH window will remain open)" -ForegroundColor Cyan
Write-Host ""

# 保持脚本运行
try {
    while (!$sshProcess.HasExited) {
        Start-Sleep -Seconds 1
    }
} catch [System.Management.Automation.PipelineStoppedException] {
    # 用户按了Ctrl+C
    Write-Host "`nExiting..." -ForegroundColor Cyan
}
