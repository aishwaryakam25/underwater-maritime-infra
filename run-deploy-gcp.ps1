# Run this to set your GCP project and deploy in one go.
# You only need to paste your Project ID when asked.
# Use the same PowerShell window where gcloud works (after setup-gcp-tools.ps1).

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Push-Location $root

Write-Host ""
Write-Host "=== NautiCAI - Set project and deploy ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Paste your Google Cloud Project ID (from https://console.cloud.google.com, project dropdown)." -ForegroundColor Gray
Write-Host "Example: nauticai-demo-123456" -ForegroundColor Gray
Write-Host ""
$projectId = Read-Host "Project ID"
$projectId = $projectId.Trim()
if ([string]::IsNullOrWhiteSpace($projectId)) {
    Write-Error "Project ID is required."
    exit 1
}

Write-Host ""
Write-Host "Setting project to: $projectId" -ForegroundColor Yellow
& gcloud config set project $projectId
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set project. Check that the Project ID is correct and you are logged in (gcloud auth login)."
    Pop-Location
    exit 1
}

Write-Host ""
Write-Host "Starting deployment..." -ForegroundColor Yellow
& "$root\deploy-gcp.ps1" -ProjectId $projectId
$exitCode = $LASTEXITCODE
Pop-Location
exit $exitCode
