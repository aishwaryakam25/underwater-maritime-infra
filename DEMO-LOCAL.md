# Run demo locally (no Cloud Run — works in any browser / incognito)

Use this when Cloud Run is blocked by org policy (403). No auth, works in ~2 minutes.

## Quick run (PowerShell, from repo root)

```powershell
.\run-demo-local.ps1
```

- A **second window** will open with the backend (port 8000).
- This window will start the frontend (port 3000).
- Open **http://localhost:3000** in any browser (or incognito).

---

## Manual steps (if the script fails)

**Terminal 1 — Backend**

```powershell
cd c:\Users\Asus\Documents\nauticai-underwater-anomaly
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend**

```powershell
cd c:\Users\Asus\Documents\nauticai-underwater-anomaly\frontend
npm start
```

Then open **http://localhost:3000** in your browser (or incognito). The frontend proxies API calls to the backend automatically.

---

## Optional: model file

If you have `best.pt` in the repo root, detection will use it. Otherwise the app may download from HuggingFace on first run.
