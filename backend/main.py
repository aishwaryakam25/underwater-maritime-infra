import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from pdf_report import build_pdf, build_batch_pdf
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
from detection import (
    run_detection, annotate_image, build_heatmap, get_model_name, load_yolo,
    AVAILABLE_MODELS, MODEL_DESCRIPTIONS, set_active_model, get_active_model_key
)

# Also make app/pdf_report.py importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
from pdf_report import build_pdf, build_batch_pdf

app = FastAPI(
    title="NautiCAI API",
    description="Underwater Infrastructure Inspection Copilot — API",
    version="1.0.5",
)

# Allow React dev server and deployed frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Batch PDF Report Endpoint ─────────────────────────────────────────────
from typing import List, Optional

@app.post("/api/report/pdf/batch")
async def report_pdf_batch(
    files: List[UploadFile] = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    sev_filter: str = Form("All Detections"),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    marine_snow: bool = Form(False),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
    pdf_password: Optional[str] = Form(None),
):
    batch_results = []
    for file in files:
        pil_img = Image.open(io.BytesIO(await file.read())).convert("RGB")
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
        batch_results.append({
            "filename": file.filename or "image",
            "orig_img": pil_img,
            "enhanced_img": enhanced,
            "annotated_img": annotated,
            "heatmap_img": heatmap,
            "dets": dets,
            "risk": risk,
            "grade": grade,
        })
    pdf_bytes = build_batch_pdf(
        batch_results=batch_results,
        vessel_name=vessel_name,
        inspector=inspector,
        pdf_password=pdf_password,
    )
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="NautiCAI_Batch_Report.pdf"'},
    )

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
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_num = os.environ.get("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    if not sid or not token:
        return {"sent": False, "message": "WhatsApp not configured."}
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


# ── Startup ───────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    load_yolo()


# ── Helpers ───────────────────────────────────────────────────────────────
def _pil_to_b64(img: Image.Image, fmt="PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()

def _read_upload(file: UploadFile) -> Image.Image:
    return Image.open(io.BytesIO(file.file.read())).convert("RGB")

def _b64_to_pil(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


# ── Model Management ──────────────────────────────────────────────────────
@app.get("/api/models")
async def list_models():
    """List all available models."""
    return {
        "active": get_active_model_key(),
        "available": {k: MODEL_DESCRIPTIONS.get(k, k) for k in AVAILABLE_MODELS}
    }

@app.post("/api/models/switch")
async def switch_model(model_key: str = Form(...)):
    """Switch active detection model."""
    if model_key not in AVAILABLE_MODELS:
        return JSONResponse({"error": f"Model {model_key} not found"}, status_code=404)
    set_active_model(model_key)
    load_yolo()
    return {
        "ok": True,
        "active_model": model_key,
        "description": MODEL_DESCRIPTIONS.get(model_key, "")
    }


# ── Routes ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    model_name = get_model_name()
    return {
        "status": "ok",
        "model": model_name,
        "active_model": get_active_model_key(),
        "version": "1.0.5"
    }


@app.post("/api/detect")
async def detect(
    file: UploadFile = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    sev_filter: str = Form("All Detections"),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    marine_snow: bool = Form(False),
):
    import traceback
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("detect-endpoint")
    try:
        pil_img = _read_upload(file)
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
        scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for d in dets:
            sev_counts[d.get("severity", "Medium")] += 1

        return {
            "mission_id": mission_id,
            "scan_time": scan_time,
            "model": get_model_name(),
            "active_model": get_active_model_key(),
            "detections": dets,
            "risk_score": risk,
            "grade": grade,
            "sev_counts": sev_counts,
            "total": len(dets),
            "annotated_b64": _pil_to_b64(annotated),
            "heatmap_b64": _pil_to_b64(heatmap),
            "enhanced_b64": _pil_to_b64(enhanced),
        }
    except Exception as e:
        logger.error("ERROR in /api/detect: %s", e, exc_info=True)
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)


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
    import cv2
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
        "active_model": get_active_model_key(),
        "frames_processed": fn // sample_n + 1,
        "sample_frames": frame_results,
        "detections": all_dets[:100],
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
            ef = full_enhance(pf, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip)
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
    if (pwd := (pdf_password or "").strip()):
        pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)
    filename = f"NautiCAI_Video_Report_{mission_id}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Signup ────────────────────────────────────────────────────────────────
class SignupBody(BaseModel):
    name: str
    email: str
    whatsapp: str = ""
    alerts_whatsapp: bool = False

@app.post("/api/signup")
async def signup(body: SignupBody):
    _store_signup({
        "name": body.name,
        "email": body.email,
        "whatsapp": body.whatsapp,
        "alerts_whatsapp": body.alerts_whatsapp,
    })
    return {"ok": True, "message": "Signed up. Redirecting to demo…"}


# ── WhatsApp ──────────────────────────────────────────────────────────────
class WhatsAppSendBody(BaseModel):
    to: str
    message: str

@app.post("/api/whatsapp/send")
async def whatsapp_send(body: WhatsAppSendBody):
    result = _send_whatsapp(body.to, body.message)
    return result


def _normalize_phone(phone: str) -> str:
    p = "".join(c for c in phone if c.isdigit() or c == "+")
    if not p.startswith("+"):
        p = "+" + p
    return p


# ── Export CSV ────────────────────────────────────────────────────────────
class ExportDetectionsBody(BaseModel):
    detections: list = []

@app.post("/api/export/csv")
async def export_detections_csv(body: ExportDetectionsBody):
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


@app.post("/api/detect/batch")
async def detect_batch(
    files: list[UploadFile] = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    sev_filter: str = Form("All Detections"),
    use_clahe: bool = Form(True),
    clahe_clip: float = Form(3.0),
    use_green: bool = Form(True),
    use_edge: bool = Form(False),
    turbidity_in: float = Form(0.0),
    corr_turb: bool = Form(True),
    marine_snow: bool = Form(False),
):
    """Run detection on multiple images at once. Returns results per image + combined summary."""
    SEV_RANK = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    results = []
    all_dets = []
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    for i, file in enumerate(files):
        try:
            pil_img = _read_upload(file)
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
            dets = run_detection(enhanced, conf_thr, iou_thr, mode)

            if sev_filter == "Critical Only":
                dets = [d for d in dets if d["severity"] == "Critical"]
            elif sev_filter == "High+":
                dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 3]
            elif sev_filter == "Medium+":
                dets = [d for d in dets if SEV_RANK.get(d["severity"], 0) >= 2]

            annotated = annotate_image(enhanced, dets)
            risk = compute_risk(dets)
            grade = score_to_grade(risk)
            sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
            for d in dets:
                sev_counts[d.get("severity", "Medium")] += 1
            all_dets.extend(dets)

            results.append({
                "image_index": i,
                "filename": file.filename or f"image_{i+1}",
                "total": len(dets),
                "risk_score": risk,
                "grade": grade,
                "sev_counts": sev_counts,
                "detections": dets,
                "annotated_b64": _pil_to_b64(annotated),
            })
        except Exception as e:
            results.append({
                "image_index": i,
                "filename": file.filename or f"image_{i+1}",
                "error": str(e),
            })

    total_risk = compute_risk(all_dets)
    total_grade = score_to_grade(total_risk)
    total_sev = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for d in all_dets:
        total_sev[d.get("severity", "Medium")] += 1

    return {
        "mission_id": mission_id,
        "scan_time": scan_time,
        "model": get_model_name(),
        "active_model": get_active_model_key(),
        "total_images": len(files),
        "total_detections": len(all_dets),
        "overall_risk_score": total_risk,
        "overall_grade": total_grade,
        "overall_sev_counts": total_sev,
        "results": results,
    }


@app.post("/api/detect/3d")
async def detect_3d(
    file: UploadFile = File(...),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    pipeline_length: float = Form(100.0),
):
    """Run YOLO detection and return 3D twin mapping data."""
    pil_img = _read_upload(file)
    enhanced = full_enhance(pil_img, use_clahe=True, use_green=True,
                            turb_in=0.0, corr_turb=True, use_edge=False,
                            clahe_clip=3.0, marine_snow=False)
    dets = run_detection(enhanced, conf_thr, iou_thr, "pipeline")
    W, H = enhanced.size

    # Map detections to 3D pipeline coordinates
    twin_defects = []
    for d in dets:
        cx = (d["x1"] + d["x2"]) / 2
        cy = (d["y1"] + d["y2"]) / 2
        pipeline_pos = (cx / W) * pipeline_length
        angle = (cy / H) * 6.28318
        twin_defects.append({
            "id": d["id"],
            "cls": d["cls"],
            "severity": d["severity"],
            "conf": round(d["conf"], 3),
            "pipeline_pos": round(pipeline_pos, 2),
            "angle": round(angle, 4),
            "x1": d["x1"], "y1": d["y1"],
            "x2": d["x2"], "y2": d["y2"],
        })

    risk = compute_risk(dets)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"

    return {
        "mission_id": mission_id,
        "total_defects": len(dets),
        "risk_score": risk,
        "grade": grade,
        "pipeline_length": pipeline_length,
        "model": get_model_name(),
        "active_model": get_active_model_key(),
        "defects_3d": twin_defects,
        "annotated_b64": _pil_to_b64(annotate_image(enhanced, dets)),
    }


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
        body_text = f"NautiCAI report {mission_id} generated."
        if pwd:
            body_text += f" Password to open PDF: {pwd}"
    result = _send_whatsapp(phone, body_text, media_url=download_url if download_url else None)
    result["download_url"] = download_url
    return result