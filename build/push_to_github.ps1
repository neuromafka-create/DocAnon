#Requires -Version 5.1
<#
.SYNOPSIS
  Создаёт (при необходимости) репозиторий DocAnon на GitHub и пушит main.

.EXAMPLE
  # 1) Войти (один раз, откроется браузер):
  & "C:\Program Files\GitHub CLI\gh.exe" auth login -h github.com -p https -w

  # 2) Запушить:
  .\build\push_to_github.ps1
  .\build\push_to_github.ps1 -Private
#>
param(
    [string]$RepoName = "DocAnon",
    [switch]$Private,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
    $ghCmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($ghCmd) { $gh = $ghCmd.Source }
    else { throw "GitHub CLI (gh) не найден. Установите: winget install GitHub.cli" }
}

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

# Auth
& $gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Нужен вход в GitHub. Запускаю: gh auth login ..." -ForegroundColor Yellow
    & $gh auth login -h github.com -p https -w
    if ($LASTEXITCODE -ne 0) { throw "Авторизация не удалась" }
}

$user = & $gh api user --jq .login
if (-not $user) { throw "Не удалось получить GitHub username" }
Write-Host "GitHub user: $user" -ForegroundColor Cyan

$visibility = if ($Private) { "private" } else { "public" }
$full = "$user/$RepoName"

# Create repo if missing
$exists = $true
& $gh repo view $full 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    $exists = $false
    Write-Host "Создаю репозиторий $full ($visibility)..." -ForegroundColor Cyan
    & $gh repo create $RepoName --$visibility --source=. --remote=origin --description "DocAnon — локальный анонимизатор документов по 152-ФЗ"
    if ($LASTEXITCODE -ne 0) { throw "gh repo create failed" }
}
else {
    Write-Host "Репозиторий уже есть: $full" -ForegroundColor Green
    $url = "https://github.com/$full.git"
    $remote = git remote get-url origin 2>$null
    if (-not $remote) {
        git remote add origin $url
    }
    else {
        git remote set-url origin $url
    }
}

# Ensure on main with commit
$branch = git branch --show-current
if ($branch -ne "main") {
    git branch -M main
}

Write-Host "Push main -> origin..." -ForegroundColor Cyan
if ($Force) {
    git push -u origin main --force
}
else {
    git push -u origin main
}
if ($LASTEXITCODE -ne 0) { throw "git push failed" }

Write-Host @"

Готово: https://github.com/$full

"@ -ForegroundColor Green
