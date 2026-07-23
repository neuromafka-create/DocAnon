#Requires -Version 5.1
<#
.SYNOPSIS
  Сборка DocAnon для Windows: PyInstaller (portable) + Inno Setup (установщик).

.DESCRIPTION
  1. Устанавливает pyinstaller (если нет)
  2. Проверяет spaCy-модель ru_core_news_lg
  3. Собирает dist\DocAnon\  (portable, можно копировать на флешку)
  4. Если установлен Inno Setup — собирает dist\installer\DocAnon-Setup-*.exe

.EXAMPLE
  .\build\build_windows.ps1
  .\build\build_windows.ps1 -SkipInstaller
  .\build\build_windows.ps1 -Clean
#>
param(
    [switch]$SkipInstaller,
    [switch]$Clean,
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

Write-Host "=== DocAnon Windows build ===" -ForegroundColor Cyan
Write-Host "Root: $Root"

# --- Python ---
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    throw "Python не найден в PATH. Установите Python 3.10+ и повторите."
}
Write-Host "Python: $(python --version)"

# --- Clean ---
if ($Clean) {
    Write-Host "Cleaning build/dist/__pycache__..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$Root\build\DocAnon"
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "$Root\dist"
    Get-ChildItem -Recurse -Directory -Filter "__pycache__" $Root |
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Deps ---
Write-Host "Installing build deps..." -ForegroundColor Cyan
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
python -m pip install -q "pyinstaller>=6.0"

# --- spaCy model ---
Write-Host "Checking ru_core_news_lg..." -ForegroundColor Cyan
$hasModel = python -c "import ru_core_news_lg; print('ok')" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Downloading spaCy model ru_core_news_lg (large, ~500MB)..." -ForegroundColor Yellow
    python -m spacy download ru_core_news_lg
    if ($LASTEXITCODE -ne 0) { throw "Не удалось установить ru_core_news_lg" }
}

# --- PyInstaller ---
Write-Host "Running PyInstaller (this may take 5-15 minutes)..." -ForegroundColor Cyan
$spec = Join-Path $Root "build\docanon.spec"
python -m PyInstaller --noconfirm --clean $spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$distApp = Join-Path $Root "dist\DocAnon"
if (-not (Test-Path (Join-Path $distApp "DocAnon.exe"))) {
    throw "dist\DocAnon\DocAnon.exe not found after build"
}

# Portable zip
Write-Host "Creating portable ZIP..." -ForegroundColor Cyan
$zipPath = Join-Path $Root "dist\DocAnon-portable-0.1.0.zip"
if (Test-Path $zipPath) {
    try { Remove-Item $zipPath -Force -ErrorAction Stop }
    catch { Start-Sleep -Seconds 2; Remove-Item $zipPath -Force -ErrorAction SilentlyContinue }
}
Compress-Archive -Path (Join-Path $distApp "*") -DestinationPath $zipPath -Force
$zipMb = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "Portable ZIP: $zipPath ($zipMb MB)" -ForegroundColor Green

# --- Inno Setup ---
if (-not $SkipInstaller) {
    $iscc = @(
        "${env:LocalAppData}\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if ($iscc) {
        Write-Host "Compiling installer with Inno Setup: $iscc" -ForegroundColor Cyan
        $iss = Join-Path $Root "build\docanon.iss"
        & $iscc $iss
        if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
        $setup = Get-ChildItem (Join-Path $Root "dist\installer") -Filter "DocAnon-Setup-*.exe" -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($setup) {
            Write-Host "Installer: $($setup.FullName)" -ForegroundColor Green
        }
    }
    else {
        Write-Host @"

Inno Setup 6 not found — installer .exe skipped.
Portable build is ready: dist\DocAnon\ and $zipPath

To build full installer:
  1. Install Inno Setup 6: https://jrsoftware.org/isinfo.php
  2. Re-run: .\build\build_windows.ps1
  Or open build\docanon.iss in Inno Setup Compiler.

"@ -ForegroundColor Yellow
    }
}

Write-Host @"

=== Done ===
Portable folder : dist\DocAnon\
Portable ZIP    : dist\DocAnon-portable-0.1.0.zip
Installer (Inno): dist\installer\DocAnon-Setup-0.1.0.exe  (if Inno Setup installed)

Run portable:
  dist\DocAnon\DocAnon.exe

Установка в профиль пользователя (без Inno Setup):
  .\build\install_portable.ps1

"@ -ForegroundColor Cyan
