# NautiCAI — Deploy to AWS

Deploy the NautiCAI backend (FastAPI + ML) and frontend (React) to AWS. You get a public website and API.

**Architecture:**

- **Backend:** Docker image → Amazon ECR → **AWS App Runner** (managed container, 4 GB RAM, auto-scaling).
- **Frontend:** React build (with backend URL) → **S3 + CloudFront** or **Amplify Hosting**.

---

## Prerequisites

1. **AWS CLI** installed and configured:
   ```powershell
   # Install: https://aws.amazon.com/cli/
   aws configure
   # Enter Access Key ID, Secret, and default region (e.g. us-east-1)
   ```

2. **Docker** installed and running (to build images).

3. **Node.js** (for building the frontend).

---

## Quick deploy (script)

From project root in **Git Bash** or **WSL**:

```bash
chmod +x deploy-aws.sh
./deploy-aws.sh
```

The script will:

1. Create ECR repositories (if missing).
2. Build and push the **backend** image to ECR.
3. Deploy or update the **backend** on App Runner (and print the API URL).
4. Build the **frontend** with that API URL.
5. Give you exact **AWS CLI commands** to upload the frontend to S3 and (optionally) create a CloudFront distribution.

You still run the S3/CloudFront (or Amplify) steps once to publish the website — see **Step 4** below if you prefer doing everything manually.

---

## Manual deployment steps

### Step 1: Choose region and set variables

```powershell
$AWS_REGION = "us-east-1"
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query Account --output text)
$ECR_BACKEND = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/nauticai-backend"
$ECR_FRONTEND = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/nauticai-frontend"
```

---

### Step 2: Backend — ECR + App Runner

**2.1 Create ECR repository (if it doesn’t exist)**

```powershell
aws ecr describe-repositories --repository-names nauticai-backend --region $AWS_REGION 2>$null
if ($LASTEXITCODE -ne 0) {
  aws ecr create-repository --repository-name nauticai-backend --region $AWS_REGION
}
```

**2.2 Log in Docker to ECR**

```powershell
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
```

**2.3 Build and push backend image**

```powershell
docker build --platform linux/amd64 -f Dockerfile.backend -t nauticai-backend:latest .
docker tag nauticai-backend:latest "${ECR_BACKEND}:latest"
docker push "${ECR_BACKEND}:latest"
```

**2.4 Create App Runner service (first time only)**

App Runner needs permission to pull from ECR. Create an **access role** that allows `ecr:GetDownloadUrlForLayer` and `ecr:BatchGetImage` on your repo (or use the default `AppRunnerECRAccessRole` if your account has it). Then:

```powershell
# Create service (replace YOUR_ECR_ACCESS_ROLE_ARN if you use a custom role)
aws apprunner create-service `
  --service-name nauticai-api `
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'"${ECR_BACKEND}"':latest",
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": false
  }' `
  --instance-configuration '{
    "Cpu": "2 vCPU",
    "Memory": "4 GB"
  }' `
  --region $AWS_REGION
```

If you get an error about access role, in **AWS Console → App Runner → Create service → Source = Container registry (ECR)** use the same image and let the console create the IAM role for ECR access, then note the **Service URL**.

**2.5 Get backend URL**

```powershell
aws apprunner list-services --region $AWS_REGION --query "ServiceSummaryList[?ServiceName=='nauticai-api'].ServiceUrl" --output text
```

Or in **AWS Console → App Runner → nauticai-api → Default domain**. Example: `https://xxxxx.us-east-1.awsapprunner.com`.

Set this as your **backend URL** (e.g. `$BACKEND_URL`) for the frontend build.

**2.6 Later: update backend (new image)**

```powershell
docker build --platform linux/amd64 -f Dockerfile.backend -t nauticai-backend:latest .
docker tag nauticai-backend:latest "${ECR_BACKEND}:latest"
docker push "${ECR_BACKEND}:latest"

$SERVICE_ARN = (aws apprunner list-services --region $AWS_REGION --query "ServiceSummaryList[?ServiceName=='nauticai-api'].ServiceArn" --output text)
aws apprunner start-deployment --service-arn $SERVICE_ARN --region $AWS_REGION
```

---

### Step 3: Frontend — build with backend URL

Replace `YOUR_BACKEND_URL` with the App Runner URL (no trailing slash), e.g. `https://xxxxx.us-east-1.awsapprunner.com`:

**Option A — Build with npm (no Docker)**

```powershell
cd frontend
$env:REACT_APP_API_URL = "YOUR_BACKEND_URL"
npm install
npm run build
cd ..
# Static files are in frontend/build/
```

**Option B — Build with Docker**

```powershell
docker build --platform linux/amd64 -f Dockerfile.frontend --build-arg REACT_APP_API_URL=YOUR_BACKEND_URL -t nauticai-frontend:latest .
# Then copy build out of container, or push to ECR and use ECS/Amplify to serve
```

---

### Step 4: Host the frontend (website)

**Option A — S3 + CloudFront (static site)**

1. Create S3 bucket (e.g. `nauticai-web-yourname`), enable **Static website hosting**, index document `index.html`, error document `index.html` (for SPA).
2. Bucket policy: allow public read (for public website) or keep private and use only CloudFront.
3. Upload build:
   ```powershell
   aws s3 sync frontend/build/ s3://nauticai-web-yourname/ --delete
   ```
4. (Recommended) Create a **CloudFront** distribution with origin = S3 bucket or S3 website endpoint, default root `index.html`, and use the CloudFront URL as your website URL (e.g. `https://d1234abcd.cloudfront.net`).

**Option B — Amplify Hosting**

1. In **AWS Console → Amplify → Hosting → Get started**.
2. Connect your repo (GitHub/GitLab/etc.) or choose “Deploy without Git”.
3. If using Git: set build settings; set env var **`REACT_APP_API_URL`** = your App Runner backend URL; root directory = `frontend` (or build command `npm run build` and output `build`).
4. If deploying without Git: upload the contents of `frontend/build` (zip) or use the Amplify CLI to deploy the built app.

Your **website URL** will be the Amplify app URL (e.g. `https://main.xxxxx.amplifyapp.com`).

---

## Marketing website (About, Contact, Demo gate)

The `website/` folder is the landing page (Hero, How it works, About, Contact) and the **demo signup gate** (`demo.html`). Deploy it separately from the React app.

**For production:** After deploy, set on `<body>` in **both** `index.html` and `demo.html`:
- `data-app-url="https://your-react-app-url"` (inspection app URL)
- `data-api-url="https://your-backend-url"` (API URL for signup and footer status)

Example: `<body data-app-url="https://app.yourdomain.com" data-api-url="https://api.yourdomain.com">`. This makes “Try demo” redirect to the right app and the footer show “API Live” when the backend is up.

**Deploy to S3:**

```bash
# 1. Create bucket and enable static hosting (one-time)
aws s3 mb s3://nauticai-marketing-yourname --region us-east-1
aws s3 website s3://nauticai-marketing-yourname --index-document index.html --error-document index.html

# 2. Set bucket policy for public read (or use CloudFront with private bucket)
# See: https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteAccessPermissionsReqd.html

# 3. Deploy
export NAUTICAI_WEBSITE_BUCKET=nauticai-marketing-yourname
./deploy-website-aws.sh
```

**Run locally:**

```powershell
.\run-website.ps1
# Opens http://localhost:8080
```

**Contact form:** Uses mailto: (opens default email client). Change the email in `website/index.html` — set `data-mailto="your@email.com"` on the form.

---

## Summary

| Component        | AWS service        | Result                          |
|-----------------|--------------------|----------------------------------|
| Backend API     | ECR + App Runner   | `https://xxxxx.awsapprunner.com` |
| React app       | S3 + CloudFront or Amplify | Detection platform URL   |
| Marketing site  | S3 (optional CloudFront) | Landing page (About, Contact)   |

**Cost:** App Runner and S3/CloudFront/Amplify have free tiers; beyond that you pay for usage. Set billing alerts in **AWS Billing**.

---

## Troubleshooting

- **App Runner “Unable to pull image”:** Ensure the ECR repository allows App Runner to pull (IAM role with `ecr:GetDownloadUrlForLayer` and `ecr:BatchGetImage`). Use the console once to create the service and the default ECR access role.
- **Frontend can’t reach API:** Confirm `REACT_APP_API_URL` was set at **build** time and matches the App Runner URL (HTTPS, no trailing slash). Check browser Network tab for failed requests to the API.
- **CORS:** The backend already allows all origins; if you restrict later, add your CloudFront/Amplify origin.

For local run and other clouds, see [DEPLOY.md](DEPLOY.md).
