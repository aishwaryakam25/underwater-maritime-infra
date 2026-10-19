# Run before your demo (from repo root or any path).
# 1) Automated: backend import + /api/health + frontend production build
# 2) Manual: start API in another window, then open React dev server

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "`n=== NautiCAI pre-demo health ===" -ForegroundColor Cyan
python scripts/check_stack_health.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nFix errors above before the meeting." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n--- Manual steps for live demo ---" -ForegroundColor Yellow
Write-Host "Terminal A (backend):" -ForegroundColor Gray
Write-Host "  cd `"$root`"" -ForegroundColor White
Write-Host "  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host "`nTerminal B (frontend dev, proxy to 8000):" -ForegroundColor Gray
Write-Host "  cd `"$root\frontend`"" -ForegroundColor White
Write-Host "  npm start" -ForegroundColor White
Write-Host "`nThen open http://localhost:3000 and confirm detection runs." -ForegroundColor Green
Write-Host "Quick API check (with backend running):" -ForegroundColor Gray
Write-Host "  curl http://127.0.0.1:8000/api/health" -ForegroundColor White
