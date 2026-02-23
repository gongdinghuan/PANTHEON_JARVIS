@echo off
chcp 65001 >nul
echo ======================================
echo   SSH密钥登录 47服务器
echo ======================================
echo.
echo 正在使用密钥认证登录...
echo.

start "" /wait cmd /k "ssh -i C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\scripts\id_rsa -p 222 root@47.97.113.144"

echo.
echo SSH会话已关闭
pause
