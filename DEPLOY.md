# NautiCAI — Deploy & Run the Website

This guide walks you through running the NautiCAI web app **locally** and **deploying** it to the cloud.

---

## Option A: Run the website locally (fastest)

Use this to open the full app in your browser in a few minutes.

### 1. One-command run (PowerShell, from project root)

```powershell
.\run-demo-local.ps1
```

- A **second window** opens with the backend (port 8000).
- This window starts the frontend (port 3000).
- Open **http://localhost:3000** in your browser.

### 2. Manual run (if the script fails)

**Terminal 1 — Backend**

```powershell
cd "c:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly"
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend**

```powershell
cd "c:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\frontend"
npm install
npm start
```

Then open **http://localhost:3000**. The frontend uses `proxy` in `package.json` to talk to the backend.

### 3. Optional: model file

- If you have **`best.pt`** in the project root, the app uses it.
- Otherwise the backend downloads the model from Hugging Face on first detection (slower first run).

---

## Option B: Run with Docker (local)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed.

```powershell
# From project root
docker compose up --build
```

- Frontend: **http://localhost:3000**
- Backend API: **http://localhost:8000**
- API docs: **http://localhost:8000/docs**

To use a local model, place `best.pt` in the project root before running. The `docker-compose.yml` mounts it into the backend.

---

## Option C: Deploy to AWS (recommended if you use AWS)

Use **ECR + App Runner** for the backend and **S3 + CloudFront** or **Amplify** for the frontend.

- **Full guide:** [DEPLOY-AWS.md](DEPLOY-AWS.md)
- **Quick script** (Git Bash or WSL, from project root):
  ```bash
  chmod +x deploy-aws.sh
  ./deploy-aws.sh
  ```
  The script builds and pushes the backend to ECR, updates App Runner if the service already exists, and builds the frontend. You then upload the frontend to S3 or deploy via Amplify (steps in DEPLOY-AWS.md).

---

## Option D: Deploy to the cloud (Google Cloud Run)

You get a public website (e.g. `https://nauticai-web-xxxxx.run.app`) and a separate API URL.

### Prerequisites

1. [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) installed.
2. Log in and set a project:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

### Deploy

From project root (Git Bash or WSL on Windows):

```bash
chmod +x deploy-gcp.sh
./deploy-gcp.sh
```

The script will:

1. Enable Cloud Run and Container Registry APIs.
2. Build and deploy the **backend** (4 GB RAM, 2 CPU, port 8000).
3. Build the **frontend** with the backend URL baked in.
4. Deploy the **frontend** (512 MB, port 80).

At the end it prints:

- **Frontend URL** — your public website (e.g. `https://nauticai-web-xxxxx.run.app`).
- **Backend URL** — API (e.g. `https://nauticai-api-xxxxx.run.app`).
- **API docs** — `https://nauticai-api-xxxxx.run.app/docs`.

### Cost note

Cloud Run charges for CPU/memory and requests. You can set budget alerts in GCP Console. The free tier usually covers light demo use.

---

## Option E: Other hosts (Vercel + Railway / Render)

- **Frontend:** Deploy the `frontend/` folder to [Vercel](https://vercel.com) (Connect repo → root directory: `frontend`). Set env var **`REACT_APP_API_URL`** to your backend URL.
- **Backend:** Deploy the backend (e.g. Dockerfile.backend) to [Railway](https://railway.app) or [Render](https://render.com) (Web Service, Docker). Use the generated URL as `REACT_APP_API_URL` when building the frontend.

---

## Summary

| Goal                | What to do                    | URL / command                    |
|---------------------|-------------------------------|----------------------------------|
| Local app           | Run `.\run-demo-local.ps1`    | http://localhost:3000            |
| Local with Docker   | `docker compose up --build`   | http://localhost:3000            |
| Marketing site      | Run `.\run-website.ps1` or double-click `START-WEBSITE.cmd` | http://localhost:8080 |
| Deploy (AWS)        | See [DEPLOY-AWS.md](DEPLOY-AWS.md), run `./deploy-aws.sh` + `./deploy-website-aws.sh` | URLs in guide |
| Deploy (GCP)        | Run `./deploy-gcp.sh`         | Printed at end of script         |

For questions or issues, see the main [README.md](README.md) or open an issue on the repo.
