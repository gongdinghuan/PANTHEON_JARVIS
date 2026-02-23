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
set PLINK1=C:\Program Files\PuTTY\plink.exe
set PLINK2=C:\Program Files (x86)\PuTTY\plink.exe

if exist "%PLINK1%" (
    set PLINK=%PLINK1%
) else if exist "%PLINK2%" (
    set PLINK=%PLINK2%
) else (
    echo ERROR: plink.exe not found
    goto :eof
)

echo Using plink: %PLINK%
echo.

echo Executing commands on server...
echo.

(
echo =========================================
echo         Server Maintenance Report
echo =========================================
echo.

echo === 1. System Info ===
uname -a
cat /etc/os-release ^| head -5
uptime

echo.
echo === 2. System Load ===
top -bn1 ^| head -15

echo.
echo === 3. Memory Usage ===
free -h

echo.
echo === 4. Disk Usage ===
df -h

echo.
echo === 5. Network Connections ===
ss -tulnp ^| head -20

echo.
echo === 6. SSH Service Status ===
systemctl status sshd ^| head -15

echo.
echo === 7. Running Services ===
systemctl list-units --type=service --state=running --no-pager ^| head -20

echo.
echo === 8. Online Users ===
who -a

echo.
echo === 9. Login History ===
last -n 10 ^| head -15

echo.
echo === 10. Process Info ===
ps aux --sort=-%%cpu ^| head -20

echo.
echo =========================================
echo       Report Complete
echo =========================================
) > "%TEMP%\ssh_commands.txt"

"%PLINK%" -ssh -P %PORT% -l %USER% -pw %PASS% %SERVER% < "%TEMP%\ssh_commands.txt" > "%OUTPUT%" 2>&1

del "%TEMP%\ssh_commands.txt"

echo Report saved to: %OUTPUT%
echo.
echo =========================================
echo       Report Content
echo =========================================
type "%OUTPUT%"

echo.
pause
