#Requires -Version 5.1
<#
.SYNOPSIS
    Start backend (uvicorn --reload) and frontend (vite) in two windows.

.EXAMPLE
    .\scripts\dev.ps1
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root 'backend'
$Frontend = Join-Path $Root 'frontend'
$Py = Join-Path $Backend '.venv\Scripts\python.exe'

if (-not (Test-Path $Py)) {
    throw 'Virtualenv not found. Run .\scripts\bootstrap.ps1 first.'
}

$Shell = (Get-Process -Id $PID).Path
$BackendCommand = "Set-Location -LiteralPath '$Backend'; & '$Py' -m uvicorn app.main:app --reload --port 8000"
$FrontendCommand = "Set-Location -LiteralPath '$Frontend'; npm run dev"

Start-Process -FilePath $Shell -ArgumentList @('-NoExit', '-Command', "`"$BackendCommand`"") | Out-Null
Start-Process -FilePath $Shell -ArgumentList @('-NoExit', '-Command', "`"$FrontendCommand`"") | Out-Null

Write-Host 'Backend : http://127.0.0.1:8000/docs'
Write-Host 'Frontend: http://localhost:5173'
Write-Host 'Close the two spawned windows to stop the servers.'
