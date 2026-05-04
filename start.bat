@echo off
REM ============================================================
REM 学生成绩数据库 - 一键启动
REM 优先 runtime\python.exe (打包内置), 否则 fallback 到 py312
REM ============================================================

setlocal
chcp 65001 > nul
cd /d "%~dp0"

set "PY="
if exist "runtime\python.exe" (
    set "PY=runtime\python.exe"
) else if exist "D:\Anaconda\envs\py312\python.exe" (
    set "PY=D:\Anaconda\envs\py312\python.exe"
) else (
    where python > nul 2>&1
    if %errorlevel%==0 ( set "PY=python" )
)

if "%PY%"=="" (
    echo [ERROR] 找不到 Python 解释器.
    echo   请安装 Python 3.12+ 或把 embeddable runtime 解压到 runtime\ 目录.
    pause
    exit /b 1
)

REM 探测 MySQL 端口
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient; try { $c.Connect('127.0.0.1',3306); $c.Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 (
    echo [WARN] 无法连接 127.0.0.1:3306. 请确认 MySQL 服务正在运行.
    echo   1. 按 Win+R, 输入 services.msc, 启动 MySQL 服务
    echo   2. 或运行: net start MySQL
    echo.
    pause
)

set "PYTHONPATH=%cd%"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
"%PY%" -X utf8 -m app
endlocal
