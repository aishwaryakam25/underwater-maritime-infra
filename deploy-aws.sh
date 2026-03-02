#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# NautiCAI — AWS Deployment (ECR + App Runner + frontend build)
# ═══════════════════════════════════════════════════════════════════════
# Prerequisites: AWS CLI configured, Docker running, Node.js for frontend.
# Run from project root (Git Bash or WSL on Windows).
# ═══════════════════════════════════════════════════════════════════════

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
BACKEND_ECR_REPO="nauticai-backend"
APP_RUNNER_SERVICE_NAME="nauticai-api"

echo "═══════════════════════════════════════════════════"
echo "  NautiCAI — Deploying to AWS"
echo "  Region: ${AWS_REGION}"
echo "═══════════════════════════════════════════════════"

# ── Resolve account and ECR URIs ─────────────────────────────────────
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
BACKEND_IMAGE="${ECR_URI}/${BACKEND_ECR_REPO}:latest"

# ── Step 1: ECR repository ─────────────────────────────────────────────
echo "[1/5] Ensuring ECR repository exists..."
aws ecr describe-repositories --repository-names "${BACKEND_ECR_REPO}" --region "${AWS_REGION}" 2>/dev/null || \
  aws ecr create-repository --repository-name "${BACKEND_ECR_REPO}" --region "${AWS_REGION}"

# ── Step 2: Docker login to ECR ────────────────────────────────────────
echo "[2/5] Logging Docker into ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | \
  docker login --username AWS --password-stdin "${ECR_URI}"

# ── Step 3: Build and push backend ────────────────────────────────────
echo "[3/5] Building and pushing backend image..."
docker build --platform linux/amd64 -f Dockerfile.backend -t "${BACKEND_ECR_REPO}:latest" .
docker tag "${BACKEND_ECR_REPO}:latest" "${BACKEND_IMAGE}"
docker push "${BACKEND_IMAGE}"

# ── Step 4: App Runner (update if service exists, else instruct) ───────
echo "[4/5] App Runner..."
SERVICE_ARN=$(aws apprunner list-services --region "${AWS_REGION}" --query "ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceArn" --output text 2>/dev/null || true)

if [ -n "${SERVICE_ARN}" ]; then
  echo "      Starting deployment for existing service: ${APP_RUNNER_SERVICE_NAME}"
  aws apprunner start-deployment --service-arn "${SERVICE_ARN}" --region "${AWS_REGION}" --output text
  echo "      Wait 2–5 min for the deployment to become RUNNING. Check: AWS Console → App Runner → ${APP_RUNNER_SERVICE_NAME}"
else
  echo "      No App Runner service named '${APP_RUNNER_SERVICE_NAME}' found."
  echo "      Create it once (Console or CLI). You need an IAM role that allows App Runner to pull from ECR."
  echo ""
  echo "      Option A — AWS Console:"
  echo "        1. App Runner → Create service"
  echo "        2. Source: Container registry → Amazon ECR"
  echo "        3. Select repository: ${BACKEND_ECR_REPO}, image: latest"
  echo "        4. Let the console create the ECR access role, then Create."
  echo ""
  echo "      Option B — CLI (set NAUTICAI_APP_RUNNER_ACCESS_ROLE_ARN to your ECR access role ARN):"
  echo "        aws apprunner create-service --service-name ${APP_RUNNER_SERVICE_NAME} \\"
  echo "          --source-configuration '{\"ImageRepository\":{\"ImageIdentifier\":\"${BACKEND_IMAGE}\",\"ImageRepositoryType\":\"ECR\"},\"AuthenticationConfiguration\":{\"AccessRoleArn\":\"${NAUTICAI_APP_RUNNER_ACCESS_ROLE_ARN}\"}}' \\"
  echo "          --instance-configuration '{\"Cpu\":\"2 vCPU\",\"Memory\":\"4 GB\"}' --region ${AWS_REGION}"
  echo ""
fi

# Get backend URL if service exists (may still be deploying)
BACKEND_URL=""
SERVICE_URL=$(aws apprunner list-services --region "${AWS_REGION}" --query "ServiceSummaryList[?ServiceName=='${APP_RUNNER_SERVICE_NAME}'].ServiceUrl" --output text 2>/dev/null || true)
if [ -n "${SERVICE_URL}" ]; then
  BACKEND_URL="https://${SERVICE_URL}"
  echo "      Backend URL (use for frontend): ${BACKEND_URL}"
fi

# ── Step 5: Frontend build ─────────────────────────────────────────────
echo "[5/5] Frontend build..."
if [ -z "${BACKEND_URL}" ]; then
  echo "      No backend URL yet. After App Runner is RUNNING, get the URL from the console and run:"
  echo "        cd frontend && REACT_APP_API_URL=https://YOUR_APP_RUNNER_URL npm run build && cd .."
  echo "      Then upload frontend/build/ to S3 or deploy via Amplify (see DEPLOY-AWS.md)."
else
  (
    cd frontend
    export REACT_APP_API_URL="${BACKEND_URL}"
    npm install --silent
    npm run build
  )
  echo ""
  echo "      Frontend built in frontend/build/."
  echo "      To publish the website (choose one):"
  echo ""
  echo "      S3 + optional CloudFront:"
  echo "        aws s3 sync frontend/build/ s3://YOUR-BUCKET-NAME/ --delete"
  echo "        (Then enable static hosting on the bucket or put CloudFront in front.)"
  echo ""
  echo "      Amplify: Use AWS Console → Amplify → Hosting, connect repo or upload frontend/build."
  echo "        Set env REACT_APP_API_URL=${BACKEND_URL} if building from Amplify."
fi

echo ""
echo "═══════════════════════════════════════════════════"
echo "  Backend image: ${BACKEND_IMAGE}"
echo "  Full steps: see DEPLOY-AWS.md"
echo "═══════════════════════════════════════════════════"
