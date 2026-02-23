# 自动配置SSH密钥认证
$ErrorActionPreference = "Stop"

# 配置参数
$Server = "47.97.113.144"
$Port = "222"
$User = "root"
$Password = "zXc363324112"
$KeyPath = "C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa"

# 公钥内容（从私钥导出）
$PublicKey = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCyB43w7qybi60hNX2e7hx5G28wKX7ZFzH9Qqo4vOKwNaBQeEHy7+mfXC94a8TXnBJEvO5IIgYQqsVy/Sd9HUqG7yJenSK6WnEKEfeBkIolF2gTMOVqEAfuMXd76urBDjGv25K8XhQYv3puZB2whUCKg2zMULK7j7FRs2kfOGr29MVvQlLr5F9x0jT8j5SrQMIFA1Qmhvv+yRyPHjtK7/ND7XhdDS7jtDPJNUmjEx9QwXMNnKk51jFH6nb4hRxZFGHOY6MuwPghHFjvFCV7XgjDHtCCLMbuovFadYbMihrd7EMbhx+g62guh4NgiMS1ytC8xTL1E9rtVpnBaKYTHxF85Rd1ulvVjbtsxx7cafNAXPA7KiJjJbEzRGpFY8KUmDGcVsDy0rcGXnKCR5U9nr+kT5RkXHfBz7SliIxLZsW9Cv0bVYIpkJN8AqW9hJStcwnVFAqFavWzc8vgZ3pojm9qLY1srV5wLLdAjhH99dg9AzRoJaPA+tEYNkPOhEoMnQirgTwd5pINLYfGUf+0p0KKt5AYlxqoNpiYnrTxz5AgThAxMpc9JFpzDMXCLN4sOn8nbk774dX82ssWo9UDCS1Q325ah4nU+mhby2ACcXMnLXjMOcx+ATWDCq4K9UF3vi4LIJa1YNBtTYBi8cEzTacig4ODN4rMHIAxrD5YrZSvew== gong363324112@qq.com"

# 颜色输出
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

Write-ColorOutput Cyan "========================================"
Write-ColorOutput Cyan "  自动配置SSH密钥认证"
Write-ColorOutput Cyan "========================================"
Write-Output ""

# Step 1: 使用密码登录并配置服务器
Write-ColorOutput Yellow "📡 步骤1: 使用密码登录服务器..."
Write-ColorOutput Yellow "🔧 步骤2: 配置SSH密钥认证..."

# 创建临时期望脚本用于自动化登录
$ExpScript = @"
#!/usr/bin/expect -f
set timeout 30
spawn ssh -p $port $user@$server
expect {
    "yes/no" { send "yes\r"; exp_continue }
    "password:" { send "$password\r" }
}
expect "#"
send "mkdir -p ~/.ssh\r"
expect "#"
send "chmod 700 ~/.ssh\r"
expect "#"
send "echo '$PublicKey' >> ~/.ssh/authorized_keys\r"
expect "#"
send "chmod 600 ~/.ssh/authorized_keys\r"
expect "#"
send "systemctl restart sshd\r"
expect "#"
send "echo '配置完成！密钥已添加到服务器'\r"
expect "#"
exit
"@

$ExpScriptPath = "$env:TEMP\setup_ssh_key.exp"
$ExpScript | Out-File -FilePath $ExpScriptPath -Encoding ASCII

# Step 2: 使用expect脚本自动配置
Write-Output ""
Write-ColorOutput Yellow "🚀 正在自动配置服务器..."

try {
    $result = & expect $ExpScriptPath 2>&1
    Write-Output $result
    Write-ColorOutput Green "✅ 密钥配置成功！"
} catch {
    Write-ColorOutput Red "❌ 自动配置失败，请使用手动方式"
}

# Step 3: 测试密钥登录
Write-Output ""
Write-ColorOutput Yellow "🔑 步骤3: 测试密钥登录..."
Write-Output ""

Start-Sleep -Seconds 2

try {
    $testResult = ssh -i $KeyPath -p $Port -o StrictHostKeyChecking=no -o ConnectTimeout=10 "$User@$Server" "echo '✅ 密钥登录成功！' && uname -a" 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput Green "✅ 密钥登录测试成功！"
        Write-Output $testResult
        
        # Step 4: 执行运维命令
        Write-Output ""
        Write-ColorOutput Cyan "========================================"
        Write-ColorOutput Cyan "  开始执行运维命令"
        Write-ColorOutput Cyan "========================================"
        Write-Output ""
        
        $Commands = @(
            "echo '=== 1. 系统信息 ==='",
            "uname -a && uptime",
            "",
            "echo '=== 2. 内存使用 ==='",
            "free -h",
            "",
            "echo '=== 3. 磁盘使用 ==='",
            "df -h",
            "",
            "echo '=== 4. 系统负载 ==='",
            "top -bn1 | head -15",
            "",
            "echo '=== 5. 网络连接 ==='",
            "ss -tulnp | head -20",
            "",
            "echo '=== 6. SSH服务状态 ==='",
            "systemctl status sshd | head -10"
        )
        
        foreach ($cmd in $Commands) {
            if ($cmd -ne "") {
                ssh -i $KeyPath -p $Port -o StrictHostKeyChecking=no "$User@$Server" "$cmd"
                if ($LASTEXITCODE -ne 0) {
                    Write-ColorOutput Red "❌ 命令执行失败: $cmd"
                }
            } else {
                Write-Output ""
            }
        }
        
        Write-Output ""
        Write-ColorOutput Green "✅ 所有运维任务完成！"
        
    } else {
        Write-ColorOutput Red "❌ 密钥登录测试失败"
        Write-Output $testResult
        Write-ColorOutput Yellow "💡 可能原因："
        Write-Output "   1. 服务器未正确配置公钥"
        Write-Output "   2. SSH服务未重启"
        Write-Output "   3. 权限设置不正确"
    }
} catch {
    Write-ColorOutput Red "❌ 密钥登录测试异常: $_"
}

Write-Output ""
Write-ColorOutput Cyan "========================================"
