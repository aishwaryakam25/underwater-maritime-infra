# NautiCAI - Deploy to Google Cloud (backend + website files + env vars)
# Run from project root. Requires: gcloud CLI, Docker, and (for website) Firebase CLI.
# Usage:
#   .\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID
#   .\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID -TwilioSid ACxxx -TwilioToken secret -TwilioFrom "whatsapp:+14155238886"

param(
    [Parameter(Mandatory = $false)]
    [string] $ProjectId,
    [string] $Region = "us-central1",
    [string] $TwilioSid = "",
    [string] $TwilioToken = "",
    [string] $TwilioFrom = "",
    [switch] $SkipFirebase,
    [switch] $BackendOnly
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# Validate project root
if (-not (Test-Path (Join-Path $root "Dockerfile")) -or -not (Test-Path (Join-Path $root "website\index.html"))) {
    Write-Error "Run from project root (folder with Dockerfile and website/)."
    exit 1
}

Write-Host ""
Write-Host "=== NautiCAI - Google Cloud deployment ===" -ForegroundColor Cyan
Write-Host ""

# Resolve project ID
if (-not $ProjectId) {
    $ProjectId = Read-Host "Enter your Google Cloud Project ID"
    if ([string]::IsNullOrWhiteSpace($ProjectId)) {
        Write-Error "Project ID is required."
        exit 1
    }
}

# Check gcloud
$gcloud = Get-Command gcloud -ErrorAction SilentlyContinue
if (-not $gcloud) {
    Write-Error "gcloud CLI not found. Install from https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Check docker
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Write-Error "Docker not found. Install Docker and ensure it is running."
    exit 1
}

# Set project (ignore environment-tag warning; gcloud may still exit non-zero)
Write-Host "[1/9] Setting project to $ProjectId..." -ForegroundColor Yellow
& gcloud config set project $ProjectId 2>&1 | Out-Null
$currentProject = (gcloud config get-value project 2>$null)
if ($currentProject -ne $ProjectId) {
    Write-Error "Failed to set project. Run: gcloud auth login"
    exit 1
}
Write-Host "  Project set. (Ignore environment-tag message if shown; deploy will continue.)" -ForegroundColor Gray

# Enable APIs
Write-Host "[2/9] Enabling APIs..." -ForegroundColor Yellow
& gcloud services enable run.googleapis.com artifactregistry.googleapis.com firebasehosting.googleapis.com --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Some APIs may already be enabled or need billing. Continuing."
}

# Artifact Registry repo (ignore if exists)
Write-Host "[3/9] Configuring Artifact Registry..." -ForegroundColor Yellow
& gcloud artifacts repositories create nauticai-repo --repository-format=docker --location=$Region 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    $err = $Error[0].ToString()
    if ($err -notmatch "already exists") {
        Write-Warning "Could not create repo (may already exist). Continuing."
    }
}
& gcloud auth configure-docker "${Region}-docker.pkg.dev" --quiet 2>&1 | Out-Null

# Build and push image
$IMAGE = "${Region}-docker.pkg.dev/${ProjectId}/nauticai-repo/nauticai-backend:latest"
Write-Host "[4/9] Building Docker image (this may take several minutes)..." -ForegroundColor Yellow
Push-Location $root
try {
    & docker build --platform linux/amd64 -t $IMAGE -f Dockerfile . 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Docker build failed." }
} finally {
    Pop-Location
}
Write-Host "[5/9] Pushing image to Artifact Registry..." -ForegroundColor Yellow
& docker push $IMAGE 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker push failed. Ensure you are logged in: gcloud auth configure-docker ${Region}-docker.pkg.dev"
    exit 1
}

# Deploy to Cloud Run
Write-Host "[6/9] Deploying to Cloud Run..." -ForegroundColor Yellow
& gcloud run deploy nauticai-api `
    --image $IMAGE `
    --region $Region `
    --platform managed `
    --allow-unauthenticated `
    --memory 4Gi `
    --cpu 2 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Cloud Run deploy failed."
    exit 1
}

# Get service URL
$BackendUrl = (gcloud run services describe nauticai-api --region $Region --format "value(status.url)" 2>$null)
if (-not $BackendUrl) {
    Write-Error "Could not get Cloud Run service URL."
    exit 1
}
$BackendUrl = $BackendUrl.Trim().TrimEnd("/")
Write-Host ""
Write-Host "  Backend URL: $BackendUrl" -ForegroundColor Green
Write-Host ""

# Set env vars on Cloud Run
Write-Host "[7/9] Setting Cloud Run env vars (NAUTICAI_BASE_URL + optional Twilio)..." -ForegroundColor Yellow
$envVars = "NAUTICAI_BASE_URL=$BackendUrl"
if (-not [string]::IsNullOrWhiteSpace($TwilioSid) -and -not [string]::IsNullOrWhiteSpace($TwilioToken) -and -not [string]::IsNullOrWhiteSpace($TwilioFrom)) {
    $envVars += ",TWILIO_ACCOUNT_SID=$TwilioSid,TWILIO_AUTH_TOKEN=$TwilioToken,TWILIO_WHATSAPP_FROM=$TwilioFrom"
    Write-Host "  Including Twilio vars for WhatsApp." -ForegroundColor Gray
} else {
    Write-Host "  Twilio not set; add in Console later for WhatsApp (see WHATSAPP_SETUP.md)." -ForegroundColor Gray
}
& gcloud run services update nauticai-api --region $Region --set-env-vars $envVars --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Env vars update failed; set them manually in Cloud Run Console."
}

if (-not $BackendOnly) {
    # Update website HTML with backend URL
    Write-Host "[8/9] Updating website/index.html and website/demo.html with data-api-url..." -ForegroundColor Yellow
    $indexPath = Join-Path $root "website\index.html"
    $demoPath = Join-Path $root "website\demo.html"
    $patternEmpty = "data-api-url=`"`""
    $patternAny = "data-api-url=`"[^`"]*`""
    $replacement = "data-api-url=`"$BackendUrl`""
    foreach ($path in @($indexPath, $demoPath)) {
        if (Test-Path $path) {
            $content = Get-Content $path -Raw -Encoding UTF8
            $content = $content -replace $patternEmpty, $replacement
            $content = $content -replace $patternAny, $replacement
            Set-Content $path $content -NoNewline -Encoding UTF8
        }
    }
    Write-Host "  Set data-api-url=$BackendUrl" -ForegroundColor Gray
}

# Firebase deploy (optional)
Write-Host "[9/9] Firebase Hosting..." -ForegroundColor Yellow
if ($SkipFirebase -or $BackendOnly) {
    Write-Host "  Skipped (use -SkipFirebase to skip when running manually)." -ForegroundColor Gray
} else {
    $firebaseJson = Join-Path $root "firebase.json"
    if (Test-Path $firebaseJson) {
        $firebase = Get-Command firebase -ErrorAction SilentlyContinue
        if ($firebase) {
            Push-Location $root
            try {
                & firebase deploy --only hosting 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "  Website deployed to Firebase Hosting." -ForegroundColor Green
                } else {
                    Write-Warning "Firebase deploy failed. Run manually: firebase deploy --only hosting"
                }
            } finally {
                Pop-Location
            }
        } else {
            Write-Host "  Firebase CLI not found. To deploy website: npm install -g firebase-tools, firebase login, firebase init hosting (public dir: website), then firebase deploy --only hosting" -ForegroundColor Gray
        }
    } else {
        Write-Host "  No firebase.json. First time: run firebase init hosting (public directory: website), then run this script again or run firebase deploy --only hosting." -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "=== Deployment summary ===" -ForegroundColor Cyan
Write-Host "  Backend (API):  $BackendUrl" -ForegroundColor Green
Write-Host "  Health check:   $BackendUrl/api/health" -ForegroundColor Gray
if (-not $BackendOnly) {
    Write-Host "  Website files:  data-api-url updated in website/index.html and website/demo.html" -ForegroundColor Gray
    $siteUrl = 'https://' + $ProjectId + '.web.app'
    Write-Host ('  Next: If you use Firebase, run: firebase deploy --only hosting. Site: ' + $siteUrl) -ForegroundColor Gray
}
Write-Host ""
