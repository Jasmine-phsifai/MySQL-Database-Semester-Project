@echo off
rem Python env one-click installer (delegates to install.ps1).
rem Uses Tsinghua mirror; works on Win10/11 with PowerShell 5.1+.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
if errorlevel 1 (
    echo.
    echo [ERROR] install failed. Read messages above for details.
    pause
    exit /b 1
)
echo.
echo [OK] install finished. Now run: start.bat
pause
