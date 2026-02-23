# ========================================
# SSH 密钥认证自动化脚本
# ========================================
# 作者：JARVIS
# 创建时间：2026-02-13
# 说明：使用 Windows OpenSSH 密钥认证
# ========================================

param(
    [string]$Server = "47.97.113.144",
    [int]$Port = 222,
    [string]$Username = "root",
    [string]$KeyPath = "$env:USERPROFILE\.ssh\id_rsa",
    [string]$Command = ""
)

# ========================================
# 函数：使用密钥认证 SSH 连接
# ========================================
function Invoke-SSHKeyAuth {
    param(
        [string]$Server,
        [int]$Port,
        [string]$Username,
        [string]$KeyPath,
        [string]$Command
    )
    
    # 检查私钥文件
    if (-Not (Test-Path $KeyPath)) {
        Write-Host "❌ 找不到私钥文件：$KeyPath" -ForegroundColor Red
        Write-Host "`n生成密钥命令：" -ForegroundColor Yellow
        Write-Host "ssh-keygen -t rsa -b 4096 -f $KeyPath" -ForegroundColor Cyan
        exit 1
    }
    
    Write-Host "`n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host " SSH 密钥认证连接" -ForegroundColor Cyan
    Write-Host " 服务器：$Server`:$Port" -ForegroundColor Cyan
    Write-Host " 密钥：$KeyPath" -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━`n" -ForegroundColor Cyan
    
    # 执行 SSH 连接
    $sshCmd = "ssh -i $KeyPath -p $Port $Username@$Server"
    
    if ([string]::IsNullOrEmpty($Command)) {
        # 交互式连接
        Invoke-Expression $sshCmd
    } else {
        # 执行命令
        $fullCmd = "$sshCmd `"$Command`""
        Invoke-Expression $fullCmd
    }
}

# ========================================
# 函数：复制公钥到服务器
# ========================================
function Copy-SSHPublicKey {
    param(
        [string]$Server,
        [int]$Port,
        [string]$Username,
        [string]$KeyPath
    )
    
    $pubKeyPath = "$KeyPath.pub"
    
    if (-Not (Test-Path $pubKeyPath)) {
        Write-Host "❌ 找不到公钥文件：$pubKeyPath" -ForegroundColor Red
        exit 1
    }
    
    # 读取公钥内容
    $pubKey = Get-Content $pubKeyPath
    
    Write-Host "`n正在复制公钥到服务器..." -ForegroundColor Green
    Write-Host "公钥内容：$pubKey`n" -ForegroundColor Cyan
    
    # 使用 ssh-copy-id（如果可用）或手动复制
    Write-Host "请在服务器上执行以下命令：" -ForegroundColor Yellow
    Write-Host "`n  mkdir -p ~/.ssh" -ForegroundColor White
    Write-Host "  chmod 700 ~/.ssh" -ForegroundColor White
    Write-Host "  echo `"$pubKey`" >> ~/.ssh/authorized_keys" -ForegroundColor White
    Write-Host "  chmod 600 ~/.ssh/authorized_keys`n" -ForegroundColor White
}

# ========================================
# 主程序
# ========================================

# 检查是否安装了 OpenSSH
$sshCheck = Get-Command ssh -ErrorAction SilentlyContinue
if (-Not $sshCheck) {
    Write-Host "❌ 系统未安装 OpenSSH 客户端" -ForegroundColor Red
    Write-Host "安装命令：" -ForegroundColor Yellow
    Write-Host "Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Cyan
    exit 1
}

# 执行连接或复制密钥
if ($args -contains "--copy-key") {
    Copy-SSHPublicKey -Server $Server -Port $Port -Username $Username -KeyPath $KeyPath
} else {
    Invoke-SSHKeyAuth -Server $Server -Port $Port -Username $Username -KeyPath $KeyPath -Command $Command
}

Write-Host "`n✅ 完成！" -ForegroundColor Green
