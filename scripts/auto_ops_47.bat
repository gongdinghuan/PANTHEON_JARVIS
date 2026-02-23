@echo off
chcp 65001 >nul
echo =====================================================
echo   正在连接到服务器 47.97.113.144...
echo   账号: root
echo   端口: 22
echo   密码: zXc363324112
echo =====================================================
echo.
echo [√] 正在启动 SSH 连接...
echo.
start "" /max ssh root@47.97.113.144
timeout /t 5 /nobreak >nul
echo [√] SSH 窗口已打开，等待您输入密码
echo.
echo 密码: zXc363324112
echo.
timeout /t 30
