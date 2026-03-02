# NautiCAI — Deployment checklist

Use this before going live so every link, button, and icon works. Applies to **AWS** ([DEPLOY-AWS.md](DEPLOY-AWS.md)) or **Google Cloud** ([DEPLOY-GCP.md](DEPLOY-GCP.md)).

---

## 1. Marketing website (`website/`)

**Deploy:** AWS → S3 + CloudFront. GCP → Firebase Hosting.

- [ ] **Links:** Nav logo and footer logo point to `index.html`. All `.demo-link` → `demo.html` (set by `script.js`). Anchor links `#how`, `#use-cases`, `#about`, `#contact` work (smooth scroll).
- [ ] **Contact form:** Uses `mailto:`; recipient is `data-mailto` on the form (default `contact@nauticai-ai.com`). Change in `index.html` if needed.
- [ ] **Production URLs:** After deploy, set on `<body>` in **both** `index.html` and `demo.html`:
  - `data-app-url="https://your-react-app-url"` — where the inspection app lives (e.g. CloudFront or Amplify URL for the React build). No trailing slash.
  - `data-api-url="https://your-backend-url"` — backend API (e.g. App Runner URL). No trailing slash.  
  Example:  
  `<body data-app-url="https://app.yourdomain.com" data-api-url="https://api.yourdomain.com">`
- [ ] **Run:** `export NAUTICAI_WEBSITE_BUCKET=your-bucket && ./deploy-website-aws.sh` (or use AWS Console upload).

---

## 2. React app (inspection demo)

**Deploy:** S3 + CloudFront, or Amplify Hosting.

- [ ] **Build with env:** Set before `npm run build`:
  - `REACT_APP_API_URL` = backend URL (e.g. `https://xxxxx.awsapprunner.com`). Required for detection, PDF, WhatsApp.
  - `REACT_APP_DEMO_GATE_URL` = marketing demo page (e.g. `https://www.yourdomain.com/demo.html`). Used for “Book a demo” and redirect when no access.
- [ ] **Book a demo:** Button opens `REACT_APP_DEMO_GATE_URL` or `/demo.html` in a new tab. Works if env is set at build time.
- [ ] **Demo gate redirect:** If user has no access, app redirects to `REACT_APP_DEMO_GATE_URL` or `/demo.html`. Set so it points to your deployed marketing site.

See `frontend/.env.example`.

---

## 3. Backend API

**Deploy:** AWS → App Runner (or EC2/ECS). GCP → Cloud Run.

- [ ] **CORS:** Backend allows all origins. For production you can restrict to your CloudFront/Amplify origins.
- [ ] **Env (optional):**
  - `NAUTICAI_BASE_URL` = backend URL (for WhatsApp report download links). No trailing slash.
  - `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` for WhatsApp alerts. Without these, signup and PDF still work; WhatsApp returns “not configured”.

See `backend/.env.example`.

---

## 4. Quick verification

| Item | Where | Expected |
|------|--------|----------|
| Nav: How it works, Use cases, About, Contact | Marketing | Smooth scroll to section |
| Try demo | Marketing | Goes to demo.html |
| Sign up & open demo | Demo page | Redirects to React app with access |
| Back to website | Demo page | Goes to index.html |
| Contact Send | Marketing | Opens mailto with pre-filled body |
| Book a demo (topbar) | React app | Opens demo gate in new tab |
| API status (footer) | Marketing | “API Live” when data-api-url is set and backend is up |

---

## 5. Cloud recap

**AWS:** From project root (Git Bash/WSL): `./deploy-aws.sh` then `./deploy-website-aws.sh` (set `NAUTICAI_WEBSITE_BUCKET`). Full steps: [DEPLOY-AWS.md](DEPLOY-AWS.md).

**Google Cloud:** Backend → build image, push to Artifact Registry, deploy to Cloud Run. Website → set `data-api-url` / `data-app-url` in `website/*.html`, then `firebase deploy --only hosting`. Full steps: [DEPLOY-GCP.md](DEPLOY-GCP.md).

Set `data-app-url` and `data-api-url` in `website/index.html` and `website/demo.html` (or inject at deploy time) for your chosen backend and app URLs.
