@echo off
setlocal enabledelayedexpansion

:: 服务器信息
set SERVER=47.97.113.144
set PORT=222
set USER=root
set PASSWORD=zXc363324112

:: 检查 plink 是否存在
where plink.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] 使用 plink 连接...
    plink.exe -P %PORT% -pw %PASSWORD% %USER%@%SERVER% "uname -a && uptime && echo '=== MEMORY ===' && free -h && echo '=== DISK ===' && df -h && echo '=== TOP ===' && top -bn1 | head -15 && echo '=== SERVICES ===' && systemctl list-units --type=service --state=running | head -20"
) else (
    echo [INFO] plink 未找到，使用 PowerShell...
    powershell -ExecutionPolicy Bypass -File "%~dp0ssh_remote_ops.ps1"
)

pause
