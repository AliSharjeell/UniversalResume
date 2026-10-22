# UniversalResume / SameThread one-line installer for Windows
$ErrorActionPreference = "Stop"

Write-Host "Installing UniversalResume..." -ForegroundColor White

# Check for Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3.9+ is required but not found in PATH."
}

# Check or install Bun
if (-not (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Host "Installing Bun..." -ForegroundColor Yellow
    irm bun.sh/install.ps1 | iex
    $env:PATH = "$env:USERPROFILE\.bun\bin;$env:PATH"
}

# Target directory
if (Test-Path "$PSScriptRoot\pyproject.toml") {
    $targetDir = (Resolve-Path $PSScriptRoot).Path
    Write-Host "Installing locally from $targetDir..." -ForegroundColor Cyan
} elseif (Test-Path "$env:USERPROFILE\.samethread-repo") {
    $targetDir = "$env:USERPROFILE\.samethread-repo"
    Write-Host "Updating repository in $targetDir..." -ForegroundColor DarkGray
    git -C $targetDir pull --quiet
} else {
    $targetDir = "$env:USERPROFILE\.samethread-repo"
    Write-Host "Cloning repository to $targetDir..." -ForegroundColor DarkGray
    git clone --quiet https://github.com/AliSharjeell/UniversalResume.git $targetDir
}

# Install dependencies and link
Push-Location $targetDir
try {
    Write-Host "Setting up OpenTUI and agent hooks..." -ForegroundColor DarkGray
    & bun install --silent
    & npm link --silent 2>$null
    & python -m pip install -e . --quiet
    & hop install
} finally {
    Pop-Location
}

# Ensure resume wrapper is globally available in user npm
$npmDir = "$env:APPDATA\npm"
if (Test-Path $npmDir) {
    $cmdContent = @"
@echo off
setlocal
if exist "%~dp0resume.js" (
  bun "%~dp0resume.js" %*
) else if exist "$targetDir\bin\resume.js" (
  bun "$targetDir\bin\resume.js" %*
) else (
  bun "%USERPROFILE%\.samethread-repo\bin\resume.js" %*
)
"@
    Set-Content -Path "$npmDir\resume.cmd" -Value $cmdContent -Encoding ASCII
}

Write-Host "`nUniversalResume installed successfully!" -ForegroundColor Green
Write-Host "Type 'resume' anywhere in your terminal to start."
