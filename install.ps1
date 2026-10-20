# UniversalResume / SameThread one-line installer for Windows
$ErrorActionPreference = "Stop"

Write-Host @'
   __  __      _                             __   ____                                
  / / / /___  (_)   _____  ______________ _ / /  / __ \___  _______  ______ ___  ___ 
 / / / / __ \/ / | / / _ \/ ___/ ___/ __ `// /  / /_/ / _ \/ ___/ / / / __ `__ \/ _ \
/ /_/ / / / / /| |/ /  __/ /  (__  ) /_/ // /  / _, _/  __(__  ) /_/ / / / / / /  __/
\____/_/ /_/_/ |___/\___/_/  /____/\__,_//_/  /_/ |_|\___/____/\__,_/_/ /_/ /_/\___/ 
'@ -ForegroundColor White

Write-Host "Installing UniversalResume..."

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
$targetDir = "$env:USERPROFILE\.samethread-repo"
if (Test-Path $targetDir) {
    Write-Host "Updating repository in $targetDir..." -ForegroundColor DarkGray
    git -C $targetDir pull --quiet
} else {
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
    & hop sync
} finally {
    Pop-Location
}

# Ensure resume wrapper is globally available in user npm
$npmDir = "$env:APPDATA\npm"
if (Test-Path $npmDir) {
    Copy-Item -Force "$targetDir\bin\resume.cmd" "$npmDir\resume.cmd"
}

Write-Host "`nUniversalResume installed successfully!" -ForegroundColor Green
Write-Host "Type 'resume' anywhere in your terminal to start."
