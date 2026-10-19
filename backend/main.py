"""
NautiCAI — FastAPI Backend
Serves the detection engine, visibility enhancement, PDF report, and heatmap APIs.
Run: uvicorn backend.main:app --reload --port 8000
"""
import io, os, sys, uuid, datetime, base64, tempfile, csv, time, hashlib, logging
from pathlib import Path

logger = logging.getLogger("nauticai.api")

# Load .env from backend folder so TWILIO_* and NAUTICAI_BASE_URL work without setting in shell
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass

from fastapi import FastAPI, File, UploadFile, Form, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from PIL import Image

# Ensure backend/ imports win over app/
sys.path.insert(0, str(Path(__file__).resolve().parent))

_app_dir = Path(__file__).resolve().parent.parent / "app"
if str(_app_dir) not in sys.path:
    sys.path.append(str(_app_dir))
from pdf_report import build_pdf, build_batch_pdf

from severity import (
    compute_risk,
    score_to_grade,
    ARCHIVE_MODEL_CLASSES_19,
    OFFICIAL_DEFECT_CLASSES_19,
    official_19_only_outputs,
    filter_defects_to_official_19,
)
from defect_taxonomy import taxonomy_payload
from visibility import full_enhance, pil_to_cv, cv_to_pil, apply_clahe, apply_green_water, apply_turbidity, apply_edge_estimator
from inspection_provenance import NAUTICAI_API_VERSION, collect_inspection_provenance

from detection import (
    run_detection, annotate_image, build_heatmap, get_model_name, load_yolo,
    split_asset_and_defects,
    boxes_for_visualization,
    AVAILABLE_MODELS, MODEL_DESCRIPTIONS, set_active_model, get_active_model_key,
    is_taxonomy_model_key,
)

_SIGNUPS_DIR = Path(__file__).resolve().parent
_signups_file = _SIGNUPS_DIR / "signups.json"
_report_downloads: dict = {}


def _encrypt_pdf(data: bytes, password: str) -> bytes:
    if not (password or "").strip():
        return data
    try:
        from io import BytesIO
        from pypdf import PdfReader, PdfWriter

        r = PdfReader(BytesIO(data))
        w = PdfWriter()
        for page in r.pages:
            w.add_page(page)
        w.encrypt(password.strip())
        out = BytesIO()
        w.write(out)
        return out.getvalue()
    except Exception:
        return data


_REPO_ROOT = Path(__file__).resolve().parent.parent

SEV_RANK_FILTER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}


def _retry_if_only_pipeline(det_img, iou_thr, mode: str, effective_conf: float, dets: list) -> tuple[list, float]:
    """Retry lower confidence on the same image tensor used for inference (must match annotate/heatmap)."""
    if mode != "general" or not dets:
        return dets, effective_conf
    _, defects = split_asset_and_defects(dets, mode)
    if defects:
        return dets, effective_conf
    if effective_conf > 0.05:
        dets = run_detection(det_img, 0.05, iou_thr, mode)
        effective_conf = 0.05
    _, defects = split_asset_and_defects(dets, mode)
    if defects:
        return dets, effective_conf
    if effective_conf > 0.02:
        dets = run_detection(det_img, 0.02, iou_thr, mode)
        effective_conf = 0.02
    return dets, effective_conf


def _apply_sev_filter(defects: list, sev_filter: str) -> list:
    if sev_filter == "Critical Only":
        return [d for d in defects if d["severity"] == "Critical"]
    if sev_filter == "High+":
        return [d for d in defects if SEV_RANK_FILTER.get(d["severity"], 0) >= 3]
    if sev_filter == "Medium+":
        return [d for d in defects if SEV_RANK_FILTER.get(d["severity"], 0) >= 2]
    return list(defects)


def _finalize_inspection(dets: list, mode: str, sev_filter: str) -> tuple[list, list, list]:
    assets, defects = split_asset_and_defects(dets, mode)
    defects = _apply_sev_filter(defects, sev_filter)
    # By default, we expose only the Severity Table 19 labels.
    # But taxonomy models (e.g. hull/subsea trained with configs/*_defects.yaml) must be allowed
    # to return their richer class sets (barnacles, algae, etc.).
    if official_19_only_outputs() and (not is_taxonomy_model_key(get_active_model_key())):
        defects = filter_defects_to_official_19(defects)
    else:
        for i, d in enumerate(defects, 1):
            d["id"] = i
    combined = assets + defects
    return assets, defects, combined


def _defects_from_raw(raw_dets: list, mode: str, sev_filter: str = "All Detections") -> list:
    """Public defect list: asset split + severity filter + optional official-19-only."""
    _, defects, _ = _finalize_inspection(raw_dets, mode, sev_filter)
    return defects


def _raw_dets_for_video_frame(frame_idx: int, sample_n: int, by_frame: dict) -> list:
    """Bucket + nearest sampled frame — matches VideoLiveAnalysis overlay behaviour."""
    sn = max(1, int(sample_n) if sample_n else 10)
    bucket = (int(frame_idx) // sn) * sn
    if bucket in by_frame:
        return by_frame[bucket]
    if not by_frame:
        return []
    nearest = min(by_frame.keys(), key=lambda f: abs(int(f) - int(frame_idx)))
    return by_frame[nearest]


app = FastAPI(
    title="NautiCAI API",
    description="Underwater Infrastructure Inspection Copilot — API",
    version=NAUTICAI_API_VERSION,
)

# Register innovation routes (for weld inspection and more)

from innovation_routes import router as innovation_router
app.include_router(innovation_router)

# Include sonar_routes for /api/sonar endpoints
from sonar_routes import router as sonar_router
app.include_router(sonar_router)

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
    report_style: str = Form("diver_hull"),
    vessel_imo: str = Form(""),
    report_place: str = Form(""),
    report_activity: str = Form("U/W Hull Cleaning & Propeller polishing."),
    job_number: str = Form(""),
):
    try:
        t_batch0 = time.perf_counter()
        batch_results = []
        for file in files:
            pil_img = Image.open(io.BytesIO(await file.read())).convert("RGB")
            pil_img = _limit_long_edge(pil_img, max_side=4096)
            enhanced = full_enhance(pil_img, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip, marine_snow)
            eff = conf_thr
            dets = run_detection(enhanced, eff, iou_thr, mode)
            if not dets and conf_thr > 0.05:
                eff = 0.05
                dets = run_detection(enhanced, eff, iou_thr, mode)
            if not dets and conf_thr > 0.02:
                eff = 0.02
                dets = run_detection(enhanced, eff, iou_thr, mode)
            dets, _ = _retry_if_only_pipeline(enhanced, iou_thr, mode, eff, dets)
            assets, defects, combined = _finalize_inspection(dets, mode, sev_filter)
            annotated = annotate_image(
                enhanced, boxes_for_visualization(assets, defects, mode), mode=mode,
            )
            heatmap = build_heatmap(enhanced, defects)
            risk = compute_risk(defects)
            grade = score_to_grade(risk)
            batch_results.append({
                "filename": file.filename or "image",
                "orig_img": pil_img,
                "enhanced_img": enhanced,
                "annotated_img": annotated,
                "heatmap_img": heatmap,
                "dets": defects,
                "risk": risk,
                "grade": grade,
            })
        inference_ms = (time.perf_counter() - t_batch0) * 1000.0
        cover_ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
        batch_mid = f"BATCH-{hashlib.sha256((cover_ts + vessel_name).encode()).hexdigest()[:8]}"
        batch_provenance = collect_inspection_provenance(
            mission_id=batch_mid,
            mode=mode,
            conf_thr=conf_thr,
            iou_thr=iou_thr,
            use_clahe=use_clahe,
            clahe_clip=clahe_clip,
            use_green=use_green,
            use_edge=use_edge,
            turbidity_in=turbidity_in,
            corr_turb=corr_turb,
            marine_snow=marine_snow,
            sev_filter=sev_filter,
            sample_stride=None,
        )
        diver_meta = {}
        if (vessel_imo or "").strip():
            diver_meta["imo"] = vessel_imo.strip()
        if (report_place or "").strip():
            diver_meta["place"] = report_place.strip()
        if (report_activity or "").strip():
            diver_meta["activity"] = report_activity.strip()
        if (job_number or "").strip():
            diver_meta["job_number"] = job_number.strip()

        pdf_bytes = build_batch_pdf(
            batch_results=batch_results,
            vessel_name=vessel_name,
            inspector=inspector,
            pdf_password=pdf_password,
            inference_ms=inference_ms,
            provenance=batch_provenance,
            mission_id=batch_mid,
            cover_ts=cover_ts,
            report_style=report_style,
            diver_meta=diver_meta,
        )
        rs = (report_style or "diver_hull").strip().lower().replace("-", "_")
        batch_filename = (
            "NautiCAI_Hull_Cleaning_Report.pdf"
            if rs in ("diver", "diver_hull", "hull_diver", "panama_style")
            else "NautiCAI_Batch_Report.pdf"
        )
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{batch_filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/report/pdf/batch failed")
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)[:900]}",
        ) from e

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


def _limit_long_edge(pil_img: Image.Image, max_side: int = 4096) -> Image.Image:
    """Avoid OOM / ReportLab blow-ups on very large ROV frames (PDF batch re-infers per file)."""
    w, h = pil_img.size
    longest = max(w, h)
    if longest <= max_side:
        return pil_img
    scale = max_side / float(longest)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS  # Pillow < 9.1
    return pil_img.resize((nw, nh), resample)


def _b64_to_pil(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")


# ── Model Management ──────────────────────────────────────────────────────
@app.get("/api/models")
async def list_models():
    """List all available models and whether each weight file exists on disk."""
    return {
        "active": get_active_model_key(),
        "available": {k: MODEL_DESCRIPTIONS.get(k, k) for k in AVAILABLE_MODELS},
        "weight_paths": {k: str(_REPO_ROOT / rel) for k, rel in AVAILABLE_MODELS.items()},
        "file_exists": {k: (_REPO_ROOT / rel).is_file() for k, rel in AVAILABLE_MODELS.items()},
    }


@app.post("/api/models/switch")
async def switch_model(model_key: str = Form(...)):
    """Switch active detection model."""
    if model_key not in AVAILABLE_MODELS:
        return JSONResponse({"error": f"Model {model_key} not found"}, status_code=404)
    rel = AVAILABLE_MODELS[model_key]
    weight_path = _REPO_ROOT / rel
    missing = not weight_path.is_file()
    set_active_model(model_key)
    load_yolo()
    out = {
        "ok": True,
        "active_model": model_key,
        "description": MODEL_DESCRIPTIONS.get(model_key, ""),
        "weight_path": str(weight_path),
        "weight_missing": missing,
    }
    if missing:
        out["warning"] = (
            f"No file at {weight_path}; inference may fall back to another weight on disk. "
            "Copy your trained best.pt to that path."
        )
    return out


# ── Routes ────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    model_name = get_model_name()
    return {
        "status": "ok",
        "model": model_name,
        "active_model": get_active_model_key(),
        "version": "1.0.5",
    }


@app.get("/api/model/classes")
async def model_classes():
    return {
        "active_model": get_active_model_key(),
        "official_defect_classes_19": OFFICIAL_DEFECT_CLASSES_19,
        "archive_yolo_categories_19": ARCHIVE_MODEL_CLASSES_19,
        "note": (
            "Three cases: (1) active_model=archive expects archive_yolo_categories_19 — CLASS_REMAP maps "
            "those raw names to official_defect_classes_19. "
            "(2) Trained on configs/nauticai_official_19.yaml — use official_19 or merged_original; "
            "CLASS_REMAP skipped when raw label matches an official class. "
            "(3) subsea_taxonomy/hull_taxonomy use extended taxonomy labels. "
            "By default NAUTICAI_OFFICIAL_19_ONLY=true strips API responses to only official_defect_classes_19."
        ),
        "training_yaml": "configs/nauticai_official_19.yaml",
        "target_taxonomy_url": "/api/defect-taxonomy",
    }


@app.get("/api/defect-taxonomy")
async def defect_taxonomy():
    return taxonomy_payload()


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
        eff = conf_thr
        dets = run_detection(enhanced, eff, iou_thr, mode)
        if not dets and conf_thr > 0.05:
            eff = 0.05
            dets = run_detection(enhanced, eff, iou_thr, mode)
        if not dets and conf_thr > 0.02:
            eff = 0.02
            dets = run_detection(enhanced, eff, iou_thr, mode)
        dets, _ = _retry_if_only_pipeline(enhanced, iou_thr, mode, eff, dets)
        assets, defects, combined = _finalize_inspection(dets, mode, sev_filter)

        annotated = annotate_image(
            enhanced, boxes_for_visualization(assets, defects, mode), mode=mode,
        )
        heatmap = build_heatmap(enhanced, defects)
        risk = compute_risk(defects)
        grade = score_to_grade(risk)
        mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
        scan_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for d in defects:
            sev_counts[d.get("severity", "Medium")] += 1

        return {
            "mission_id": mission_id,
            "scan_time": scan_time,
            "model": get_model_name(),
            "active_model": get_active_model_key(),
            "detections": defects,
            "risk_score": risk,
            "grade": grade,
            "sev_counts": sev_counts,
            "total": len(defects),
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
    try:
        pil_img = _read_upload(file)
        pil_img = _limit_long_edge(pil_img, max_side=4096)
        enhanced = full_enhance(pil_img, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip, marine_snow)
        eff = conf_thr
        dets = run_detection(enhanced, eff, iou_thr, mode)
        if not dets and conf_thr > 0.05:
            eff = 0.05
            dets = run_detection(enhanced, eff, iou_thr, mode)
        if not dets and conf_thr > 0.02:
            eff = 0.02
            dets = run_detection(enhanced, eff, iou_thr, mode)
        dets, _ = _retry_if_only_pipeline(enhanced, iou_thr, mode, eff, dets)
        assets, defects, combined = _finalize_inspection(dets, mode, sev_filter)
        annotated = annotate_image(
            enhanced, boxes_for_visualization(assets, defects, mode), mode=mode,
        )
        heatmap = build_heatmap(enhanced, defects)
        risk = compute_risk(defects)
        grade = score_to_grade(risk)
        mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
        provenance_pdf = collect_inspection_provenance(
            mission_id=mission_id,
            mode=mode,
            conf_thr=conf_thr,
            iou_thr=iou_thr,
            use_clahe=use_clahe,
            clahe_clip=clahe_clip,
            use_green=use_green,
            use_edge=use_edge,
            turbidity_in=turbidity_in,
            corr_turb=corr_turb,
            marine_snow=marine_snow,
            sev_filter=sev_filter,
            sample_stride=None,
        )
        pdf_bytes = build_pdf(
            mission_id, vessel_name, inspector, mode,
            defects, pil_img, enhanced, annotated, heatmap,
            risk, grade, conf_thr, iou_thr,
            model_name=get_model_name(),
            provenance=provenance_pdf,
        )
        if (pwd := (pdf_password or "").strip()):
            pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)
        filename = f"NautiCAI_Report_{mission_id}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/report/pdf failed")
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)[:900]}",
        ) from e


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
            df_assets, df_pub, df_combined = _finalize_inspection(df_v, mode, "All Detections")
            af = annotate_image(
                ef, boxes_for_visualization(df_assets, df_pub, mode), mode=mode,
            )
            if len(frame_results) < 4:
                frame_results.append({
                    "frame_num": fn,
                    "detection_count": len(df_pub),
                    "annotated_b64": _pil_to_b64(af),
                })
        fn += 1
    cap.release()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    defects_pub = _defects_from_raw(all_dets, mode)
    risk = compute_risk(defects_pub)
    grade = score_to_grade(risk)
    fps_safe = float(fps_v) if fps_v and fps_v > 0.5 else 25.0
    for d in defects_pub:
        fn_d = d.get("frame")
        if fn_d is not None:
            try:
                d["time_sec"] = round(float(fn_d) / fps_safe, 4)
            except (TypeError, ValueError):
                pass
    # One entry per frame that has ≥1 detection (full video), for UI timeline — avoids losing later hits when capping detections.
    frame_primary_cls: dict = {}
    for d in defects_pub:
        fn_d = d.get("frame")
        if fn_d is None:
            continue
        try:
            fi = int(fn_d)
        except (TypeError, ValueError):
            continue
        if fi not in frame_primary_cls:
            frame_primary_cls[fi] = str(d.get("cls") or d.get("class") or "Unknown")
    timeline_hits = [{"frame": fi, "cls": frame_primary_cls[fi]} for fi in sorted(frame_primary_cls.keys())]

    video_dets_cap = 12000
    det_slice = defects_pub[:video_dets_cap]
    return {
        "video_info": {
            "total_frames": total,
            "fps": round(fps_v, 1),
            "resolution": f"{wv}x{hv}",
            "duration": round(total / fps_safe, 1),
        },
        "sample_stride": sample_n,
        "total_detections": len(defects_pub),
        "risk_score": risk,
        "grade": grade,
        "active_model": get_active_model_key(),
        "frames_processed": (fn + sample_n - 1) // sample_n if fn else 0,
        "sample_frames": frame_results,
        "timeline_hits": timeline_hits,
        "detections_truncated": len(defects_pub) > len(det_slice),
        "detections": det_slice,
    }


@app.post("/api/video/export-annotated")
async def video_export_annotated(
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
    """Full-length MP4 with boxes/labels burned in (same enhancement + sampling as /api/video/detect)."""
    import cv2
    import numpy as np

    suffix = Path(file.filename or "video.mp4").suffix or ".mp4"
    tmp_in = None
    tmp_out = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(await file.read())
            tmp_in = tf.name
        tmp_out = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name

        cap = cv2.VideoCapture(tmp_in)
        if not cap.isOpened():
            raise HTTPException(status_code=400, detail="Could not open video file.")

        fps_v = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        if fps_v < 0.5:
            fps_v = 25.0
        wv = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        hv = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if wv <= 0 or hv <= 0:
            cap.release()
            raise HTTPException(status_code=400, detail="Invalid video dimensions.")

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(tmp_out, fourcc, fps_v, (wv, hv))
        if not writer.isOpened():
            cap.release()
            raise HTTPException(
                status_code=500,
                detail="Video encoder failed to start (mp4v). Try re-encoding the source as H.264 MP4.",
            )

        by_frame: dict = {}
        fn = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                pf = cv_to_pil(frame)
                ef = full_enhance(
                    pf, use_clahe, use_green, turbidity_in, corr_turb, use_edge, clahe_clip,
                )
                sn = max(1, int(sample_n) if sample_n else 10)
                if fn % sn == 0:
                    df_v = run_detection(ef, conf_thr, iou_thr, mode)
                    by_frame[fn] = df_v

                raw = _raw_dets_for_video_frame(fn, sn, by_frame)
                df_assets, df_pub, _ = _finalize_inspection(raw, mode, "All Detections")
                annotated_pil = annotate_image(
                    ef,
                    boxes_for_visualization(df_assets, df_pub, mode),
                    mode=mode,
                )
                rgb = np.asarray(annotated_pil.convert("RGB"), dtype=np.uint8)
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
                writer.write(bgr)
                fn += 1
        finally:
            writer.release()
            cap.release()

        if fn == 0:
            raise HTTPException(status_code=400, detail="Video contained no frames.")

        with open(tmp_out, "rb") as f:
            out_bytes = f.read()
        if len(out_bytes) < 32:
            raise HTTPException(status_code=500, detail="Annotated video export produced an empty file.")

        base = Path(file.filename or "video").stem
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in base)[:120]
        filename = f"NautiCAI_annotated_{safe}.mp4"
        return StreamingResponse(
            io.BytesIO(out_bytes),
            media_type="video/mp4",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /api/video/export-annotated failed")
        raise HTTPException(
            status_code=500,
            detail=f"{type(e).__name__}: {str(e)[:900]}",
        ) from e
    finally:
        for p in (tmp_in, tmp_out):
            if p:
                try:
                    os.unlink(p)
                except OSError:
                    pass


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
    total_vc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_vc = cap.get(cv2.CAP_PROP_FPS) or 25
    all_dets = []
    first_enhanced = first_annotated = None
    first_raw_pil = None
    first_raw_frame_dets = []
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
            if first_enhanced is None:
                first_enhanced = ef
                first_raw_pil = pf.copy()
                first_raw_frame_dets = list(df_v)
        fn += 1
    cap.release()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    if first_enhanced is None:
        first_enhanced = Image.new("RGB", (640, 480), (40, 40, 40))
        first_raw_pil = first_enhanced
        first_raw_frame_dets = []
    defects_pub = _defects_from_raw(all_dets, mode)
    fps_safe_pdf = float(fps_vc) if fps_vc and fps_vc > 0.5 else 25.0
    duration_sec_pdf = round(total_vc / fps_safe_pdf, 1) if total_vc else 0.0
    frames_processed_pdf = (fn + sample_n - 1) // sample_n if fn else 0
    video_meta_pdf = {
        "duration_sec": duration_sec_pdf,
        "fps": round(fps_vc, 1),
        "total_frames": total_vc,
        "sample_stride": sample_n,
        "frames_processed": frames_processed_pdf,
        "total_detections": len(defects_pub),
    }
    first_assets, first_hm_defects, first_combined = _finalize_inspection(
        first_raw_frame_dets, mode, "All Detections",
    )
    first_annotated = annotate_image(
        first_enhanced,
        boxes_for_visualization(first_assets, first_hm_defects, mode),
        mode=mode,
    )
    risk = compute_risk(defects_pub)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    heatmap = build_heatmap(first_enhanced, first_hm_defects)
    provenance_pdf = collect_inspection_provenance(
        mission_id=mission_id,
        mode="video",
        conf_thr=conf_thr,
        iou_thr=iou_thr,
        use_clahe=use_clahe,
        clahe_clip=clahe_clip,
        use_green=use_green,
        use_edge=use_edge,
        turbidity_in=turbidity_in,
        corr_turb=corr_turb,
        marine_snow=False,
        sev_filter="All Detections",
        sample_stride=sample_n,
    )
    pdf_bytes = build_pdf(
        mission_id, vessel_name, inspector, "video",
        defects_pub, first_raw_pil or first_enhanced, first_enhanced, first_annotated, heatmap,
        risk, grade, conf_thr, iou_thr,
        model_name=get_model_name(),
        video_meta=video_meta_pdf,
        provenance=provenance_pdf,
    )
    if (pwd := (pdf_password or "").strip()):
        pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)
    filename = f"NautiCAI_Video_Report_{mission_id}_{datetime.datetime.now().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
    import cv2

    suffix = Path(file.filename or "video.mp4").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        tf.write(await file.read())
        tmp_path = tf.name
    cap = cv2.VideoCapture(tmp_path)
    total_vc = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps_vc = cap.get(cv2.CAP_PROP_FPS) or 25
    all_dets = []
    first_enhanced = first_annotated = None
    first_raw_pil = None
    first_raw_frame_dets = []
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
            if first_enhanced is None:
                first_enhanced = ef
                first_raw_pil = pf.copy()
                first_raw_frame_dets = list(df_v)
        fn += 1
    cap.release()
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    if first_enhanced is None:
        first_enhanced = Image.new("RGB", (640, 480), (40, 40, 40))
        first_raw_pil = first_enhanced
        first_raw_frame_dets = []
    defects_pub = _defects_from_raw(all_dets, mode)
    fps_safe_pdf = float(fps_vc) if fps_vc and fps_vc > 0.5 else 25.0
    duration_sec_pdf = round(total_vc / fps_safe_pdf, 1) if total_vc else 0.0
    frames_processed_pdf = (fn + sample_n - 1) // sample_n if fn else 0
    video_meta_pdf = {
        "duration_sec": duration_sec_pdf,
        "fps": round(fps_vc, 1),
        "total_frames": total_vc,
        "sample_stride": sample_n,
        "frames_processed": frames_processed_pdf,
        "total_detections": len(defects_pub),
    }
    first_assets, first_hm_defects, first_combined = _finalize_inspection(
        first_raw_frame_dets, mode, "All Detections",
    )
    first_annotated = annotate_image(
        first_enhanced,
        boxes_for_visualization(first_assets, first_hm_defects, mode),
        mode=mode,
    )
    risk = compute_risk(defects_pub)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    heatmap = build_heatmap(first_enhanced, first_hm_defects)
    provenance_pdf = collect_inspection_provenance(
        mission_id=mission_id,
        mode="video",
        conf_thr=conf_thr,
        iou_thr=iou_thr,
        use_clahe=use_clahe,
        clahe_clip=clahe_clip,
        use_green=use_green,
        use_edge=use_edge,
        turbidity_in=turbidity_in,
        corr_turb=corr_turb,
        marine_snow=False,
        sev_filter="All Detections",
        sample_stride=sample_n,
    )
    pdf_bytes = build_pdf(
        mission_id, vessel_name, inspector, "video",
        defects_pub, first_raw_pil or first_enhanced, first_enhanced, first_annotated, heatmap,
        risk, grade, conf_thr, iou_thr,
        model_name=get_model_name(),
        video_meta=video_meta_pdf,
        provenance=provenance_pdf,
    )
    pwd = (pdf_password or "").strip()
    if pwd:
        pdf_bytes = _encrypt_pdf(pdf_bytes, pwd)
    rid = uuid.uuid4().hex[:12]
    _report_downloads[rid] = (pdf_bytes, datetime.datetime.now(), None)
    base_url = os.environ.get("NAUTICAI_BASE_URL", "").rstrip("/")
    download_url = f"{base_url}/api/report/download/{rid}" if base_url else None
    phone = _normalize_phone(to)
    body_text = f"NautiCAI video report {mission_id} is ready. Download: {download_url}"
    if pwd:
        body_text += f"\nPassword to open PDF: {pwd}"
    if not download_url:
        body_text = f"NautiCAI video report {mission_id} generated."
        if pwd:
            body_text += f" Password to open PDF: {pwd}"
    result = _send_whatsapp(phone, body_text, media_url=download_url if download_url else None)
    result["download_url"] = download_url
    return result


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
            eff = conf_thr
            dets = run_detection(enhanced, eff, iou_thr, mode)
            if not dets and conf_thr > 0.05:
                eff = 0.05
                dets = run_detection(enhanced, eff, iou_thr, mode)
            if not dets and conf_thr > 0.02:
                eff = 0.02
                dets = run_detection(enhanced, eff, iou_thr, mode)
            dets, _ = _retry_if_only_pipeline(enhanced, iou_thr, mode, eff, dets)
            assets, defects, combined = _finalize_inspection(dets, mode, sev_filter)

            annotated = annotate_image(
                enhanced, boxes_for_visualization(assets, defects, mode), mode=mode,
            )
            risk = compute_risk(defects)
            grade = score_to_grade(risk)
            sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
            for d in defects:
                sev_counts[d.get("severity", "Medium")] += 1
            all_dets.extend(defects)

            results.append({
                "image_index": i,
                "filename": file.filename or f"image_{i+1}",
                "total": len(defects),
                "risk_score": risk,
                "grade": grade,
                "sev_counts": sev_counts,
                "detections": defects,
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
    eff = conf_thr
    dets = run_detection(enhanced, eff, iou_thr, "pipeline")
    if not dets and conf_thr > 0.05:
        dets = run_detection(enhanced, 0.05, iou_thr, "pipeline")
    if not dets and conf_thr > 0.02:
        dets = run_detection(enhanced, 0.02, iou_thr, "pipeline")
    W, H = enhanced.size

    assets, defects, combined = _finalize_inspection(dets, "pipeline", "All Detections")

    twin_defects = []
    for d in defects:
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

    risk = compute_risk(defects)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"

    return {
        "mission_id": mission_id,
        "total_defects": len(defects),
        "risk_score": risk,
        "grade": grade,
        "pipeline_length": pipeline_length,
        "model": get_model_name(),
        "active_model": get_active_model_key(),
        "defects_3d": twin_defects,
        "annotated_b64": _pil_to_b64(
            annotate_image(
                enhanced,
                boxes_for_visualization(assets, defects, "pipeline"),
                mode="pipeline",
            ),
        ),
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
    eff = conf_thr
    dets = run_detection(enhanced, eff, iou_thr, mode)
    if not dets and conf_thr > 0.05:
        eff = 0.05
        dets = run_detection(enhanced, eff, iou_thr, mode)
    if not dets and conf_thr > 0.02:
        eff = 0.02
        dets = run_detection(enhanced, eff, iou_thr, mode)
    dets, _ = _retry_if_only_pipeline(enhanced, iou_thr, mode, eff, dets)
    assets, defects, combined = _finalize_inspection(dets, mode, sev_filter)
    annotated = annotate_image(
        enhanced, boxes_for_visualization(assets, defects, mode), mode=mode,
    )
    heatmap = build_heatmap(enhanced, defects)
    risk = compute_risk(defects)
    grade = score_to_grade(risk)
    mission_id = f"M-{uuid.uuid4().hex[:6].upper()}"
    provenance_pdf = collect_inspection_provenance(
        mission_id=mission_id,
        mode=mode,
        conf_thr=conf_thr,
        iou_thr=iou_thr,
        use_clahe=use_clahe,
        clahe_clip=clahe_clip,
        use_green=use_green,
        use_edge=use_edge,
        turbidity_in=turbidity_in,
        corr_turb=corr_turb,
        marine_snow=marine_snow,
        sev_filter=sev_filter,
        sample_stride=None,
    )
    pdf_bytes = build_pdf(
        mission_id, vessel_name, inspector, mode,
        defects, pil_img, enhanced, annotated, heatmap,
        risk, grade, conf_thr, iou_thr,
        model_name=get_model_name(),
        provenance=provenance_pdf,
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