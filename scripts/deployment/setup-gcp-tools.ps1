# NautiCAI - Install tools needed for Google Cloud deployment
# Run in PowerShell. Some steps may prompt for Administrator (UAC).
# After running, close and reopen PowerShell (or restart terminal) so gcloud is on PATH.

$ErrorActionPreference = "Stop"
Write-Host ""
Write-Host "=== NautiCAI - GCP deployment tools installer ===" -ForegroundColor Cyan
Write-Host ""

# 1. Google Cloud SDK
Write-Host "[1/4] Google Cloud SDK (gcloud)..." -ForegroundColor Yellow
$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if ($gcloud) {
    Write-Host "  Already installed: $($gcloud.Source)" -ForegroundColor Green
} else {
    Write-Host "  Installing via winget (you may see a UAC prompt)..." -ForegroundColor Gray
    winget install -e --id Google.CloudSDK --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "  winget install failed. Install manually: https://cloud.google.com/sdk/docs/install"
    } else {
        Write-Host "  Installed. Restart PowerShell so 'gcloud' is on PATH." -ForegroundColor Green
    }
}

# 2. Docker
Write-Host "[2/4] Docker..." -ForegroundColor Yellow
$docker = Get-Command docker -ErrorAction SilentlyContinue
if ($docker) {
    Write-Host "  Already installed." -ForegroundColor Green
} else {
    Write-Host "  Installing via winget (Docker Desktop - you may see UAC prompt)..." -ForegroundColor Gray
    winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "  winget install failed. Install manually: https://docs.docker.com/desktop/install/windows-install/ or from Microsoft Store (search Docker Desktop)."
    } else {
        Write-Host "  Installed. Start Docker Desktop from the Start menu, then restart PowerShell." -ForegroundColor Green
    }
}

# 3. Node.js (for Firebase CLI)
Write-Host "[3/4] Node.js (for Firebase CLI)..." -ForegroundColor Yellow
$node = Get-Command node -ErrorAction SilentlyContinue
if ($node) {
    Write-Host "  Already installed: $(node --version)" -ForegroundColor Green
} else {
    Write-Host "  Installing via winget..." -ForegroundColor Gray
    winget install -e --id OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "  winget install failed. Install manually: https://nodejs.org"
    } else {
        Write-Host "  Installed. Restart PowerShell so 'node' and 'npm' are on PATH." -ForegroundColor Green
    }
}

# 4. Firebase CLI (requires Node)
Write-Host "[4/4] Firebase CLI..." -ForegroundColor Yellow
$firebase = Get-Command firebase -ErrorAction SilentlyContinue
if ($firebase) {
    Write-Host "  Already installed." -ForegroundColor Green
} else {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if ($npm) {
        Write-Host "  Installing firebase-tools globally..." -ForegroundColor Gray
        npm install -g firebase-tools
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "  npm install failed. Run manually: npm install -g firebase-tools"
        } else {
            Write-Host "  Installed." -ForegroundColor Green
        }
    } else {
        Write-Host "  Skipped (Node.js not found). Install Node.js first, restart PowerShell, then run: npm install -g firebase-tools" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "=== Next steps ===" -ForegroundColor Cyan
Write-Host "  1. Close and reopen PowerShell (so gcloud, docker, node are on PATH)."
Write-Host "  2. Log in to Google Cloud:  gcloud auth login"
Write-Host "  3. Set your project:        gcloud config set project YOUR_PROJECT_ID"
Write-Host "  4. Deploy:                 .\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID"
Write-Host ""
