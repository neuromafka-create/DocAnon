#Requires -Version 5.1
<#
.SYNOPSIS
  Простой установщик без Inno Setup: копирует portable DocAnon в профиль
  пользователя и создаёт ярлыки в меню Пуск и на рабочем столе.

.EXAMPLE
  # из корня репозитория после build_windows.ps1:
  .\build\install_portable.ps1

  # из распакованного ZIP (рядом с DocAnon.exe):
  .\install_portable.ps1
#>
param(
    [string]$InstallDir = "",
    [switch]$NoDesktop
)

$ErrorActionPreference = "Stop"

# Источник: dist\DocAnon или папка, где лежит этот скрипт / exe
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $ScriptDir "..") -ErrorAction SilentlyContinue
$Source = $null
if ($Root -and (Test-Path (Join-Path $Root "dist\DocAnon\DocAnon.exe"))) {
    $Source = Join-Path $Root "dist\DocAnon"
}
elseif (Test-Path (Join-Path $ScriptDir "DocAnon.exe")) {
    $Source = $ScriptDir
}
elseif (Test-Path (Join-Path (Get-Location) "DocAnon.exe")) {
    $Source = (Get-Location).Path
}
else {
    throw "Не найден DocAnon.exe. Сначала соберите: .\build\build_windows.ps1"
}

if (-not $InstallDir) {
    $InstallDir = Join-Path $env:LOCALAPPDATA "Programs\DocAnon"
}

Write-Host "Source : $Source" -ForegroundColor Cyan
Write-Host "Install: $InstallDir" -ForegroundColor Cyan

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Copy-Item -Path (Join-Path $Source "*") -Destination $InstallDir -Recurse -Force

$exe = Join-Path $InstallDir "DocAnon.exe"
if (-not (Test-Path $exe)) { throw "Copy failed: $exe missing" }

# Ярлыки
$WshShell = New-Object -ComObject WScript.Shell

$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\DocAnon"
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null
$lnk = $WshShell.CreateShortcut((Join-Path $startMenu "DocAnon.lnk"))
$lnk.TargetPath = $exe
$lnk.WorkingDirectory = $InstallDir
$lnk.Description = "DocAnon — анонимизатор документов"
$lnk.Save()

if (-not $NoDesktop) {
    $desk = [Environment]::GetFolderPath("Desktop")
    $lnk2 = $WshShell.CreateShortcut((Join-Path $desk "DocAnon.lnk"))
    $lnk2.TargetPath = $exe
    $lnk2.WorkingDirectory = $InstallDir
    $lnk2.Description = "DocAnon — анонимизатор документов"
    $lnk2.Save()
}

# Uninstall helper
$uninst = @"
# Удаление DocAnon (portable install)
Remove-Item -LiteralPath '$InstallDir' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath '$startMenu' -Recurse -Force -ErrorAction SilentlyContinue
`$desk = [Environment]::GetFolderPath('Desktop')
Remove-Item (Join-Path `$desk 'DocAnon.lnk') -Force -ErrorAction SilentlyContinue
Write-Host 'DocAnon удалён.'
"@
Set-Content -Path (Join-Path $InstallDir "uninstall.ps1") -Value $uninst -Encoding UTF8

Write-Host @"

Установка завершена.
  Папка:   $InstallDir
  Запуск:  $exe
  Меню Пуск: DocAnon
  Удаление:  $InstallDir\uninstall.ps1

"@ -ForegroundColor Green
