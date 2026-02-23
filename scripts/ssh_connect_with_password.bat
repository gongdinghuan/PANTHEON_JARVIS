@echo off
REM SSH自动密码连接脚本
echo ========================================
echo   SSH Connection to 47.97.113.144
echo ========================================
echo.
echo Server: 47.97.113.144:222
echo User: root
echo.

REM 尝试使用plink（如果有）
where plink >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using plink with auto-password...
    plink -ssh -P 222 -pw zXc363324112 root@47.97.113.144
    goto :end
)

REM 尝试使用Windows OpenSSH
where ssh >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Using ssh (manual password required)...
    echo Password: zXc363324112
    ssh -p 222 root@47.97.113.144
    goto :end
)

echo Error: Neither plink nor ssh found!
echo Please install PuTTY or enable Windows OpenSSH

:end
pause
