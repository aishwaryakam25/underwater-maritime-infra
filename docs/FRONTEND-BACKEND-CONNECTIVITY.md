# Frontend and backend connectivity

How the **marketing website**, **React app**, and **backend API** connect, and how to check they are working.

---

## How they connect

| Part | Connects to backend via | Where to set |
|------|-------------------------|--------------|
| **Marketing site** (website/) | `data-api-url` on `<body>` in `index.html` and `demo.html` | Edit the HTML, or set when deploying (deploy-gcp.ps1 does this). |
| **React app** (frontend/) | `REACT_APP_API_URL` at **build time** | `.env` or `REACT_APP_API_URL=... npm run build` / set in CI. |
| **Local dev – React** | `proxy` in `frontend/package.json` → `http://localhost:8000` | No change needed if backend runs on port 8000. |
| **Local dev – website** | If you open site on port 8080, it infers API at `http://localhost:8000` | Or set `data-api-url="http://localhost:8000"` in demo.html/index.html. |

So:

- **Backend** = one place (local: port 8000, or Cloud Run URL after deploy).
- **Marketing site** talks to backend using `data-api-url`.
- **React app** talks to backend using `REACT_APP_API_URL` (or proxy in dev).

They are “connected” when that URL points to the same backend and the backend is running.

---

## Check 1: Backend is up

**Local:** Backend runs on port 8000 (e.g. `.\run-website.ps1` or `uvicorn backend.main:app --port 8000`).

**GCP:** Backend is your Cloud Run URL (e.g. `https://nauticai-api-xxxxx-uc.a.run.app`).

Open in browser:

- Local: `http://localhost:8000/api/health`
- GCP: `https://YOUR_CLOUD_RUN_URL/api/health`

You should see JSON like `{"status":"ok","model":"..."}`. If that works, the backend is working.

---

## Check 2: Marketing website is connected

1. Open the marketing site (local: `http://localhost:8080` or your Firebase URL).
2. **Demo page:** Sign up and “Send test alert” use the backend. If `data-api-url` is set and backend is up, signup and test alert work.
3. **Footer:** On `index.html`, the script calls `data-api-url + "/api/health"`. If configured, it shows “API Live” or similar when the backend responds.

So: if `data-api-url` is set (in HTML or by deploy script) and the backend URL is correct, the **marketing site and backend are connected**. You can confirm by checking the footer status or using the demo page.

---

## Check 3: React app is connected

**Local dev:**

1. Start backend: `.\run-website.ps1` (or uvicorn on 8000).
2. Start React: `cd frontend && npm start` (runs on 3000).
3. React uses `proxy` → all `/api/*` requests go to `http://localhost:8000`. So no `REACT_APP_API_URL` needed in dev.
4. In the React app UI you should see **“API Online”** (and optionally model name) when the health check succeeds.

**Production / deployed:**

1. React is built with `REACT_APP_API_URL=https://YOUR_CLOUD_RUN_URL` (no trailing slash).
2. Deployed app calls that URL for `/api/health`, `/api/detect`, etc.
3. If the backend is up and the URL is correct, you see **“API Online”** in the app.

So: **React and backend are connected** when:

- Local: backend on 8000 + React dev server (proxy).
- Production: `REACT_APP_API_URL` points to the same backend URL you used in Check 1.

---

## Quick verification (local)

1. **Backend:** `curl http://localhost:8000/api/health` (or open in browser) → JSON with `"status":"ok"`.
2. **Website:** Open `http://localhost:8080/demo.html`; if backend hint does not show, backend is reachable; sign up and test alert should work if `data-api-url` is set.
3. **React:** Open `http://localhost:3000`; top bar or footer should show **“API Online”** if backend is reachable (via proxy).

---

## After GCP deploy

- **Backend:** Cloud Run URL (from deploy output). Test: `https://YOUR_CLOUD_RUN_URL/api/health`.
- **Marketing site:** `deploy-gcp.ps1` sets `data-api-url` in `website/index.html` and `website/demo.html` to that Cloud Run URL. So marketing site and backend are connected after deploy.
- **React:** To connect the React app to the same backend, build with:
  ```powershell
  cd frontend
  $env:REACT_APP_API_URL = "https://YOUR_CLOUD_RUN_URL"
  npm run build
  ```
  Then deploy the `frontend/build` folder (e.g. Firebase Hosting). The deployed React app will show “API Online” when the backend is up.

---

## Summary

| Question | Answer |
|----------|--------|
| Are frontend and backend connected? | Yes, when the **backend URL** is set correctly for each frontend (marketing site via `data-api-url`, React via `REACT_APP_API_URL` or dev proxy) and the backend is running. |
| How do I know the backend works? | Call `/api/health` (browser or curl). |
| How do I know the marketing site is connected? | Footer shows API status; demo signup and test alert work. |
| How do I know the React app is connected? | React UI shows **“API Online”** when the health check succeeds. |
