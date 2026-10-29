#Requires -Version 5.1
<#
.SYNOPSIS
    Local quality gate: ruff + pytest (+ frontend production build).

.PARAMETER BackendOnly
    Skip the frontend build (useful when node_modules is absent).

.EXAMPLE
    .\scripts\check.ps1
    .\scripts\check.ps1 -BackendOnly
#>
[CmdletBinding()]
param(
    [switch]$BackendOnly
)

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Py = Join-Path $Backend '.venv\Scripts\python.exe'

function Write-Step([string]$Message) {
    Write-Host ''
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$Exe,
        [string[]]$Arguments,
        [string]$WorkDir
    )
    $previous = $ErrorActionPreference
    Push-Location -LiteralPath $WorkDir
    try {
        $ErrorActionPreference = 'Continue'
        & $Exe @Arguments
        $code = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
        Pop-Location
    }
    if ($code -ne 0) {
        throw "Command failed ($code): $Exe $($Arguments -join ' ')"
    }
}

if (-not (Test-Path $Py)) {
    throw 'Virtualenv not found. Run .\scripts\bootstrap.ps1 first.'
}

Write-Step 'ruff check'
Invoke-Checked $Py @('-m', 'ruff', 'check', 'app', 'tests', 'scripts') $Backend

Write-Step 'pytest'
Invoke-Checked $Py @('-m', 'pytest', 'tests/', '-q') $Backend

if (-not $BackendOnly) {
    if (Test-Path (Join-Path $Frontend 'node_modules')) {
        Write-Step 'frontend build'
        Invoke-Checked 'npm' @('run', 'build') $Frontend
    } else {
        Write-Warning 'frontend/node_modules is missing, skip build.'
    }
}

Write-Host ''
Write-Host 'All checks passed.' -ForegroundColor Green
exit 0
