# NautiCAI — Local demo (no Cloud Run, works in any browser / incognito)
# Run from repo root. Uses backend on :8000, frontend on :3000 with proxy to backend.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host "=== 1. Backend (port 8000) ===" -ForegroundColor Cyan
if (-not (Test-Path "venv")) {
    python -m venv venv
}
& "$root\venv\Scripts\Activate.ps1"
pip install -q -r backend\requirements.txt
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; .\venv\Scripts\Activate.ps1; uvicorn backend.main:app --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 3

Write-Host "=== 2. Frontend (port 3000, proxy to backend) ===" -ForegroundColor Cyan
Set-Location frontend
npm start
