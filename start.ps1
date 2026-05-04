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
