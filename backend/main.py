"""
NautiCAI — FastAPI Backend
Serves the detection engine, visibility enhancement, PDF report, and heatmap APIs.
Run: uvicorn backend.main:app --reload --port 8000
"""
import io, os, sys, uuid, datetime, base64, tempfile, csv
from pathlib import Path

# Load .env from backend folder so TWILIO_* and NAUTICAI_BASE_URL work without setting in shell
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass

from fastapi import FastAPI, File, UploadFile, Form, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from PIL import Image

# Add parent dir so imports work when running from project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from severity import compute_risk, score_to_grade
from visibility import full_enhance, pil_to_cv, cv_to_pil, apply_clahe, apply_green_water, apply_turbidity, apply_edge_estimator
from detection import run_detection, annotate_image, build_heatmap, get_model_name, load_yolo

# Also make app/pdf_report.py importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from pdf_report import build_pdf

app = FastAPI(
    title="NautiCAI API",
    description="Underwater Infrastructure Inspection Copilot — API",
    version="1.0.4",
)

# Allow React dev server and deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── In-memory stores for demo (signups, one-time PDF links) ─────────────
_signups_file = Path(__file__).resolve().parent / "signups.json"
_report_downloads = {}  # report_id -> (pdf_bytes, created_at, download_password or None)


def _encrypt_pdf(pdf_bytes: bytes, user_password: str) -> bytes:
    """Encrypt PDF with user password so only recipients with the password can open it."""
    try:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(io.BytesIO(pdf_bytes))
        writer = PdfWriter(clone_from=reader)
        writer.encrypt(user_password=user_password, algorithm="AES-256")
        out = io.BytesIO()
        writer.write(out)
        return out.getvalue()
    except Exception:
        return pdf_bytes

def _store_signup(data: dict):
    try:
        import json
        existing = []
        if _signups_file.exists():
            existing = json.loads(_signups_file.read_text())
        existing.append({**data, "ts": datetime.datetime.now().isoformat()})
        _signups_file.write_text(json.dumps(existing, indent=2))
    except Exception:
        pass

def _send_whatsapp(to: str, body: str, media_url: str = None) -> dict:
    """Send WhatsApp message via Twilio if configured. Returns {sent: bool, message: str}."""
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")  # Twilio sandbox
    if not sid or not token:
        return {"sent": False, "message": "WhatsApp not configured. Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM."}
    try:
        try:
            from twilio.rest import Client
        except ImportError:
            return {"sent": False, "message": "Install twilio: pip install twilio"}
        client = Client(sid, token)
        to_wa = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
        msg_params = {"body": body, "from_": from_num}
        if media_url:
            msg_params["media_url"] = [media_url]
        client.messages.create(to=to_wa, **msg_params)
        return {"sent": True, "message": "Message sent."}
    except Exception as e:
        return {"sent": False, "message": str(e)}


# ── Startup: pre-load model ─────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    load_yolo()


# ── Helpers ──────────────────────────────────────────────────────────────
def _pil_to_b64(img: Image.Image, fmt="PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()


def _read_upload(file: UploadFile) -> Image.Image:
    return Image.open(io.BytesIO(file.file.read())).convert("RGB")


def _b64_to_pil(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


# ── Routes ───────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    model_name = get_model_name()
    return {"status": "ok", "model": model_name, "version": "1.0.4"}


@app.post("/api/detect")
async def detect(
    file: UploadFile = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    sev_filter: str = Form("All Detections"),
    # Visibility settings
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    marine_snow: bool = Form(False),
):
    """
    Run the vision model on an uploaded image.
    Returns: detections, annotated image (base64), heatmap (base64), metrics.
    """
    pil_img = _read_upload(file)

    # Visibility enhancement
    enhanced = full_enhance(
        pil_img,
        use_clahe=use_clahe,
        use_green=use_green,
        turb_in=turbidity_in,
        corr_turb=corr_turb,
        use_edge=use_edge,
        clahe_clip=clahe_clip,
        marine_snow=marine_snow,
    )

    # Run detection
    dets = run_detection(enhanced, conf_thr, iou_thr, mode)

    # Severity filter
    SEV_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    if sev_filter == "Critical Only":
        dets = [d for d in dets if d["severity"] == "Critical"]
    elif sev_filter == "High+":
        dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 3]
    elif sev_filter == "Medium+":
        dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 2]

    # Annotate + heatmap
    annotated = annotate_image(enhanced, dets)
    heatmap = build_heatmap(enhanced, dets)

    risk = compute_risk(dets)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for d in dets:
        sev_counts[d.get("severity", "Medium")] += 1

    return {
        "mission_id": mission_id,
        "scan_time": scan_time,
        "model": get_model_name(),
        "detections": dets,
        "risk_score": risk,
        "grade": grade,
        "sev_counts": sev_counts,
        "total": len(dets),
        "annotated_b64": _pil_to_b64(annotated),
        "heatmap_b64": _pil_to_b64(heatmap),
        "enhanced_b64": _pil_to_b64(enhanced),
    }


@app.post("/api/enhance")
async def enhance(
    file: UploadFile = File(...),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    marine_snow: bool = Form(False),
):
    """Return visibility-enhanced image comparison."""
    pil_img = _read_upload(file)
    bgr = pil_to_cv(pil_img)

    clahe_img = cv_to_pil(apply_clahe(bgr))
    green_img = cv_to_pil(apply_green_water(bgr))
    turb_img = cv_to_pil(apply_turbidity(bgr, 0.45))
    edge_img = cv_to_pil(apply_edge_estimator(bgr))
    full_img = full_enhance(pil_img, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip, marine_snow)

    return {
        "clahe_b64": _pil_to_b64(clahe_img),
        "green_b64": _pil_to_b64(green_img),
        "turbidity_b64": _pil_to_b64(turb_img),
        "edge_b64": _pil_to_b64(edge_img),
        "full_b64": _pil_to_b64(full_img),
    }


@app.post("/api/report/pdf")
async def generate_pdf(
    file: UploadFile = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
    sev_filter: str = Form("All Detections"),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    marine_snow: bool = Form(False),
    pdf_password: str = Form(""),
):
    """Generate and download a PDF inspection report. Optional pdf_password encrypts the PDF for privacy."""
    pil_img = _read_upload(file)

    enhanced = full_enhance(pil_img, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip, marine_snow)
    dets = run_detection(enhanced, conf_thr, iou_thr, mode)

    SEV_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    if sev_filter == "Critical Only":
        dets = [d for d in dets if d["severity"] == "Critical"]
    elif sev_filter == "High+":
        dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 3]
    elif sev_filter == "Medium+":
        dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 2]

    annotated = annotate_image(enhanced, dets)
    heatmap = build_heatmap(enhanced, dets)
    risk = compute_risk(dets)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"

    pdf_bytes = build_pdf(
        mission_id, vessel_name, inspector, mode,
        dets, pil_img, annotated, heatmap,
        risk, grade, conf_thr, iou_thr,
    )
    if (pwd := (pdf_password or "").strip()):
        pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)

    filename = f"NautiCAI_Report_{mission_id}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/video/detect")
async def video_detect(
    file: UploadFile = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    sample_n: int = Form(10),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
):
    """Process a video file frame-by-frame."""
    import cv2

    # Save uploaded video to temp file
    suffix = Path(file.filename or "video.mp4").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        tf.write(await file.read())
        tmp_path = tf.name

    cap = cv2.VideoCapture(tmp_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_v = cap.get(cv2.CAP_PROP_FPS) or 25
    wv = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    hv = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    all_dets = []
    frame_results = []
    fn = 0
    det_id_offset = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if fn % sample_n == 0:
            pf = cv_to_pil(frame)
            ef = full_enhance(pf, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip)
            df_v = run_detection(ef, conf_thr, iou_thr, mode)
            for d in df_v:
                det_id_offset += 1
                d["id"] = det_id_offset
                d["frame"] = fn
            all_dets.extend(df_v)
            af = annotate_image(ef, df_v)
            # Only keep first 4 annotated frames as base64
            if len(frame_results) < 4:
                frame_results.append({
                    "frame_num": fn,
                    "detection_count": len(df_v),
                    "annotated_b64": _pil_to_b64(af),
                })
        fn += 1

    cap.release()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    risk = compute_risk(all_dets)
    grade = score_to_grade(risk)

    return {
        "video_info": {
            "total_frames": total,
            "fps": round(fps_v, 1),
            "resolution": f"{wv}x{hv}",
            "duration": round(total / fps_v, 1),
        },
        "total_detections": len(all_dets),
        "risk_score": risk,
        "grade": grade,
        "frames_processed": fn // sample_n + 1,
        "sample_frames": frame_results,
        "detections": all_dets[:100],  # Limit for response size
    }


@app.post("/api/report/pdf/video")
async def generate_pdf_video(
    file: UploadFile = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
    sample_n: int = Form(10),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    pdf_password: str = Form(""),
):
    """Generate and download a PDF report for video analysis (ROV footage). Optional pdf_password encrypts the PDF."""
    import cv2

    suffix = Path(file.filename or "video.mp4").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        tf.write(await file.read())
        tmp_path = tf.name

    cap = cv2.VideoCapture(tmp_path)
    all_dets = []
    first_enhanced = None
    first_annotated = None
    first_frame_dets = None
    fn = 0
    det_id_offset = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if fn % sample_n == 0:
            pf = cv_to_pil(frame)
            ef = full_enhance(pf, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip)
            df_v = run_detection(ef, conf_thr, iou_thr, mode)
            for d in df_v:
                det_id_offset += 1
                d["id"] = det_id_offset
                d["frame"] = fn
            all_dets.extend(df_v)
            af = annotate_image(ef, df_v)
            if first_enhanced is None:
                first_enhanced = ef
                first_annotated = af
                first_frame_dets = df_v
        fn += 1

    cap.release()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass

    if first_enhanced is None:
        first_enhanced = Image.new("RGB", (640, 480), (40, 40, 40))
        first_annotated = first_enhanced
        first_frame_dets = []

    risk = compute_risk(all_dets)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    heatmap = build_heatmap(first_enhanced, first_frame_dets)

    pdf_bytes = build_pdf(
        mission_id, vessel_name, inspector, "video",
        all_dets, first_enhanced, first_annotated, heatmap,
        risk, grade, conf_thr, iou_thr,
    )
    if (pwd := (pdf_password or "").strip()):
        pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)

    filename = f"NautiCAI_Video_Report_{mission_id}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Signup (demo gate) ──────────────────────────────────────────────────
class SignupBody(BaseModel):
    name: str
    email: str
    whatsapp: str = ""
    alerts_whatsapp: bool = False


@app.post("/api/signup")
async def signup(body: SignupBody):
    """Store demo signup; used by demo gate before redirecting to app."""
    _store_signup({
        "name": body.name,
        "email": body.email,
        "whatsapp": body.whatsapp,
        "alerts_whatsapp": body.alerts_whatsapp,
    })
    return {"ok": True, "message": "Signed up. Redirecting to demo…"}


# ── WhatsApp: send message (alerts / normal) ─────────────────────────────
class WhatsAppSendBody(BaseModel):
    to: str  # E.164 or whatsapp:+1234567890
    message: str


@app.post("/api/whatsapp/send")
async def whatsapp_send(body: WhatsAppSendBody):
    """Send a text message to WhatsApp. Requires Twilio env vars."""
    result = _send_whatsapp(body.to, body.message)
    return result


# ── WhatsApp: send PDF (one-time link) ───────────────────────────────────
def _normalize_phone(phone: str) -> str:
    p = "".join(c for c in phone if c.isdigit() or c == "+")
    if not p.startswith("+"):
        p = "+" + p
    return p


# ── Export detections as CSV (API) ───────────────────────────────────────
class ExportDetectionsBody(BaseModel):
    detections: list = []  # [{ id, class, confidence, severity, bbox }, ...]


@app.post("/api/export/csv")
async def export_detections_csv(body: ExportDetectionsBody):
    """Return detections as CSV file. Same shape as client-side export."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["id", "class", "confidence", "severity", "bbox"])
    for d in body.detections:
        bbox = d.get("bbox")
        bbox_str = str(bbox) if bbox is not None else ""
        writer.writerow([
            d.get("id", ""),
            d.get("class", d.get("class_name", "")),
            d.get("confidence", ""),
            d.get("severity", ""),
            bbox_str,
        ])
    out.seek(0)
    filename = f"NautiCAI_detections_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(out.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/report/download/{report_id}")
async def report_download(report_id: str, password: str = Query(None)):
    """One-time PDF download (used by WhatsApp link). If report was stored with a password, ?password= is required."""
    if report_id not in _report_downloads:
        return JSONResponse({"error": "Not found or expired"}, status_code=404)
    entry = _report_downloads[report_id]
    pdf_bytes, _, download_pwd = entry[0], entry[1], (entry[2] if len(entry) > 2 else None)
    if download_pwd and password != download_pwd:
        return JSONResponse({"error": "Password required or incorrect"}, status_code=401)
    del _report_downloads[report_id]
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="NautiCAI_Report.pdf"'},
    )


@app.post("/api/report/pdf/send-whatsapp")
async def pdf_send_whatsapp(
    file: UploadFile = File(...),
    to: str = Form(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
    sev_filter: str = Form("All Detections"),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    marine_snow: bool = Form(False),
    pdf_password: str = Form(""),
):
    """Generate PDF and send to WhatsApp. Optional pdf_password encrypts the PDF; we include it in the message for the recipient."""
    pil_img = _read_upload(file)
    enhanced = full_enhance(pil_img, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip, marine_snow)
    dets = run_detection(enhanced, conf_thr, iou_thr, mode)
    SEV_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    if sev_filter == "Critical Only":
        dets = [d for d in dets if d["severity"] == "Critical"]
    elif sev_filter == "High+":
        dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 3]
    elif sev_filter == "Medium+":
        dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 2]
    annotated = annotate_image(enhanced, dets)
    heatmap = build_heatmap(enhanced, dets)
    risk = compute_risk(dets)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    pdf_bytes = build_pdf(
        mission_id, vessel_name, inspector, mode,
        dets, pil_img, annotated, heatmap,
        risk, grade, conf_thr, iou_thr,
    )
    pwd = (pdf_password or "").strip()
    if pwd:
        pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)
    rid = uuid.uuid4().hex[:12]
    _report_downloads[rid] = (pdf_bytes, datetime.datetime.now(), None)
    base_url = os.environ.get("NAUTICAI_BASE_URL", "").rstrip("/")
    download_url = f"{base_url}/api/report/download/{rid}" if base_url else None
    phone = _normalize_phone(to)
    body_text = f"NautiCAI inspection report {mission_id} is ready. Download: {download_url}"
    if pwd:
        body_text += f"\nPassword to open PDF: {pwd}"
    if not download_url:
        body_text = f"NautiCAI report {mission_id} generated. Log in to the demo to download."
        if pwd:
            body_text += f" Password to open PDF: {pwd}"
    result = _send_whatsapp(phone, body_text, media_url=download_url if download_url else None)
    result["download_url"] = download_url
    return result


@app.post("/api/report/pdf/video/send-whatsapp")
async def pdf_video_send_whatsapp(
    file: UploadFile = File(...),
    to: str = Form(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
    sample_n: int = Form(10),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    pdf_password: str = Form(""),
):
    """Generate video PDF and send to WhatsApp. Optional pdf_password encrypts the PDF."""
    import cv2
    suffix = Path(file.filename or "video.mp4").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        tf.write(await file.read())
        tmp_path = tf.name
    cap = cv2.VideoCapture(tmp_path)
    all_dets = []
    first_enhanced = first_annotated = first_frame_dets = None
    fn = 0
    det_id_offset = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if fn % sample_n == 0:
            pf = cv_to_pil(frame)
            ef = full_enhance(pf, use_clahe, use_green, 0.0, corr_turb, use_edge, clahe_clip)
            df_v = run_detection(ef, conf_thr, iou_thr, mode)
            for d in df_v:
                det_id_offset += 1
                d["id"] = det_id_offset
                d["frame"] = fn
            all_dets.extend(df_v)
            af = annotate_image(ef, df_v)
            if first_enhanced is None:
                first_enhanced, first_annotated, first_frame_dets = ef, af, df_v
        fn += 1
    cap.release()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    if first_enhanced is None:
        first_enhanced = Image.new("RGB", (640, 480), (40, 40, 40))
        first_annotated = first_enhanced
        first_frame_dets = []
    risk = compute_risk(all_dets)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    heatmap = build_heatmap(first_enhanced, first_frame_dets)
    pdf_bytes = build_pdf(
        mission_id, vessel_name, inspector, "video",
        all_dets, first_enhanced, first_annotated, heatmap,
        risk, grade, conf_thr, iou_thr,
    )
    pwd = (pdf_password or "").strip()
    if pwd:
        pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)
    rid = uuid.uuid4().hex[:12]
    _report_downloads[rid] = (pdf_bytes, datetime.datetime.now(), None)
    base_url = os.environ.get("NAUTICAI_BASE_URL", "").rstrip("/")
    download_url = f"{base_url}/api/report/download/{rid}" if base_url else None
    phone = _normalize_phone(to)
    body_text = f"NautiCAI video report {mission_id} ready. Download: {download_url}"
    if pwd:
        body_text += f"\nPassword to open PDF: {pwd}"
    if not download_url:
        body_text = f"NautiCAI video report {mission_id} generated."
        if pwd:
            body_text += f" Password to open PDF: {pwd}"
    result = _send_whatsapp(phone, body_text)
    result["download_url"] = download_url
    return result
