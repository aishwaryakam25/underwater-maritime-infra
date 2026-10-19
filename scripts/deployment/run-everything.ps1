# NautiCAI — Run everything locally (backend + React app + marketing site)
# From project root. Opens 3 processes; use the URLs below.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host ""
Write-Host "=== NautiCAI — Starting all services ===" -ForegroundColor Cyan
Write-Host ""

# 1. Backend (new window)
Write-Host "[1/3] Starting backend (port 8000) in new window..." -ForegroundColor Yellow
$backendCmd = "cd '$root'; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 2

# 2. React app (new window)
Write-Host "[2/3] Starting React app (port 3000) in new window..." -ForegroundColor Yellow
$frontendCmd = "cd '$root\frontend'; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Start-Sleep -Seconds 3

# 3. Marketing site (this window)
Write-Host "[3/3] Starting marketing site (port 8080) here..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Marketing site:  http://localhost:8080  (open in browser)" -ForegroundColor Green
Write-Host "  React app:       http://localhost:3000  (Try demo from marketing site)" -ForegroundColor Green
Write-Host "  Backend API:     http://localhost:8000  (docs: /docs)" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop this server only. Close the other two windows to stop all." -ForegroundColor Gray
Write-Host ""

$website = Join-Path $root "website"
Push-Location $website
try { python -m http.server 8080 } finally { Pop-Location }
