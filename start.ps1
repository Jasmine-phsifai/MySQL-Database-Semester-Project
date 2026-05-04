# Student Grading DB - PowerShell launcher
# All ASCII to avoid Windows PowerShell 5.1 ANSI/UTF-8 parsing pitfalls.
# Chinese error pop-ups are inside the Python/Qt app itself.

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot
$env:PYTHONPATH = $ProjectRoot

# ---- 1. Locate Python ------------------------------------------------------
$Py = $null
foreach ($p in @(
    (Join-Path $ProjectRoot "runtime\python.exe"),
    "D:\Anaconda\envs\py312\python.exe"
)) {
    if (Test-Path $p) { $Py = $p; break }
}
if ($Py -eq $null) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $Py = $cmd.Source }
}
if ($Py -eq $null) {
    Write-Host "[ERR] Python 3.12+ not found." -ForegroundColor Red
    Write-Host "      Install Python or unzip embeddable into runtime\"
    exit 1
}
Write-Host "[boot] Python: $Py" -ForegroundColor DarkCyan

# ---- 1.5 Verify required packages ------------------------------------------
$probe = "import importlib.util as u; mods=['PyQt6','pymysql','bcrypt','pandas','openpyxl','faker','qdarktheme','pdfplumber']; miss=[m for m in mods if not u.find_spec(m)]; print(','.join(miss)); import sys; sys.exit(1 if miss else 0)"
$missOut = & $Py -c $probe 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[err] missing python packages: $missOut" -ForegroundColor Red
    Write-Host "      Run install.bat first (Tsinghua mirror, one-click)." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "[boot] python deps ok" -ForegroundColor DarkGreen

# ---- 2. Probe MySQL --------------------------------------------------------
$tcp = New-Object System.Net.Sockets.TcpClient
try {
    $tcp.Connect("127.0.0.1", 3306)
    $tcp.Close()
    Write-Host "[boot] MySQL 127.0.0.1:3306 reachable" -ForegroundColor DarkGreen
} catch {
    Write-Host "[warn] Cannot reach 127.0.0.1:3306." -ForegroundColor Yellow
    Write-Host "       Start MySQL via services.msc or: net start MySQL"
    Read-Host "Press Enter to launch anyway"
}

# ---- 3. Launch app --------------------------------------------------------
Write-Host "[boot] launching python -m app ..." -ForegroundColor DarkCyan
& $Py -X utf8 -m app
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Host ""
    Write-Host "[exit $code] app terminated abnormally" -ForegroundColor Red
    Read-Host "Press Enter to close"
}
exit $code
