# =====================================================
# JARVIS SSH Linux 运维工具包 v2.0
# 学习日期: 2025-02-13
# 功能: Windows SSH Linux 自动化运维
# =====================================================

param(
    [string]$Server = "47.97.113.144",
    [int]$Port = 222,
    [string]$User = "root",
    [string]$Password = "zXc363324112",
    [string]$Command = "",
    [switch]$InstallPlink,
    [switch]$GenerateKey,
    [switch]$Help
)

# =====================================================
# 颜色输出函数
# =====================================================
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { param([string]$Msg) Write-ColorOutput "✅ $Msg" "Green" }
function Write-Error { param([string]$Msg) Write-ColorOutput "❌ $Msg" "Red" }
function Write-Warning { param([string]$Msg) Write-ColorOutput "⚠️  $Msg" "Yellow" }
function Write-Info { param([string]$Msg) Write-ColorOutput "ℹ️  $Msg" "Cyan" }

# =====================================================
# 1. OpenSSH 连接 (Windows 内置)
# =====================================================
function Connect-OpenSSH {
    Write-Info "使用 Windows OpenSSH 连接到 $Server`:$Port"
    Write-Info "用户: $User"
    Write-Info "命令: ssh -p $Port $User@$Server"
    Write-Warning "需要手动输入密码"
    
    ssh -p $Port $User@$Server $Command
}

# =====================================================
# 2. plink 自动化 (需要安装)
# =====================================================
function Connect-Plink {
    Write-Info "使用 plink 自动化连接"
    
    $plinkPaths = @(
        "C:\Program Files\PuTTY\plink.exe",
        "C:\Program Files (x86)\PuTTY\plink.exe",
        "$env:USERPROFILE\Desktop\putty\plink.exe"
    )
    
    $plink = $null
    foreach ($path in $plinkPaths) {
        if (Test-Path $path) {
            $plink = $path
            break
        }
    }
    
    if (-not $plink) {
        Write-Error "未找到 plink.exe"
        Write-Info "请运行: .\ssh_linux_toolkit.ps1 -InstallPlink"
        return
    }
    
    Write-Success "找到 plink: $plink"
    
    if ($Command) {
        Write-Info "执行远程命令: $Command"
        & $plink -ssh -P $Port -l $User -pw $Password $Server $Command
    } else {
        Write-Info "启动交互式会话"
        & $plink -ssh -P $Port -l $User -pw $Password $Server
    }
}

# =====================================================
# 3. 生成 SSH 密钥对
# =====================================================
function New-SSHKeyPair {
    Write-Info "生成 SSH 密钥对..."
    
    $keyPath = "$env:USERPROFILE\.ssh\id_rsa"
    
    if (Test-Path $keyPath) {
        Write-Warning "密钥已存在: $keyPath"
        $confirm = Read-Host "是否重新生成? (y/N)"
        if ($confirm -ne "y") { return }
    }
    
    ssh-keygen -t rsa -b 4096 -f $keyPath -C "jarvis@windows"
    
    Write-Success "密钥生成完成！"
    Write-Info "公钥: $keyPath.pub"
    Write-Info "私钥: $keyPath"
    Write-Info @"

将公钥添加到Linux服务器:
1. 复制公钥内容:
   type $keyPath.pub

2. 添加到Linux服务器:
   mkdir -p ~/.ssh
   echo "$(cat $keyPath.pub)" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   chmod 700 ~/.ssh
"@
}

# =====================================================
# 4. 配置 SSH 密钥认证
# =====================================================
function Set-SSHKeyAuth {
    Write-Info "配置 SSH 密钥认证..."
    
    $keyPath = "$env:USERPROFILE\.ssh\id_rsa"
    
    if (-not (Test-Path $keyPath)) {
        Write-Error "密钥不存在，请先运行: -GenerateKey"
        return
    }
    
    Write-Info "复制公钥到服务器..."
    $pubKey = Get-Content "$keyPath.pub"
    
    Write-Info "请手动在服务器上执行:"
    Write-Host @"
mkdir -p ~/.ssh
echo "$pubKey" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
"@ -ForegroundColor Yellow
    
    Write-Success "配置完成！之后可使用密钥登录"
}

# =====================================================
# 5. 远程命令执行封装
# =====================================================
function Invoke-SSHCommand {
    param(
        [string]$Cmd
    )
    
    Write-Info "执行远程命令: $Cmd"
    
    # 尝试使用 plink
    $plinkPaths = @(
        "C:\Program Files\PuTTY\plink.exe",
        "C:\Program Files (x86)\PuTTY\plink.exe"
    )
    
    $plink = $null
    foreach ($path in $plinkPaths) {
        if (Test-Path $path) {
            $plink = $path
            break
        }
    }
    
    if ($plink) {
        & $plink -ssh -P $Port -l $User -pw $Password $Server $Cmd
    } else {
        Write-Warning "未找到 plink，使用 OpenSSH (需手动输入密码)"
        ssh -p $Port $User@$Server $Cmd
    }
}

# =====================================================
# 6. 系统信息采集
# =====================================================
function Get-SystemInfo {
    Write-Info "采集系统信息..."
    
    $commands = @(
        "echo '=== 系统信息 ==='",
        "uname -a",
        "echo ''",
        "echo '=== 运行时间 ==='",
        "uptime",
        "echo ''",
        "echo '=== 内存使用 ==='",
        "free -h",
        "echo ''",
        "echo '=== 磁盘使用 ==='",
        "df -h",
        "echo ''",
        "echo '=== CPU使用 ==='",
        "top -bn1 | head -15"
    )
    
    $scriptBlock = $commands -join "; "
    Invoke-SSHCommand -Cmd $scriptBlock
}

# =====================================================
# 7. 下载安装 plink
# =====================================================
function Install-PlinkTool {
    Write-Info "下载 PuTTY 工具包..."
    
    $downloadDir = "$env:USERPROFILE\Desktop\putty"
    New-Item -ItemType Directory -Force -Path $downloadDir | Out-Null
    
    $url = "https://the.earth.li/~sgtatham/putty/latest/w64/plink.exe"
    $output = "$downloadDir\plink.exe"
    
    try {
        Invoke-WebRequest -Uri $url -OutFile $output -UseBasicParsing
        Write-Success "plink 下载完成: $output"
        Write-Info "现在可以使用 -UsePlink 参数"
    } catch {
        Write-Error "下载失败: $_"
        Write-Info "请手动下载: https://www.putty.org/"
    }
}

# =====================================================
# 8. 显示帮助
# =====================================================
function Show-Help {
    Write-Host @"

╔═══════════════════════════════════════════════════════╗
║     JARVIS SSH Linux 运维工具包 v2.0                   ║
║     Windows SSH Linux 自动化运维                       ║
╚═══════════════════════════════════════════════════════╝

📖 使用方法:

1. 基础连接:
   .\ssh_linux_toolkit.ps1
   (交互式SSH连接，需手动输入密码)

2. 使用 plink 自动登录:
   .\ssh_linux_toolkit.ps1 -UsePlink
   (自动密码登录，需要先安装plink)

3. 执行远程命令:
   .\ssh_linux_toolkit.ps1 -Command "ls -la"
   .\ssh_linux_toolkit.ps1 -Command "systemctl status sshd"

4. 系统信息采集:
   .\ssh_linux_toolkit.ps1 -GetInfo

5. 生成SSH密钥:
   .\ssh_linux_toolkit.ps1 -GenerateKey

6. 安装 plink 工具:
   .\ssh_linux_toolkit.ps1 -InstallPlink

📌 参数说明:
   -Server     服务器IP (默认: 47.97.113.144)
   -Port       SSH端口 (默认: 222)
   -User       用户名 (默认: root)
   -Password   密码 (默认: zXc363324112)
   -Command    要执行的远程命令
   -UsePlink   使用plink自动登录
   -GetInfo    采集系统信息
   -GenerateKey 生成SSH密钥对
   -InstallPlink 下载安装plink

💡 示例:

   # 连接到自定义服务器
   .\ssh_linux_toolkit.ps1 -Server 192.168.1.100 -Port 22

   # 执行多个命令
   .\ssh_linux_toolkit.ps1 -Command "df -h && free -h"

   # 采集系统信息
   .\ssh_linux_toolkit.ps1 -GetInfo

🔒 安全提示:
   - 生产环境建议使用SSH密钥认证
   - 避免在脚本中硬编码密码
   - 使用 -GenerateKey 生成密钥对

"@ -ForegroundColor Cyan
}

# =====================================================
# 主程序
# =====================================================
if ($Help) {
    Show-Help
    exit
}

if ($InstallPlink) {
    Install-PlinkTool
    exit
}

if ($GenerateKey) {
    New-SSHKeyPair
    exit
}

Write-Host @"

╔═══════════════════════════════════════════════════════╗
║           JARVIS SSH Linux 运维工具包                  ║
╚═══════════════════════════════════════════════════════╝

服务器: $Server:$Port
用户: $User

"@ -ForegroundColor Cyan

if ($Command -eq "-GetInfo") {
    Get-SystemInfo
} elseif ($Command) {
    Invoke-SSHCommand -Cmd $Command
} else {
    # 检测是否有 plink
    $plinkExists = $false
    $plinkPaths = @(
        "C:\Program Files\PuTTY\plink.exe",
        "C:\Program Files (x86)\PuTTY\plink.exe",
        "$env:USERPROFILE\Desktop\putty\plink.exe"
    )
    foreach ($path in $plinkPaths) {
        if (Test-Path $path) {
            $plinkExists = $true
            break
        }
    }
    
    if ($plinkExists) {
        Write-Info "检测到 plink，使用自动登录"
        Connect-Plink
    } else {
        Write-Info "使用 OpenSSH 连接"
        Write-Warning "未找到 plink，需要手动输入密码"
        Write-Info "提示: 运行 -InstallPlink 安装自动化工具"
        Connect-OpenSSH
    }
}
