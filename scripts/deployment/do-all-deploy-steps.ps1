# Do all steps for GitHub -> Cloud Run deploy
# Run from project root. Step 1 runs here; Steps 2-8 you do in browser/console.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
Set-Location $root

Write-Host ""
Write-Host "=== NautiCAI - All steps for Cloud Run (GitHub style) ===" -ForegroundColor Cyan
Write-Host ""

# --- STEP 1: Push to GitHub ---
Write-Host "[STEP 1/8] Push code to GitHub..." -ForegroundColor Yellow
$remote = (git remote get-url origin 2>$null)
if (-not $remote) {
    Write-Host "  No git remote. Add one first: git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git" -ForegroundColor Red
    exit 1
}
Write-Host "  Remote: $remote" -ForegroundColor Gray

git add -A
git status -s
$count = (git status -s | Measure-Object -Line).Lines
if ($count -eq 0) {
    Write-Host "  Nothing to commit (already clean)." -ForegroundColor Gray
} else {
    git commit -m "Add Dockerfile, deploy scripts, website, GCP and GitHub deploy docs"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  Commit failed or nothing to commit." -ForegroundColor Gray
    } else {
        git push origin main
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  Push failed. Check: git push origin main" -ForegroundColor Red
            exit 1
        }
        Write-Host "  Pushed to GitHub." -ForegroundColor Green
    }
}
Write-Host ""

# --- Steps 2-8: In browser ---
Write-Host "[STEP 2/8] Create GCP project (in browser)" -ForegroundColor Yellow
Write-Host "  Open: https://console.cloud.google.com" -ForegroundColor Gray
Write-Host "  Create project (e.g. underwater-maritime-infra). Note Project ID." -ForegroundColor Gray
Write-Host ""

Write-Host "[STEP 3/8] Connect GitHub to Google Cloud" -ForegroundColor Yellow
Write-Host "  Cloud Run -> Create Service" -ForegroundColor Gray
Write-Host "  Source: Continuously deploy from a repository" -ForegroundColor Gray
Write-Host "  Connect repository -> GitHub -> Authorize -> Select: underwater-maritime-infra (or your repo)" -ForegroundColor Gray
Write-Host "  Branch: main. Save." -ForegroundColor Gray
Write-Host ""

Write-Host "[STEP 4/8] Build settings" -ForegroundColor Yellow
Write-Host "  Build type: Docker (Dockerfile at repo root)" -ForegroundColor Gray
Write-Host "  Build context: . (root)" -ForegroundColor Gray
Write-Host "  Service name: nauticai-api" -ForegroundColor Gray
Write-Host "  Region: e.g. us-central1" -ForegroundColor Gray
Write-Host "  Authentication: Allow unauthenticated invocations" -ForegroundColor Gray
Write-Host "  Create / Deploy" -ForegroundColor Gray
Write-Host ""

Write-Host "[STEP 5/8] If deploy fails with IAM error" -ForegroundColor Yellow
Write-Host "  IAM and Admin -> IAM -> Find default compute service account" -ForegroundColor Gray
Write-Host "  Edit -> Add role: Cloud Run Admin" -ForegroundColor Gray
Write-Host "  Add role: Service Account User" -ForegroundColor Gray
Write-Host "  Save. Then push a new commit or Redeploy in Cloud Run." -ForegroundColor Gray
Write-Host ""

Write-Host "[STEP 6/8] After deploy succeeds" -ForegroundColor Yellow
Write-Host "  Copy the Cloud Run URL (e.g. https://nauticai-api-xxxxx-uc.a.run.app)" -ForegroundColor Gray
Write-Host "  Test: open that URL + /api/health in browser" -ForegroundColor Gray
Write-Host ""

Write-Host "[STEP 7/8] Set env vars (Cloud Run console)" -ForegroundColor Yellow
Write-Host "  Cloud Run -> nauticai-api -> Edit and deploy new revision" -ForegroundColor Gray
Write-Host "  Variables: NAUTICAI_BASE_URL = your Cloud Run URL (no trailing slash)" -ForegroundColor Gray
Write-Host "  Optional: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM" -ForegroundColor Gray
Write-Host ""

Write-Host "[STEP 8/8] Update website with backend URL" -ForegroundColor Yellow
Write-Host "  Edit website/index.html and website/demo.html: set data-api-url to your Cloud Run URL" -ForegroundColor Gray
Write-Host "  Or run: .\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID -BackendOnly" -ForegroundColor Gray
Write-Host "  (Then deploy website to Firebase: firebase deploy --only hosting)" -ForegroundColor Gray
Write-Host ""

Write-Host "Step 1 (push) is done. Do Steps 2-8 in the browser/console as above." -ForegroundColor Green
Write-Host "Full guide: DEPLOY-GCP-GITHUB.md" -ForegroundColor Gray
Write-Host ""
