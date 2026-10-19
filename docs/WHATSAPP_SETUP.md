# Enable WhatsApp alerts and PDF reports

WhatsApp and completion alerts use **Twilio**. Without Twilio configured, the backend still runs (signup, detection, PDF download work), but "Send test alert", "Completion alert", and "Send PDF to WhatsApp" return a "not configured" message.

---

## 1. Install Twilio (backend)

From project root:

```powershell
pip install twilio
```

Or the backend already lists it in `backend/requirements.txt` — install with:

```powershell
pip install -r backend/requirements.txt
```

---

## 2. Get Twilio credentials

1. Sign up at [twilio.com](https://www.twilio.com).
2. In the **Console**, note:
   - **Account SID**
   - **Auth Token**
3. For **WhatsApp**:
   - **Option A (quick):** [Twilio WhatsApp Sandbox](https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn) — join the sandbox with your phone (e.g. send "join &lt;code&gt;" to the sandbox number). You can only send to numbers that have joined.
   - **Option B (production):** Request a [WhatsApp Business API](https://www.twilio.com/whatsapp) number.

4. Note the **WhatsApp "From" number** (sandbox looks like `whatsapp:+14155238886`).

---

## 3. Set environment variables

Where your **backend** runs (local terminal, App Runner, EC2, etc.), set:

| Variable | Example | Required |
|----------|---------|----------|
| `TWILIO_ACCOUNT_SID` | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` | Yes |
| `TWILIO_AUTH_TOKEN` | your auth token | Yes |
| `TWILIO_WHATSAPP_FROM` | `whatsapp:+14155238886` (sandbox) or your WhatsApp Business number | Yes |

**Quick enable (recommended):** The backend loads `backend/.env` automatically. From project root:

```powershell
copy backend\.env.example backend\.env
# Edit backend\.env and set your real TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
.\run-website.ps1
```

Sign up and the demo work without WhatsApp. Once the three Twilio vars are set in `backend/.env` and the backend is restarted, "Send test alert" and completion alerts will work.

**Alternative — set in PowerShell for this session only:**

```powershell
$env:TWILIO_ACCOUNT_SID = "ACxxxxxxxx..."
$env:TWILIO_AUTH_TOKEN = "your_auth_token"
$env:TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"
# Then start the backend (or run-website.ps1 in another terminal)
uvicorn backend.main:app --port 8000
```

**AWS App Runner:** In the service → Configuration → Environment variables, add the three variables.

---

## 4. Optional: report download links in WhatsApp

When you send a PDF to WhatsApp, the message can include a one-time download link. That link must point at your **public backend URL**. Set:

| Variable | Example |
|----------|---------|
| `NAUTICAI_BASE_URL` | `https://your-api.us-east-1.awsapprunner.com` (no trailing slash) |

If this is not set, the backend still sends the WhatsApp message but may omit the link or use a placeholder.

---

## 5. Restart the backend

After setting the variables, restart the backend process so it picks them up. Then:

- **Demo page:** "Send test alert to my WhatsApp" should send a test message.
- **React app:** "🔔 Completion alert" and "📱 Send to WhatsApp" (on PDFs) should work for numbers that have joined the sandbox (or your production WhatsApp number).

---

## 6. Troubleshooting

- **"WhatsApp not configured"** — Backend did not see `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`. Check they are set in the same environment where uvicorn runs.
- **"Install twilio: pip install twilio"** — Run `pip install twilio` in the backend environment.
- **Twilio error 21211 / 21614** — Recipient number must be in E.164 (e.g. `+6591234567`). For sandbox, the recipient must have joined the sandbox first.
- **Sandbox:** Only numbers that have sent the "join &lt;code&gt;" message to your sandbox number can receive messages.
