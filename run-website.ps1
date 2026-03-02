# NautiCAI - Run marketing website + backend (so demo signup and alerts work)
# From project root. Opens backend in a new window, then serves website here.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$website = Join-Path $root "website"

if (-not (Test-Path (Join-Path $website "index.html"))) {
    Write-Error "website/index.html not found. Run from project root."
    exit 1
}

Write-Host ""
Write-Host "=== NautiCAI - Website + Backend ===" -ForegroundColor Cyan
Write-Host ""

# Start backend in new window (needed for signup and WhatsApp test alert)
Write-Host "[1/2] Starting backend (port 8000) in new window..." -ForegroundColor Yellow
$backendCmd = "cd '$root'; python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Write-Host "      Waiting for backend to be ready..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Serve website in this window
Write-Host "[2/2] Starting marketing site (port 8080) here..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  Open in browser:  http://localhost:8080" -ForegroundColor Green
Write-Host "  Try demo, sign up, then open React app at http://localhost:3000 if needed" -ForegroundColor Gray
Write-Host "  To run React app: open new terminal, cd frontend, npm start" -ForegroundColor Gray
Write-Host ""
$msg = "Press Ctrl+C to stop the website. Close the backend window to stop the API."
Write-Host $msg -ForegroundColor Gray
Write-Host ""

Push-Location $website
try { python -m http.server 8080 } finally { Pop-Location }
