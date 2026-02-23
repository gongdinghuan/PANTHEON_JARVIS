@echo off
setlocal enabledelayedexpansion

set SERVER=47.97.113.144
set PORT=222
set USER=root
set PASS=zXc363324112
set OUTPUT=C:\Users\Administrator\Desktop\workspace\PANTHEON_JARVIS\reports\server_maintenance_47.txt

echo =========================================
echo   Server Maintenance Report
echo =========================================
echo.

echo Checking plink...
set "PLINK1=C:\Program Files\PuTTY\plink.exe"
set "PLINK2=C:\Program Files (x86)\PuTTY\plink.exe"

if exist "%PLINK1%" (
    set "PLINK=%PLINK1%"
) else if exist "%PLINK2%" (
    set "PLINK=%PLINK2%"
) else (
    echo ERROR: plink.exe not found
    goto :eof
)

echo Using plink: %PLINK%
echo.

echo Executing commands on server...
echo.

"%PLINK%" -ssh -P %PORT% -l %USER% -pw %PASS% %SERVER% "uname -a && echo && uptime && echo && free -h && echo && df -h" > "%OUTPUT%" 2>&1

echo Report saved to: %OUTPUT%
echo.
type "%OUTPUT%"

echo.
pause
