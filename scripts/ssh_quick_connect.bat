@echo off
REM ========================================
REM SSH 快速连接批处理脚本
REM ========================================
REM 作者：JARVIS
REM 创建时间：2026-02-13
REM ========================================

setlocal

REM 配置参数
set SERVER=47.97.113.144
set PORT=222
set USERNAME=root
set PASSWORD=zXc363324112

REM 检查是否提供了命令参数
set COMMAND=%1

echo ========================================
echo  SSH 连接到: %SERVER%:%PORT%
echo ========================================
echo.

if "%COMMAND%"=="" (
    REM 交互式连接
    echo [模式] 交互式 SSH 会话
    echo.
    
    REM 尝试使用 plink
    if exist "C:\Tools\plink.exe" (
        "C:\Tools\plink.exe" -ssh -P %PORT% -pw %PASSWORD% %USERNAME%@%SERVER%
    ) else if exist "%USERPROFILE%\Downloads\plink.exe" (
        "%USERPROFILE%\Downloads\plink.exe" -ssh -P %PORT% -pw %PASSWORD% %USERNAME%@%SERVER%
    ) else (
        REM 使用系统 SSH（需要手动输入密码）
        ssh -p %PORT% %USERNAME%@%SERVER%
    )
) else (
    REM 执行命令
    echo [模式] 执行命令: %COMMAND%
    echo.
    
    REM 尝试使用 plink
    if exist "C:\Tools\plink.exe" (
        "C:\Tools\plink.exe" -ssh -P %PORT% -pw %PASSWORD% %USERNAME%@%SERVER% %COMMAND%
    ) else if exist "%USERPROFILE%\Downloads\plink.exe" (
        "%USERPROFILE%\Downloads\plink.exe" -ssh -P %PORT% -pw %PASSWORD% %USERNAME%@%SERVER% %COMMAND%
    ) else (
        echo [错误] 找不到 plink.exe
        echo 请下载 PuTTY: https://www.putty.org/
        exit /b 1
    )
)

echo.
echo ✅ 完成！
endlocal
