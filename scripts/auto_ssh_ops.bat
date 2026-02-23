@echo off
title SSH Server Ops - Auto
chcp 65001 >nul
echo [INFO] Starting SSH remote operations...
echo.
echo Server: 47.97.113.144:222
echo User: root
echo.

start "" cmd /c "ssh -p 222 root@47.97.113.144 -o StrictHostKeyChecking=no > C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\reports\server_raw_output.txt 2>&1"

timeout /t 8 /nobreak >nul

echo [INFO] SSH connection initiated in new window...
echo.
echo Please enter password in the SSH window: zXc363324112
echo.
echo Commands will execute automatically...
echo.
pause
