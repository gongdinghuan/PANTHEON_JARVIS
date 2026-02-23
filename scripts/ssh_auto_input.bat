@echo off
REM JARVIS SSH自动密码输入脚本
REM Stark先生专属

echo ============================================
echo   JARVIS SSH Auto Password Input
echo ============================================
echo.
echo 服务器: 47.97.113.144:222
echo 用户: root
echo.
echo 正在启动SSH连接...
echo.

REM 方法1: 使用PowerShell自动激活窗口并输入密码
powershell -Command "$w = New-Object -ComObject WScript.Shell; Start-Sleep 2; $w.AppActivate('ssh.exe'); Start-Sleep 1; $w.SendKeys('zXc363324112'); $w.SendKeys('{ENTER}')"

echo.
echo 密码已自动输入，请检查SSH窗口
echo.
pause
