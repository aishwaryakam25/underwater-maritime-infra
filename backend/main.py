"""
NautiCAI — FastAPI Backend
Serves the detection engine, visibility enhancement, PDF report, and heatmap APIs.
Run: uvicorn backend.main:app --reload --port 8000
"""
import io, os, sys, uuid, datetime, base64, tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
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
):
    """Generate and download a PDF inspection report."""
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
