#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# NautiCAI — Deploy marketing website to S3 (+ optional CloudFront)
# ═══════════════════════════════════════════════════════════════════════
# Prerequisites: AWS CLI configured. Run from project root.
# ═══════════════════════════════════════════════════════════════════════

set -e

AWS_REGION="${AWS_REGION:-us-east-1}"
BUCKET_NAME="${NAUTICAI_WEBSITE_BUCKET:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBSITE_DIR="${SCRIPT_DIR}/website"

if [ -z "${BUCKET_NAME}" ]; then
  echo "Set NAUTICAI_WEBSITE_BUCKET to your S3 bucket name, e.g.:"
  echo "  export NAUTICAI_WEBSITE_BUCKET=nauticai-website-yourname"
  echo "  ./deploy-website-aws.sh"
  echo ""
  echo "The bucket must exist and have static website hosting enabled."
  exit 1
fi

echo "═══════════════════════════════════════════════════"
echo "  NautiCAI — Deploying marketing website to S3"
echo "  Bucket: ${BUCKET_NAME}"
echo "═══════════════════════════════════════════════════"

# Sync website folder to S3 (public read for static site)
aws s3 sync "${WEBSITE_DIR}/" "s3://${BUCKET_NAME}/" \
  --delete \
  --region "${AWS_REGION}" \
  --acl public-read

echo ""
echo "✅ Deployed to S3."
echo ""
echo "Website URLs (depends on your bucket config):"
echo "  S3 website:  http://${BUCKET_NAME}.s3-website-${AWS_REGION}.amazonaws.com"
echo "  or:          http://${BUCKET_NAME}.s3-website.${AWS_REGION}.amazonaws.com"
echo ""
echo "For custom domain + HTTPS: put CloudFront in front of this bucket."
