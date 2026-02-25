#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════
# NautiCAI — Google Cloud Run Deployment Script
# ═══════════════════════════════════════════════════════════════════════
# Prerequisites:
#   1. Google Cloud SDK (gcloud) installed
#   2. You are authenticated: gcloud auth login
#   3. A GCP project is set: gcloud config set project YOUR_PROJECT_ID
# ═══════════════════════════════════════════════════════════════════════

set -e

# ── Configuration ─────────────────────────────────────────────────────
PROJECT_ID=$(gcloud config get-value project)
REGION="asia-southeast1"    # Singapore (closest to your team)
BACKEND_SERVICE="nauticai-api"
FRONTEND_SERVICE="nauticai-web"
BACKEND_IMAGE="gcr.io/${PROJECT_ID}/${BACKEND_SERVICE}"
FRONTEND_IMAGE="gcr.io/${PROJECT_ID}/${FRONTEND_SERVICE}"

echo "═══════════════════════════════════════════════════"
echo "  NautiCAI — Deploying to Google Cloud Run"
echo "  Project:  ${PROJECT_ID}"
echo "  Region:   ${REGION}"
echo "═══════════════════════════════════════════════════"

# ── Step 1: Enable required APIs ──────────────────────────────────────
echo "[1/6] Enabling Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  containerregistry.googleapis.com \
  cloudbuild.googleapis.com

# ── Step 2: Build & push backend image ────────────────────────────────
echo "[2/6] Building backend Docker image..."
gcloud builds submit \
  --tag "${BACKEND_IMAGE}" \
  --timeout=1200 \
  -f Dockerfile.backend .

# ── Step 3: Deploy backend to Cloud Run ───────────────────────────────
echo "[3/6] Deploying backend to Cloud Run..."
gcloud run deploy "${BACKEND_SERVICE}" \
  --image "${BACKEND_IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --timeout 120 \
  --max-instances 5 \
  --port 8000

# Get the backend URL
BACKEND_URL=$(gcloud run services describe "${BACKEND_SERVICE}" \
  --region "${REGION}" --format="value(status.url)")
echo "Backend deployed at: ${BACKEND_URL}"

# ── Step 4: Build frontend with backend URL baked in ──────────────────
echo "[4/6] Building frontend Docker image..."
gcloud builds submit \
  --tag "${FRONTEND_IMAGE}" \
  --timeout=600 \
  -f Dockerfile.frontend \
  --substitutions="_REACT_APP_API_URL=${BACKEND_URL}" \
  .

# ── Step 5: Deploy frontend to Cloud Run ──────────────────────────────
echo "[5/6] Deploying frontend to Cloud Run..."
gcloud run deploy "${FRONTEND_SERVICE}" \
  --image "${FRONTEND_IMAGE}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 60 \
  --max-instances 10 \
  --port 80

FRONTEND_URL=$(gcloud run services describe "${FRONTEND_SERVICE}" \
  --region "${REGION}" --format="value(status.url)")

# ── Step 6: Done ──────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo "  ✅ DEPLOYMENT COMPLETE!"
echo ""
echo "  Frontend:  ${FRONTEND_URL}"
echo "  Backend:   ${BACKEND_URL}"
echo "  API Docs:  ${BACKEND_URL}/docs"
echo "═══════════════════════════════════════════════════"
