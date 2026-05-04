# Student Grading DB - Python deps installer.
# Pure ASCII to dodge Windows PowerShell 5.1 ANSI/UTF-8 .ps1 parsing pitfalls.
#
# Usage:
#   install.bat                   - install missing packages into the auto-detected Python
#   install.bat -Target conda     - force the existing conda env at D:\Anaconda\envs\py312
#   install.bat -Target system    - the python on PATH
#   install.bat -Target runtime   - the embedded interpreter at runtime\python.exe
#   install.bat -Force            - reinstall everything even if already present

param(
    [ValidateSet("auto","conda","system","runtime")]
    [string]$Target = "auto",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

$TUNA = "https://pypi.tuna.tsinghua.edu.cn/simple"
$Req  = Join-Path $ProjectRoot "requirements.txt"
if (-not (Test-Path $Req)) {
    Write-Host "[err] requirements.txt missing at $Req" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------
# 1. Pick interpreter
# ------------------------------------------------------------------
function Find-Py {
    param([string]$which)
    $cands = switch ($which) {
        "runtime" { @((Join-Path $ProjectRoot "runtime\python.exe")) }
        "conda"   { @("D:\Anaconda\envs\py312\python.exe") }
        "system"  { @() }
        default {
            @((Join-Path $ProjectRoot "runtime\python.exe"),
              "D:\Anaconda\envs\py312\python.exe")
        }
    }
    foreach ($p in $cands) { if (Test-Path $p) { return $p } }
    if ($which -eq "system" -or $which -eq "auto") {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    return $null
}

$Py = Find-Py $Target
if ($null -eq $Py) {
    Write-Host "[err] Python interpreter not found. Tried target=$Target" -ForegroundColor Red
    Write-Host "      Hint: install Python 3.12 or unzip embeddable into runtime\"
    exit 1
}
Write-Host "[1/4] interpreter:" -ForegroundColor DarkCyan
Write-Host "      $Py"
& $Py -V
if ($LASTEXITCODE -ne 0) {
    Write-Host "[err] interpreter failed -V" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------
# 2. Make sure pip works; upgrade pip via Tsinghua
# ------------------------------------------------------------------
Write-Host "[2/4] ensure pip via Tsinghua mirror..." -ForegroundColor DarkCyan
& $Py -m ensurepip --default-pip 2>&1 | Out-Null
& $Py -m pip install --quiet --upgrade --index-url $TUNA --trusted-host pypi.tuna.tsinghua.edu.cn pip
if ($LASTEXITCODE -ne 0) {
    Write-Host "[warn] pip upgrade failed (ignoring; install will still try)" -ForegroundColor Yellow
}

# ------------------------------------------------------------------
# 3. Detect what's missing (skip work if not -Force)
# ------------------------------------------------------------------
$Modules = @(
    @{name="PyQt6";        import="PyQt6"},
    @{name="PyMySQL";      import="pymysql"},
    @{name="bcrypt";       import="bcrypt"},
    @{name="pandas";       import="pandas"},
    @{name="openpyxl";     import="openpyxl"},
    @{name="Faker";        import="faker"},
    @{name="pdfplumber";   import="pdfplumber"},
    @{name="pyqtdarktheme";import="qdarktheme"}
)

$missing = @()
if ($Force) {
    Write-Host "[3/4] -Force: skipping detection, will reinstall all" -ForegroundColor DarkCyan
} else {
    Write-Host "[3/4] detecting installed packages..." -ForegroundColor DarkCyan
    foreach ($m in $Modules) {
        $code = "import importlib.util as u, sys; sys.exit(0 if u.find_spec('$($m.import)') else 1)"
        & $Py -c $code 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host ("      [ok ] {0,-15}" -f $m.name) -ForegroundColor DarkGreen
        } else {
            Write-Host ("      [miss] {0,-15}" -f $m.name) -ForegroundColor Yellow
            $missing += $m.name
        }
    }
    if ($missing.Count -eq 0) {
        Write-Host "[3/4] nothing to install. Exit 0." -ForegroundColor DarkGreen
        exit 0
    }
}

# ------------------------------------------------------------------
# 4. pip install via Tsinghua
# ------------------------------------------------------------------
Write-Host "[4/4] installing via Tsinghua mirror ($TUNA) ..." -ForegroundColor DarkCyan

$args = @("-m","pip","install",
          "--index-url",$TUNA,
          "--trusted-host","pypi.tuna.tsinghua.edu.cn",
          "--prefer-binary",
          "-r",$Req)
if ($Force) { $args += "--force-reinstall" }

& $Py @args
$rc = $LASTEXITCODE
if ($rc -ne 0) {
    Write-Host "[err] pip install failed (exit $rc)." -ForegroundColor Red
    Write-Host "      Network problem? Try a VPN or rerun: install.bat -Force"
    exit $rc
}

# ------------------------------------------------------------------
# 5. Final verify
# ------------------------------------------------------------------
Write-Host ""
Write-Host "[verify] re-checking imports..." -ForegroundColor DarkCyan
$bad = @()
foreach ($m in $Modules) {
    $code = "import importlib.util as u, sys; sys.exit(0 if u.find_spec('$($m.import)') else 1)"
    & $Py -c $code 2>$null
    if ($LASTEXITCODE -ne 0) { $bad += $m.name }
}
if ($bad.Count -gt 0) {
    Write-Host ("[err] still missing: " + ($bad -join ", ")) -ForegroundColor Red
    exit 1
}
Write-Host "[done] all dependencies OK." -ForegroundColor DarkGreen
Write-Host ""
Write-Host "Now double-click start.bat to launch the app."
exit 0
