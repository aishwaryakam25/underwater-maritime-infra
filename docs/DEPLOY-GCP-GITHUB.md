# Deploy to Google Cloud Run from GitHub (video-style, continuous deploy)

This follows the same flow as the tutorial: **push code to GitHub → connect repo to Cloud Run → automatic deploy on every push**. No need to run Docker or deploy scripts on your laptop.

---

## 1. Push your code to GitHub

- Create a repo (e.g. `nauticai-underwater-anomaly` or `first-api-backend`).
- Push your project:
  ```powershell
  cd "C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly"
  git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
  git push -u origin main
  ```
- Ensure the repo has: `Dockerfile`, `backend/`, `app/` at the **root** (so Cloud Build can find the Dockerfile).

---

## 2. Create a Google Cloud project

1. Go to [Google Cloud Console](https://console.cloud.google.com).
2. **Create project** (e.g. name: `fastapi-backend` or `nauticai-api`). Note the **Project ID**.

---

## 3. Connect GitHub to Google Cloud

1. In the console, open **Cloud Build** or go to **Cloud Run**.
2. **Cloud Run** → **Create Service**.
3. Under **Source**, choose **Continuously deploy from a repository** (or **Connect repository**).
4. **Set up with Cloud Build** → **Connect new repository**.
5. Pick **GitHub** → Authorize → select your **repository** and **branch** (e.g. `main`).
6. **Save** the connection.

---

## 4. Build and deploy settings (Cloud Run)

When asked how to build:

- **Build type:** **Docker** (we use a Dockerfile; the video used “Build” without Docker for a simple app—our app needs Docker because of native dependencies).
- **Dockerfile location:** **Dockerfile** (at repo root).
- **Build context:** Repository root (default).
- **Service name:** e.g. `nauticai-api`.
- **Region:** Pick one (e.g. same as in the video, or a Tier 2 region for lower cost).
- **Authentication:** **Allow unauthenticated invocations** so the API is public (like the video).

**Port:** Cloud Run expects the container to listen on **8080**. Our Dockerfile already uses port 8080, so no change needed.

---

## 5. IAM fix (if deploy fails)

If you see:

**“Cloud Build trigger creation failed”** or **“Required roles: roles/run.admin, roles/iam.serviceAccountUser”**:

1. Go to **IAM & Admin** → **IAM** in the Google Cloud Console.
2. Find the **default compute service account** (e.g. `PROJECT_NUMBER-compute@developer.gserviceaccount.com`).
3. **Edit** (pencil) → **Add another role**:
   - **Cloud Run Admin**
   - **Service Account User** (or **iam.serviceAccountUser**)
4. **Save**.
5. In **Cloud Run**, trigger a new deployment (e.g. **Edit & deploy new revision** and Redeploy, or push a small change to GitHub so Cloud Build runs again).

---

## 6. Redeploy after IAM fix

- **Option A:** Push a new commit to the connected branch so Cloud Build runs again.
- **Option B:** In **Cloud Run** → your service → **Edit & deploy new revision** (if you had already created the service and only IAM was wrong).

---

## 7. Check that the backend is running

After deployment finishes:

1. In **Cloud Run**, open your service and copy the **URL** (e.g. `https://nauticai-api-xxxxx-uc.a.run.app`).
2. Open in the browser:
   - **Homepage:** `https://YOUR_URL/`
   - **Health:** `https://YOUR_URL/api/health`
3. You should see JSON like `{"status":"ok","model":"...","version":"1.0.4"}`.

Same idea as the video: **home** and **health** endpoints working.

---

## 8. Optional: set environment variables

For NautiCAI (report links, WhatsApp):

1. **Cloud Run** → your service → **Edit & deploy new revision**.
2. **Variables and secrets** → add:
   - `NAUTICAI_BASE_URL` = your Cloud Run URL (no trailing slash)
   - Optional: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`
3. **Deploy**.

---

## Summary (same flow as the video)

| Step | Video | This repo |
|------|--------|-----------|
| 1 | Push code to GitHub | Push repo with `Dockerfile`, `backend/`, `app/` |
| 2 | New GCP project | Same |
| 3 | Cloud Run → Connect repository | Same (GitHub) |
| 4 | Build: no Docker, entry point `uvicorn main:app --host 0.0.0.0 --port 8080` | Build: **Docker** (Dockerfile), port 8080 already in Dockerfile |
| 5 | Allow public access | Same |
| 6 | IAM: add `run.admin` + `iam.serviceAccountUser` to default compute SA | Same |
| 7 | Redeploy / push to trigger build | Same |
| 8 | Test `/health` and docs | Test `/api/health` and your API |

The only difference is we use **Docker** because this backend has native dependencies (OpenCV, etc.). The flow—GitHub → Cloud Run, continuous deploy, IAM fix—is the same as in the video.
