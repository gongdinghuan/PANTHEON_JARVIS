@echo off
chcp 65001 >nul
cls
echo ========================================================
echo   服务器 47.97.113.144 自动化运维
echo ========================================================
echo   账号: root
echo   端口: 222
echo   密码: zXc363324112
echo ========================================================
echo.
echo [1] 启动SSH连接
echo [2] 查看运维命令
echo [3] 一键执行（推荐）
echo.
set /p choice=请选择操作 (1-3): 

if "%choice%"=="1" goto ssh
if "%choice%"=="2" goto commands
if "%choice%"=="3" goto auto

:ssh
echo.
echo 正在启动SSH连接...
start "" /max ssh -p 222 root@47.97.113.144
echo.
echo SSH窗口已打开，请输入密码: zXc363324112
echo.
pause
exit

:commands
cls
echo ========================================================
echo   运维命令清单（复制到SSH窗口执行）
echo ========================================================
echo.
echo uname -a ^&^& uptime
echo free -h
echo df -h
echo top -bn1 ^| head -15
echo ss -tulnp ^| head -20
echo systemctl status sshd
echo systemctl list-units --type=service --state=running ^| head -20
echo who -a
echo last -n 10
echo journalctl -xe --no-pager ^| tail -20
echo.
pause
exit

:auto
cls
echo ========================================================
echo   创建自动化运维脚本
echo ========================================================
echo.

set ops_file=%USERPROFILE%\Desktop\ops_commands.sh

echo # 服务器运维脚本 > "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 服务器基础信息 ===" >> "%ops_file%"
echo uname -a >> "%ops_file%"
echo uptime >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 内存使用 ===" >> "%ops_file%"
echo free -h >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 磁盘使用 ===" >> "%ops_file%"
echo df -h >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== CPU负载 ===" >> "%ops_file%"
echo top -bn1 ^| head -15 >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 网络连接 ===" >> "%ops_file%"
echo ss -tulnp ^| head -20 >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== SSH状态 ===" >> "%ops_file%"
echo systemctl status sshd ^| head -10 >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 运行中的服务 ===" >> "%ops_file%"
echo systemctl list-units --type=service --state=running ^| head -20 >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 在线用户 ===" >> "%ops_file%"
echo who -a >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 最近登录 ===" >> "%ops_file%"
echo last -n 10 >> "%ops_file%"
echo. >> "%ops_file%"
echo echo "=== 系统日志 ===" >> "%ops_file%"
echo journalctl -xe --no-pager ^| tail -30 >> "%ops_file%"

echo.
echo [√] 运维脚本已创建: %ops_file%
echo.
echo 现在启动SSH连接...
echo 登录后执行: bash ~/Desktop/ops_commands.sh
echo.
pause

start "" /max ssh -p 222 root@47.97.113.144

echo.
echo SSH窗口已打开，请输入密码: zXc363324112
echo 登录后执行: bash ~/Desktop/ops_commands.sh
echo.
pause
exit
