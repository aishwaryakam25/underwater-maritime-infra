# Start FastAPI (8000) + React (3000). Run from project root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\start-nauticai.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "NautiCAI — starting backend + frontend" -ForegroundColor Cyan
Write-Host ""

$py = "python"
if (Test-Path (Join-Path $root "venv\Scripts\activate.ps1")) {
    Write-Host "Using venv Python..." -ForegroundColor Gray
    $py = Join-Path $root "venv\Scripts\python.exe"
}

$backendCmd = @"
Set-Location '$root'
& '$py' -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
"@

Write-Host "[1/2] Backend http://127.0.0.1:8000 (new window)" -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 4

$frontendCmd = @"
Set-Location '$root\frontend'
npm start
"@

Write-Host "[2/2] Frontend http://localhost:3000 (new window)" -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "Wait until React shows 'Compiled successfully', then open:" -ForegroundColor Green
Write-Host "  http://localhost:3000" -ForegroundColor White
Write-Host ""
Write-Host "Sonar / Combined tabs need the API on port 8000 (CRA proxies /api from :3000)." -ForegroundColor Gray
Write-Host ""
