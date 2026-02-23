@echo off
REM SSH Connection Script for 47.97.113.144
REM Created by JARVIS - 2026-02-13

echo ========================================
echo   SSH Connection to 47.97.113.144
echo ========================================
echo.

set SERVER=47.97.113.144
set PORT=222
set USER=root

echo Server: %SERVER%
echo Port: %PORT%
echo User: %USER%
echo.
echo Connecting...

REM Try using plink if available
if exist "C:\Program Files\PuTTY\plink.exe" (
    echo Using plink...
    "C:\Program Files\PuTTY\plink.exe" -P %PORT% -pw zXc363324112 %USER%@%SERVER%
) else (
    REM Using Windows OpenSSH
    echo Using Windows OpenSSH...
    echo Password will be required: zXc363324112
    ssh -p %PORT% %USER%@%SERVER%
)

echo.
echo ========================================
echo   Connection Closed
echo ========================================
pause
