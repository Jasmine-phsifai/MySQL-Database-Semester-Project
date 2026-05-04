@echo off
rem Student Grading DB - launcher
rem Pure ASCII to avoid GBK/UTF-8 cmd parsing issues with Chinese path.
rem Real Chinese messages live in start.ps1 (PowerShell handles UTF-8 fine).

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
if errorlevel 1 (
    echo.
    echo [ERROR] Launcher failed. See messages above.
    pause
)
