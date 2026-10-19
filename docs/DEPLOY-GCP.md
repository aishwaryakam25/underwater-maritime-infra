# NautiCAI — Deploy to Google Cloud

Deploy the NautiCAI backend (FastAPI + ML) and marketing website to Google Cloud. You get a public API and site with HTTPS.

**Two ways to deploy the backend:**
- **From GitHub (video-style):** Push to GitHub → Cloud Run “Connect repository” → automatic deploy on every push. No Docker on your PC. See **[DEPLOY-GCP-GITHUB.md](DEPLOY-GCP-GITHUB.md)**.
- **From your PC (script):** Run `.\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID` to build the Docker image locally, push to Artifact Registry, and deploy. See below.

---

## One-script deploy (recommended if not using GitHub)

From **project root** in PowerShell:

```powershell
.\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID
```

The script will: set project, enable APIs, create Artifact Registry repo, build and push the Docker image, deploy to Cloud Run, set `NAUTICAI_BASE_URL` (and optional Twilio vars), and update `website/index.html` and `website/demo.html` with your backend URL. If `firebase.json` exists and Firebase CLI is installed, it will run `firebase deploy --only hosting` too.

**With WhatsApp (Twilio):**
```powershell
.\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID -TwilioSid ACxxxx -TwilioToken your_token -TwilioFrom "whatsapp:+14155238886"
```

**Backend only (no website file updates):** `.\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID -BackendOnly`  
**Skip Firebase deploy:** `.\deploy-gcp.ps1 -ProjectId YOUR_PROJECT_ID -SkipFirebase`

**First time:** Ensure you have run `gcloud auth login` and that Docker is running. For Firebase Hosting, run `firebase init hosting` once (public directory: `website`), then run the script again or run `firebase deploy --only hosting` yourself.

---

## Step-by-step (in order)

Do these in sequence from the **project root** (the folder that contains `Dockerfile`, `website/`, `backend/`).

| # | What to do | Command or action |
|---|------------|--------------------|
| **0** | Have a Google Cloud project and **Project ID**. Install **gcloud CLI** and **Docker**. | [console.cloud.google.com](https://console.cloud.google.com) → New project. Install from [cloud.google.com/sdk](https://cloud.google.com/sdk/docs/install). |
| **1** | Log in and set project. | `gcloud auth login` then `gcloud config set project YOUR_PROJECT_ID` |
| **2** | Enable required APIs. | `gcloud services enable run.googleapis.com artifactregistry.googleapis.com firebasehosting.googleapis.com` |
| **3** | Set region and create Docker repo. | `$GCP_REGION = "us-central1"` then `gcloud artifacts repositories create nauticai-repo --repository-format=docker --location=$GCP_REGION` (skip if it already exists) |
| **4** | Let Docker use Google’s registry. | `gcloud auth configure-docker $GCP_REGION-docker.pkg.dev --quiet` |
| **5** | Build and push the backend image. | `$PROJECT_ID = (gcloud config get-value project)` then `$IMAGE = "$GCP_REGION-docker.pkg.dev/$PROJECT_ID/nauticai-repo/nauticai-backend:latest"` then `docker build --platform linux/amd64 -t $IMAGE -f Dockerfile .` then `docker push $IMAGE` |
| **6** | Deploy backend to Cloud Run. | `gcloud run deploy nauticai-api --image $IMAGE --region $GCP_REGION --platform managed --allow-unauthenticated --memory 4Gi --cpu 2` |
| **7** | Copy the **Service URL** from the deploy output (e.g. `https://nauticai-api-xxxxx-uc.a.run.app`). This is your **backend URL**. | Shown at end of step 6. |
| **8** | Edit `website/index.html` and `website/demo.html`: in the `<body>` tag set `data-api-url="YOUR_BACKEND_URL"` (the URL from step 7, no trailing slash). | e.g. `data-api-url="https://nauticai-api-xxxxx-uc.a.run.app"` |
| **9** | Install Firebase CLI and log in. | `npm install -g firebase-tools` then `firebase login` |
| **10** | Initialize Firebase Hosting (first time only). | `firebase init hosting` → Use existing project → **Public directory:** `website` → Single-page app: **No** → Overwrite index.html: **No** |
| **11** | Deploy the marketing website. | `firebase deploy --only hosting` |
| **12** | Open your live site. | `https://YOUR_PROJECT_ID.web.app` (Firebase shows this after deploy) |
| **13** | **Set Cloud Run env vars (required).** Go to [Cloud Run](https://console.cloud.google.com/run) → **nauticai-api** → **Edit & deploy new revision** → **Variables and secrets** → **Add variable**. Add: `NAUTICAI_BASE_URL` = your backend URL (step 7, no trailing slash). For WhatsApp alerts also add: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` (get values from [Twilio Console](https://console.twilio.com)). Then click **Deploy**. | See [WHATSAPP_SETUP.md](WHATSAPP_SETUP.md) for Twilio setup. |

**Or via CLI (step 13):** Replace `YOUR_BACKEND_URL` with the URL from step 7. For WhatsApp, replace the Twilio placeholders with your real values.

```powershell
gcloud run services update nauticai-api --region $GCP_REGION --set-env-vars "NAUTICAI_BASE_URL=YOUR_BACKEND_URL,TWILIO_ACCOUNT_SID=ACxxxx,TWILIO_AUTH_TOKEN=your_token,TWILIO_WHATSAPP_FROM=whatsapp:+14155238886"
```

**Optional:** To deploy the React inspection app, see “Step 4 (Optional): React app” in the sections below.

---

## Install Google Cloud SDK and tools (one-time)

From project root in PowerShell, run:

```powershell
.\setup-gcp-tools.ps1
```

This installs (via winget): **Google Cloud SDK** (gcloud), **Docker Desktop**, **Node.js**, and **Firebase CLI**. You may see UAC prompts; accept them. When done, **close and reopen PowerShell** so the new tools are on your PATH.

**Manual install links** (if the script fails or you prefer):

| Tool | Install |
|------|--------|
| **Google Cloud SDK** | [Install gcloud](https://cloud.google.com/sdk/docs/install) or `winget install -e --id Google.CloudSDK` |
| **Docker Desktop** | [Docker for Windows](https://docs.docker.com/desktop/install/windows-install/) or Microsoft Store “Docker Desktop” |
| **Node.js** | [nodejs.org](https://nodejs.org) LTS or `winget install -e --id OpenJS.NodeJS.LTS` |
| **Firebase CLI** | After Node: `npm install -g firebase-tools` |

---

## Prerequisites

1. **Google Cloud project**  
   Create one at [console.cloud.google.com](https://console.cloud.google.com) and note the **Project ID**.

2. **gcloud CLI**  
   Install (see “Install Google Cloud SDK and tools” above), then:
   ```powershell
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **Docker**  
   Installed and running (to build images).

4. **Node.js** (optional)  
   Only if you deploy the React frontend or use Firebase Hosting.

---

## Step 1: Enable APIs

```powershell
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
```

If you use Firebase Hosting:

```powershell
gcloud services enable firebasehosting.googleapis.com
```

---

## Step 2: Backend — Cloud Run

Your existing `Dockerfile` uses port 8080, which is what Cloud Run expects.

### 2.1 Create Artifact Registry repository

```powershell
$GCP_REGION = "us-central1"
gcloud artifacts repositories create nauticai-repo --repository-format=docker --location=$GCP_REGION
```

If the repo already exists, skip or use:

```powershell
gcloud artifacts repositories describe nauticai-repo --location=$GCP_REGION
```

### 2.2 Configure Docker for Artifact Registry

```powershell
$PROJECT_ID = (gcloud config get-value project)
gcloud auth configure-docker $GCP_REGION-docker.pkg.dev --quiet
```

### 2.3 Build and push the backend image

From **project root** (where the Dockerfile is):

```powershell
$IMAGE = "$GCP_REGION-docker.pkg.dev/$PROJECT_ID/nauticai-repo/nauticai-backend:latest"
docker build --platform linux/amd64 -t $IMAGE -f Dockerfile .
docker push $IMAGE
```

### 2.4 Deploy to Cloud Run

```powershell
$BACKEND_SERVICE = "nauticai-api"
gcloud run deploy $BACKEND_SERVICE `
  --image $IMAGE `
  --region $GCP_REGION `
  --platform managed `
  --allow-unauthenticated `
  --memory 4Gi `
  --cpu 2
```

When prompted for **region**, use the same as `$GCP_REGION`. After deployment, note the **Service URL** (e.g. `https://nauticai-api-xxxxx-uc.a.run.app`). This is your **backend URL**.

### 2.5 Set environment variables (required)

Set these env vars on the Cloud Run service so report links and (optionally) WhatsApp work:

```powershell
gcloud run services update $BACKEND_SERVICE --region $GCP_REGION `
  --set-env-vars "NAUTICAI_BASE_URL=https://nauticai-api-xxxxx-uc.a.run.app"
```

Replace the URL with your actual Cloud Run URL. For Twilio (optional):

```powershell
gcloud run services update $BACKEND_SERVICE --region $GCP_REGION `
  --set-env-vars "TWILIO_ACCOUNT_SID=ACxxxx,TWILIO_AUTH_TOKEN=your_token,TWILIO_WHATSAPP_FROM=whatsapp:+14155238886"
```

Or use **Google Cloud Console → Cloud Run → your service → Edit & deploy new revision → Variables & secrets** to add them.

---

## Step 3: Marketing website — Firebase Hosting

### 3.1 Install Firebase CLI and login

```powershell
npm install -g firebase-tools
firebase login
```

### 3.2 Initialize Firebase in the project (first time only)

From project root:

```powershell
firebase init hosting
```

- Choose “Use an existing project” and select your GCP project.
- **Public directory:** `website` (the folder with index.html, demo.html).
- **Single-page app:** No (we have index.html and demo.html).
- **Overwrite index.html:** No.

### 3.3 Set production URLs in the website

Before deploying, set the backend and app URLs so the demo and API status work.

Edit **`website/index.html`** and **`website/demo.html`**. Find the `<body>` tag and set:

- `data-api-url` = your Cloud Run backend URL (no trailing slash), e.g. `https://nauticai-api-xxxxx-uc.a.run.app`
- `data-app-url` = URL of your React app if you deploy it (e.g. `https://your-app.web.app`), or leave `/app/` if you only use the marketing site and link elsewhere.

Example:

```html
<body data-app-url="https://your-react-app.web.app" data-api-url="https://nauticai-api-xxxxx-uc.a.run.app">
```

### 3.4 Deploy the website

```powershell
firebase deploy --only hosting
```

Your site will be at `https://YOUR_PROJECT_ID.web.app` (or the custom domain you add in Firebase).

---

## Step 4 (Optional): React app on Firebase Hosting

If you want the full inspection demo (React app):

1. **Build the frontend** with your backend URL and demo gate URL:

   ```powershell
   cd frontend
   $env:REACT_APP_API_URL = "https://nauticai-api-xxxxx-uc.a.run.app"
   $env:REACT_APP_DEMO_GATE_URL = "https://YOUR_PROJECT_ID.web.app/demo.html"
   npm install
   npm run build
   cd ..
   ```

2. **Host the React build** on Firebase:
   - Either add a second Firebase site (e.g. “app”) and set **Public directory** to `frontend/build` when you run `firebase init hosting` again in a different folder or with a different target.
   - Or use the same Firebase project and deploy the marketing site from `website/` and the app from `frontend/build/` as two separate targets (e.g. `firebase target:apply hosting main website` and `firebase target:apply hosting app frontend/build`), then `firebase deploy --only hosting`.

   **Simple approach:** Use one hosting site for the marketing site. For the app, either:
   - Deploy `frontend/build` to a **second Firebase Hosting site** (e.g. “nauticai-app”), or
   - Upload `frontend/build` to a **Cloud Storage bucket** and use **Firebase Hosting** or **Load Balancer** to serve it.

3. Set **`data-app-url`** on the marketing site to the URL where the React app is served (e.g. `https://nauticai-app.web.app`).

---

## Step 5: Custom domain (optional)

- **Cloud Run:** Console → Cloud Run → your service → **Manage custom domains** → add your domain and follow DNS instructions.
- **Firebase Hosting:** Console → Hosting → **Add custom domain** and point your DNS as shown.

---

## Summary checklist

| Step | What | Result |
|------|------|--------|
| 1 | Enable Cloud Run + Artifact Registry (and Firebase if used) | APIs on |
| 2 | Build Docker image, push to Artifact Registry, deploy to Cloud Run | Backend URL (e.g. `https://nauticai-api-xxx.run.app`) |
| 3 | **Set Cloud Run env vars:** `NAUTICAI_BASE_URL` and (for WhatsApp) `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` | Report links and WhatsApp ready |
| 4 | Set `data-api-url` and `data-app-url` in `website/*.html`, then `firebase deploy --only hosting` | Marketing site URL |
| 5 | (Optional) Build React with `REACT_APP_API_URL` and `REACT_APP_DEMO_GATE_URL`, deploy to Firebase or GCS | App URL |

---

## Updating the backend

After code changes:

```powershell
$IMAGE = "$GCP_REGION-docker.pkg.dev/$PROJECT_ID/nauticai-repo/nauticai-backend:latest"
docker build --platform linux/amd64 -t $IMAGE -f Dockerfile .
docker push $IMAGE
gcloud run deploy nauticai-api --image $IMAGE --region $GCP_REGION
```

---

## Cost notes

- **Cloud Run:** Free tier includes 2 million requests/month; you pay for CPU/memory per request. Use 4 GB / 2 CPU only if the model needs it; you can start with 2 GB / 1 CPU.
- **Firebase Hosting:** Generous free tier for static files.
- **Artifact Registry:** Small storage cost for the Docker image.

For more, see [Cloud Run pricing](https://cloud.google.com/run/pricing) and [Firebase Hosting pricing](https://firebase.google.com/pricing).
