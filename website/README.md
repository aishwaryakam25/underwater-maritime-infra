# NautiCAI — Marketing Website

Landing page: Hero, How it works, About, Contact. **"Try demo"** opens a **signup gate** first; only after signup does the app open.

## Demo flow

1. Visitor clicks **Try demo** → goes to **`demo.html`** (signup gate).
2. They enter name, email, and optional **WhatsApp number** (for reports and alerts).
3. On submit they are stored (backend `POST /api/signup`) and redirected to the **React app**.
4. The React app checks for demo access; if missing, it redirects back to the gate. No signup = no app access.

## Where does the app open after signup?

Set **`data-app-url`** on `<body>` in **`demo.html`** (and optionally `index.html`):

- **Same domain:** `data-app-url="/app/"`
- **Local dev:** When serving the site on port 8080, the script uses `http://localhost:3000` for the React app.

## WhatsApp alerts and PDF to WhatsApp

- **Backend** can send text messages and report links to WhatsApp via **Twilio**. Set env vars: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` (e.g. `whatsapp:+14155238886` for sandbox). Optional: `NAUTICAI_BASE_URL` so report download links in WhatsApp point to your server.
- **Demo app:** After generating a PDF, users can click **"Send to WhatsApp"** to receive the report link on the number they gave at signup (or they see a message to add it at signup).
- Without Twilio configured, the backend still accepts signups and PDF-send requests; it returns `sent: false` with a message.

## Run locally

**PowerShell (from project root):**
```powershell
.\run-website.ps1
```

**Or manually:**
```powershell
cd website
python -m http.server 8080
```
Then open http://localhost:8080

## Contact form

Uses **mailto:** — clicking Send opens the visitor's email client with a pre-filled message. Change the recipient in `index.html`:

```html
<form ... data-mailto="your@email.com">
```

## Deploy

**AWS S3:**
```bash
export NAUTICAI_WEBSITE_BUCKET=your-bucket-name
./deploy-website-aws.sh
```

**Other hosts:** Upload the `website/` folder to Netlify, Vercel, GitHub Pages, or any static host. No build step.
