#Requires -Version 5.1
<#
.SYNOPSIS
    First-run bootstrap: virtualenv, pinned dependencies, env files, optional MySQL.

.DESCRIPTION
    Idempotent. Reuses an existing backend/.venv and existing .env files.
    Native commands are invoked with ErrorActionPreference=Continue so that
    pip/npm stderr output cannot abort the script on Windows PowerShell 5.1.

.PARAMETER WithDocker
    Start the MySQL container from docker-compose and wait for its healthcheck.

.PARAMETER SkipDb
    Do not run scripts/bootstrap_db.py (create_all + alembic stamp).

.EXAMPLE
    .\scripts\bootstrap.ps1
    .\scripts\bootstrap.ps1 -WithDocker
#>
[CmdletBinding()]
param(
    [switch]$WithDocker,
    [switch]$SkipDb
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Venv = Join-Path $Backend '.venv'

function Write-Step([string]$Message) {
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Native {
    param(
        [string]$Exe,
        [string[]]$Arguments,
        [string]$WorkDir
    )
    $previous = $ErrorActionPreference
    Push-Location -LiteralPath $WorkDir
    try {
        $ErrorActionPreference = 'Continue'
        # Out-Host 让原生输出直接显示，不混进函数返回值（否则 $LASTEXITCODE 会被输出行淹没）
        & $Exe @Arguments | Out-Host
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
        Pop-Location
    }
    return $code
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$Arguments,
        [string]$WorkDir
    )
    $code = Invoke-Native $Exe $Arguments $WorkDir
    if ($code -ne 0) {
        throw "Command failed ($code): $Exe $($Arguments -join ' ')"
    }
}

function Test-PythonLauncher312 {
    $previous = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'SilentlyContinue'
        & py -3.12 -c 'import sys' 2>&1 | Out-Null
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $previous
    }
}

Write-Step 'Detect Python'
$PythonExe = 'python'
$PythonArgs = @()
if ((Get-Command py -ErrorAction SilentlyContinue) -and (Test-PythonLauncher312)) {
    $PythonExe = 'py'
    $PythonArgs = @('-3.12')
}
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
    throw 'Python not found. Install Python 3.12 (https://www.python.org/downloads/) and retry.'
}
$Version = (& $PythonExe @PythonArgs -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" | Out-String).Trim()
Write-Host "Using Python $Version"
if (-not $Version.StartsWith('3.12')) {
    Write-Warning 'Project baseline is Python 3.12 (Docker/CI). Local version differs, keep it in mind before committing.'
}

if (-not (Test-Path (Join-Path $Venv 'Scripts\python.exe'))) {
    Write-Step "Create virtualenv: $Venv"
    Invoke-Checked $PythonExe ($PythonArgs + @('-m', 'venv', $Venv)) $Root
} else {
    Write-Host "Reuse virtualenv: $Venv"
}

$Pip = Join-Path $Venv 'Scripts\pip.exe'
$Py = Join-Path $Venv 'Scripts\python.exe'

Write-Step 'Install backend dependencies (pinned in requirements.txt)'
Invoke-Checked $Pip @('install', '-r', (Join-Path $Backend 'requirements-dev.txt')) $Backend

Write-Step 'Prepare env files'
$BackendEnv = Join-Path $Backend '.env'
if (-not (Test-Path $BackendEnv)) {
    Copy-Item (Join-Path $Backend '.env.example') $BackendEnv
    Write-Host 'Created backend/.env - adjust DATABASE_URL / LLM settings if needed.'
} else {
    Write-Host 'backend/.env already exists, skip.'
}
$RootEnv = Join-Path $Root '.env'
if (-not (Test-Path $RootEnv)) {
    Copy-Item (Join-Path $Root '.env.example') $RootEnv
    Write-Host 'Created .env for docker compose.'
}

Write-Step 'Install frontend dependencies'
if (-not (Test-Path (Join-Path $Frontend 'node_modules'))) {
    Invoke-Checked 'npm' @('ci') $Frontend
} else {
    Write-Host 'node_modules exists, skip npm ci.'
}

if ($WithDocker) {
    Write-Step 'Start MySQL container'
    Invoke-Checked 'docker' @('compose', 'up', '-d', 'mysql') $Root
    Write-Host 'Waiting for MySQL healthcheck ...'
    $healthy = $false
    for ($i = 0; $i -lt 60; $i++) {
        $previous = $ErrorActionPreference
        try {
            $ErrorActionPreference = 'SilentlyContinue'
            $status = (& docker inspect --format '{{.State.Health.Status}}' lab-mysql 2>&1 | Out-String).Trim()
        } finally {
            $ErrorActionPreference = $previous
        }
        if ($status -eq 'healthy') {
            $healthy = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $healthy) {
        throw 'MySQL container is not healthy after 120s. Check: docker compose logs mysql'
    }
}

if (-not $SkipDb) {
    Write-Step 'Initialize database schema (create_all + alembic stamp)'
    try {
        Invoke-Checked $Py @('scripts/bootstrap_db.py') $Backend
    } catch {
        Write-Warning 'Database init failed.'
        Write-Warning 'Make sure MySQL is running and backend/.env DATABASE_URL is correct.'
        Write-Warning 'Tip: .\scripts\bootstrap.ps1 -WithDocker'
    }
} else {
    Write-Host 'Skip database init (-SkipDb).'
}

Write-Step 'Done'
Write-Host 'Next:'
Write-Host '  .\scripts\dev.ps1     # start backend (8000) + frontend (5173)'
Write-Host '  .\scripts\check.ps1   # ruff + pytest (+ frontend build)'
exit 0
