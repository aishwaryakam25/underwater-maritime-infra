from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional
import os, re, math, uuid, time, hashlib, json, html, numpy as np
from datetime import datetime

from detection import run_detection, split_asset_and_defects
from visibility import full_enhance
from severity import (
    compute_risk,
    score_to_grade,
    filter_defects_to_official_19,
    official_19_only_outputs,
)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

try:
    from PIL import Image as PILImage
    import io
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ── ReportLab imports ────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image as RLImage, PageBreak, HRFlowable,
    )
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    ImageReader = None  # type: ignore

router = APIRouter(prefix="/api/sonar", tags=["Sonar Analysis"])

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads", "sonar")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SUBPIPE_WEIGHTS = os.path.join(MODEL_DIR, "subpipe_best.pt")
MARINE_PULSE_WEIGHTS = os.path.join(MODEL_DIR, "marine_pulse_best.pt")

# ── Class map ────────────────────────────────────────────────────────────
DETECTION_CLASSES = {0: "pipeline"}

SEVERITY_MAP = {
    "pipeline": "medium", "cable": "medium", "debris": "high",
    "rock": "low", "wreck": "critical", "anomaly": "high", "other": "low",
}


def confidence_to_severity(class_name: str, confidence: float, bbox_area: float) -> str:
    static = SEVERITY_MAP.get(class_name)
    if static in ("critical", "high") and class_name not in ("pipeline", "cable"):
        return static
    if confidence >= 0.80:
        return "medium"
    elif confidence >= 0.55:
        return "high"
    else:
        return "critical"


_det_model = None
_cls_model = None
_det_load_err: Optional[str] = None
_cls_load_err: Optional[str] = None


def get_detection_model():
    global _det_model, _det_load_err
    if _det_load_err is not None:
        return None
    if _det_model is None and YOLO_AVAILABLE and os.path.exists(SUBPIPE_WEIGHTS):
        try:
            _det_model = YOLO(SUBPIPE_WEIGHTS)
        except Exception as e:
            _det_load_err = repr(e)
            return None
    return _det_model


def get_classification_model():
    global _cls_model, _cls_load_err
    if _cls_load_err is not None:
        return None
    if _cls_model is None and YOLO_AVAILABLE and os.path.exists(MARINE_PULSE_WEIGHTS):
        try:
            _cls_model = YOLO(MARINE_PULSE_WEIGHTS)
        except Exception as e:
            _cls_load_err = repr(e)
            return None
    return _cls_model


# ── Pydantic models ──────────────────────────────────────────────────────

class Detection(BaseModel):
    id: str
    class_name: str
    confidence: float
    severity: str
    bbox: List[float]
    area: float
    description: str

class AnalysisResult(BaseModel):
    image_id: str
    filename: str
    timestamp: str
    processing_time_ms: float
    image_width: int
    image_height: int
    total_detections: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    detections: List[Detection]
    overall_status: str
    summary: str
    model_info: dict


# ── Mock inference ───────────────────────────────────────────────────────

def run_mock_inference(filename: str) -> List[Detection]:
    np.random.seed(hash(filename) % 2**32)
    n = np.random.choice([1, 2, 3, 4], p=[0.3, 0.35, 0.25, 0.1])
    mock_classes = list(SEVERITY_MAP.keys())
    dets = []
    for _ in range(n):
        cn   = np.random.choice(mock_classes)
        conf = round(np.random.uniform(0.40, 0.98), 3)
        x1   = round(np.random.uniform(0.05, 0.70), 3)
        y1   = round(np.random.uniform(0.05, 0.70), 3)
        x2   = round(min(x1 + np.random.uniform(0.05, 0.25), 0.95), 3)
        y2   = round(min(y1 + np.random.uniform(0.05, 0.25), 0.95), 3)
        area = round((x2 - x1) * (y2 - y1), 4)
        sev  = confidence_to_severity(cn, conf, area)
        desc = f"{cn} detected ({conf:.0%}) — severity: {sev}"
        dets.append(Detection(
            id=f"DET-{uuid.uuid4().hex[:6].upper()}",
            class_name=cn, confidence=conf, severity=sev,
            bbox=[x1, y1, x2, y2], area=area, description=desc,
        ))
    return dets


analysis_history: list = []


def _sanitize_upload_filename(name: str) -> str:
    """Windows-safe basename for disk writes (avoids path injection and illegal chars)."""
    base = os.path.basename(name or "upload.png").strip() or "upload.png"
    base = re.sub(r'[<>:"/\\|?\x00-\x1f]', "_", base)
    return base[:240] if len(base) > 240 else base


def _finite_float(x, default: float = 0.0) -> float:
    """JSON cannot encode NaN/Inf — strip before building Pydantic / FastAPI responses."""
    try:
        v = float(x)
        return v if math.isfinite(v) else default
    except Exception:
        return default


def _clamp01(x) -> float:
    return max(0.0, min(1.0, _finite_float(x, 0.0)))


def _maybe_downscale_image_bytes(contents: bytes) -> tuple:
    """
    Side-scan strips are often huge (10k–50k px wide); Ultralytics can OOM or crash.
    Uniform resize keeps normalized xyxy boxes valid for the original aspect ratio.
    Returns (bytes_for_model, orig_width, orig_height).
    """
    if not PIL_AVAILABLE:
        return contents, 1920, 256
    try:
        img = PILImage.open(io.BytesIO(contents))
        img.load()
        w, h = img.size
        ow, oh = w, h
        max_side = int(os.environ.get("NAUTICAI_SONAR_MAX_SIDE", "4096"))
        max_px = int(os.environ.get("NAUTICAI_SONAR_MAX_PIXELS", "12000000"))
        if max(w, h) <= max_side and w * h <= max_px:
            return contents, ow, oh
        scale = min(max_side / max(w, h), math.sqrt(max_px / max(1, w * h)))
        scale = min(scale, 1.0)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        try:
            resample = PILImage.Resampling.LANCZOS
        except AttributeError:
            resample = PILImage.LANCZOS
        try:
            img = img.convert("RGB")
        except Exception:
            img = img.convert("L").convert("RGB")
        img = img.resize((nw, nh), resample)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue(), ow, oh
    except Exception:
        return contents, 1920, 256


def _apply_sev_filter_anomaly(defects: list, sev_filter: str) -> list:
    rank = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
    if sev_filter == "Critical Only":
        return [d for d in defects if d["severity"] == "Critical"]
    if sev_filter == "High+":
        return [d for d in defects if rank.get(d["severity"], 0) >= 3]
    if sev_filter == "Medium+":
        return [d for d in defects if rank.get(d["severity"], 0) >= 2]
    return list(defects)


def _finalize_anomaly_detections(raw_dets: list, mode: str, sev_filter: str) -> list:
    _, defects = split_asset_and_defects(raw_dets, mode)
    defects = _apply_sev_filter_anomaly(defects, sev_filter)
    if official_19_only_outputs():
        defects = filter_defects_to_official_19(defects)
    else:
        for i, d in enumerate(defects, 1):
            d["id"] = i
    return defects


def _det_model_dump(d: Detection) -> dict:
    if hasattr(d, "model_dump"):
        return d.model_dump()
    return d.dict()


def run_sonar_analysis_core(contents: bytes, filename: str, confidence_threshold: float) -> AnalysisResult:
    """Shared sonar pipeline for single-image and combined endpoints."""
    start = time.time()
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".tiff", ".bmp"):
        raise HTTPException(400, "Unsupported image format")

    image_id = f"SSS-{uuid.uuid4().hex[:8].upper()}"
    safe_name = _sanitize_upload_filename(filename or "upload.png")
    model_bytes, img_w, img_h = _maybe_downscale_image_bytes(contents)
    save_path = os.path.join(UPLOAD_DIR, f"{image_id}_{safe_name}")
    try:
        with open(save_path, "wb") as fout:
            fout.write(model_bytes)
    except OSError as e:
        raise HTTPException(400, f"Could not save upload (invalid path or disk full): {e}") from e

    det_model = get_detection_model()
    detections: List[Detection] = []

    if det_model:
        try:
            results = det_model.predict(save_path, conf=confidence_threshold, verbose=False)
        except Exception as e:
            raise HTTPException(
                422,
                f"Sonar model inference failed (try a smaller image or lower resolution). Detail: {e!s}",
            ) from e
        for r in results:
            boxes = getattr(r, "boxes", None)
            if boxes is None or len(boxes) == 0:
                continue
            for box in boxes:
                try:
                    cls_id = int(box.cls[0])
                    raw_conf = _finite_float(box.conf[0], 0.0)
                    conf = max(0.0, min(1.0, raw_conf))
                    xy = box.xyxyn[0].tolist()
                    x1, y1, x2, y2 = [_clamp01(xy[i]) for i in range(4)]
                except Exception:
                    continue
                if x2 <= x1 or y2 <= y1:
                    continue
                cn = DETECTION_CLASSES.get(cls_id, "other")
                area = round(_finite_float((x2 - x1) * (y2 - y1), 0.0), 4)
                sev = confidence_to_severity(cn, conf, area)
                desc = f"{cn} detected ({conf:.0%}) — severity: {sev}"
                detections.append(Detection(
                    id=f"DET-{uuid.uuid4().hex[:6].upper()}",
                    class_name=cn, confidence=round(conf, 3), severity=sev,
                    bbox=[round(x1, 3), round(y1, 3), round(x2, 3), round(y2, 3)],
                    area=area, description=desc,
                ))
    else:
        detections = run_mock_inference(safe_name)

    pt = (time.time() - start) * 1000
    sevs = [d.severity for d in detections]
    if "critical" in sevs:
        status = "critical"
    elif "high" in sevs:
        status = "warning"
    elif "medium" in sevs:
        status = "attention"
    else:
        status = "healthy"

    n = len(detections)
    if n == 0:
        summary = "No anomalies detected — seabed appears clear."
    else:
        summary = (
            f"Detected {n} object{'s' if n != 1 else ''} | "
            f"Critical: {sum(1 for s in sevs if s == 'critical')}, "
            f"High: {sum(1 for s in sevs if s == 'high')}, "
            f"Medium: {sum(1 for s in sevs if s == 'medium')}, "
            f"Low: {sum(1 for s in sevs if s == 'low')} | "
            f"Status: {status.upper()}"
        )

    result = AnalysisResult(
        image_id=image_id, filename=safe_name,
        timestamp=datetime.utcnow().isoformat(),
        processing_time_ms=round(pt, 1),
        image_width=img_w, image_height=img_h,
        total_detections=n,
        critical_count=sum(1 for d in detections if d.severity == "critical"),
        high_count=sum(1 for d in detections if d.severity == "high"),
        medium_count=sum(1 for d in detections if d.severity == "medium"),
        low_count=sum(1 for d in detections if d.severity == "low"),
        detections=detections, overall_status=status, summary=summary,
        model_info={
            "detector": "SubPipe YOLOv8m" if det_model else "Mock",
            "classifier": "Marine-PULSE" if get_classification_model() else "Mock",
            "confidence_threshold": _finite_float(confidence_threshold, 0.25),
            "version": "2.0.0",
        },
    )
    analysis_history.append({
        "image_id": image_id, "filename": safe_name,
        "total_detections": n, "status": status, "timestamp": result.timestamp,
    })
    return result


def _sonar_row(ar: AnalysisResult) -> dict:
    return {
        "filename": ar.filename,
        "total_detections": ar.total_detections,
        "critical_count": ar.critical_count,
        "detections": [_det_model_dump(d) for d in ar.detections],
    }


def _critical_anomaly_count(defects: list) -> int:
    return sum(1 for d in defects if str(d.get("severity", "")).lower() == "critical")


def _retry_if_only_pipeline_visual(det_img, iou_thr: float, mode: str, eff: float, dets: list) -> tuple[list, float]:
    """Align with main /api/detect: if YOLO only returns Pipeline (asset), retry lower conf for real defects."""
    if mode != "general" or not dets:
        return dets, eff
    _, defects = split_asset_and_defects(dets, mode)
    if defects:
        return dets, eff
    if eff > 0.05:
        eff = 0.05
        dets = run_detection(det_img, eff, iou_thr, mode)
    _, defects = split_asset_and_defects(dets, mode)
    if defects:
        return dets, eff
    if eff > 0.02:
        eff = 0.02
        dets = run_detection(det_img, eff, iou_thr, mode)
    return dets, eff


# ══════════════════════════════════════════════════════════════════════════
# PDF REPORT BUILDER
# ══════════════════════════════════════════════════════════════════════════

if REPORTLAB_AVAILABLE:
    NAVY       = colors.HexColor("#0B1A2E")
    PANEL      = colors.HexColor("#F0F4FA")
    WHITE      = colors.HexColor("#FFFFFF")
    TEXT_DARK  = colors.HexColor("#1E293B")
    TEXT_MID   = colors.HexColor("#475569")
    TEXT_LIGHT = colors.HexColor("#94A3B8")
    BRAND_CYAN = colors.HexColor("#0EA5E9")
    BORDER_CLR = colors.HexColor("#CBD5E1")

    SEV_COLOR = {
        "critical": colors.HexColor("#DC2626"),
        "high":     colors.HexColor("#EA580C"),
        "medium":   colors.HexColor("#2563EB"),
        "low":      colors.HexColor("#16A34A"),
    }
    SEV_BG = {
        "critical": colors.HexColor("#FEF2F2"),
        "high":     colors.HexColor("#FFF7ED"),
        "medium":   colors.HexColor("#EFF6FF"),
        "low":      colors.HexColor("#F0FDF4"),
    }

    PAGE_W, PAGE_H = A4
    PDF_MARGIN = 18 * mm

    def _pdf_styles():
        S = lambda name, **kw: ParagraphStyle(name, **kw)
        return {
            "h2": S("h2", fontName="Helvetica-Bold", fontSize=12, leading=16,
                    textColor=BRAND_CYAN, spaceBefore=14, spaceAfter=4),
            "h3": S("h3", fontName="Helvetica-Bold", fontSize=10, leading=13,
                    textColor=TEXT_DARK, spaceBefore=8, spaceAfter=3),
            "body": S("body", fontName="Helvetica", fontSize=9.5, leading=14,
                      textColor=TEXT_MID, spaceAfter=4),
            "body_sm": S("body_sm", fontName="Helvetica", fontSize=8.5, leading=12,
                         textColor=TEXT_MID, spaceAfter=2),
            "caption": S("caption", fontName="Helvetica-Oblique", fontSize=8,
                         leading=11, textColor=TEXT_LIGHT, spaceAfter=8, alignment=TA_CENTER),
            "tbl_hdr": S("tbl_hdr", fontName="Helvetica-Bold", fontSize=8,
                         leading=11, textColor=WHITE),
            "tbl_cell": S("tbl_cell", fontName="Helvetica", fontSize=8.5,
                          leading=12, textColor=TEXT_DARK),
            "tbl_cell_bold": S("tbl_cell_bold", fontName="Helvetica-Bold",
                               fontSize=8.5, leading=12, textColor=TEXT_DARK),
            "disclaimer": S("disclaimer", fontName="Helvetica", fontSize=7,
                            leading=10, textColor=TEXT_LIGHT, alignment=TA_CENTER, spaceBefore=6),
        }

    def _pil_to_rl(pil_img, max_w, max_h):
        """Raster for ReportLab — RGB, integer pt size; ImageReader handles wide sonar PNGs reliably."""
        rgb = pil_img.convert("RGB")
        buf = io.BytesIO()
        rgb.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        w, h = rgb.size
        tw, th = float(max_w), float(max_h)
        scale = min(tw / float(max(1, w)), th / float(max(1, h)), 1.0)
        rw = max(1, int(round(w * scale)))
        rh = max(1, int(round(h * scale)))
        try:
            return RLImage(ImageReader(buf), width=rw, height=rh)
        except Exception:
            buf.seek(0)
            return RLImage(buf, width=rw, height=rh)

    def _sev_rgb_tuple(sev):
        s = str(sev or "low").lower()
        cmap = {
            "critical": (220, 38, 38),
            "high": (234, 88, 12),
            "medium": (37, 99, 235),
            "low": (22, 163, 74),
        }
        return cmap.get(s, (100, 116, 139))

    def _combined_annotate_image(pil_rgb, dets, branch: str):
        """Draw bounding boxes and short labels (class + confidence) on a copy."""
        if not PIL_AVAILABLE or not dets:
            return pil_rgb
        try:
            from PIL import ImageDraw, ImageFont
        except ImportError:
            return pil_rgb
        img = pil_rgb.copy().convert("RGB")
        draw = ImageDraw.Draw(img)
        W, H = img.size
        lw = max(2, int(min(W, H) / 400))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        for i, d in enumerate(dets):
            bb = None
            if branch == "sonar":
                raw = d.get("bbox")
                if raw and len(raw) >= 4:
                    bb = [
                        float(raw[0]) * W,
                        float(raw[1]) * H,
                        float(raw[2]) * W,
                        float(raw[3]) * H,
                    ]
            else:
                raw = d.get("bbox_norm") or d.get("bbox")
                if raw and len(raw) >= 4:
                    bb = [
                        float(raw[0]) * W,
                        float(raw[1]) * H,
                        float(raw[2]) * W,
                        float(raw[3]) * H,
                    ]
            if not bb:
                continue
            x1, y1, x2, y2 = bb
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(W - 1, int(x2)), min(H - 1, int(y2))
            if x2 <= x1 or y2 <= y1:
                continue
            rgb = _sev_rgb_tuple(d.get("severity", "low"))
            draw.rectangle([x1, y1, x2, y2], outline=rgb, width=lw)
            cn = (d.get("class_name") or d.get("cls") or "?").replace("_", " ")
            conf = d.get("confidence", d.get("conf", 0))
            try:
                cf = float(conf)
                clabel = f"{cf * 100:.0f}%" if cf <= 1.0 else f"{cf:.0f}%"
            except (TypeError, ValueError):
                clabel = "—"
            label = f"{i + 1}: {cn[:24]} {clabel}"
            ty = max(0, y1 - 14)
            tx = x1
            try:
                bbox_txt = draw.textbbox((tx, ty), label, font=font)
                tw, th = bbox_txt[2] - bbox_txt[0], bbox_txt[3] - bbox_txt[1]
            except Exception:
                tw, th = len(label) * 6, 11
            draw.rectangle([tx, ty, tx + tw + 4, ty + th + 2], fill=(15, 23, 42))
            draw.text((tx + 2, ty + 1), label, fill=(226, 232, 240), font=font)
        return img

    def _conf_pct_cell(d):
        conf = d.get("confidence", d.get("conf", 0))
        try:
            cf = float(conf)
            return f"{cf * 100:.1f}%" if cf <= 1.0 else f"{cf:.1f}%"
        except (TypeError, ValueError):
            return "—"

    def _combined_sonar_det_table(ST, usable_w, dets):
        rows = [
            [
                Paragraph("#", ST["tbl_hdr"]),
                Paragraph("Class", ST["tbl_hdr"]),
                Paragraph("Severity", ST["tbl_hdr"]),
                Paragraph("Score", ST["tbl_hdr"]),
                Paragraph("Bbox (norm.)", ST["tbl_hdr"]),
                Paragraph("Area", ST["tbl_hdr"]),
                Paragraph("Note", ST["tbl_hdr"]),
            ]
        ]
        for di, d in enumerate(dets):
            sev = str(d.get("severity", "low")).lower()
            sc = SEV_COLOR.get(sev, TEXT_DARK)
            sb = SEV_BG.get(sev, WHITE)
            pill = Table(
                [[Paragraph(sev.upper(), ParagraphStyle(
                    f"cmb_sp_{di}", fontName="Helvetica-Bold", fontSize=7.5,
                    leading=10, textColor=sc, alignment=TA_CENTER))]],
                colWidths=[22 * mm],
            )
            pill.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), sb),
                ("BOX", (0, 0), (-1, -1), 0.5, sc),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            bbox = d.get("bbox", [0, 0, 0, 0])
            note = html.escape((d.get("description") or "")[:220])
            rows.append([
                Paragraph(str(di + 1), ST["tbl_cell"]),
                Paragraph(str(d.get("class_name", "")).replace("_", " "), ST["tbl_cell_bold"]),
                pill,
                Paragraph(_conf_pct_cell(d), ST["tbl_cell"]),
                Paragraph(
                    f"({bbox[0]:.3f},{bbox[1]:.3f})-({bbox[2]:.3f},{bbox[3]:.3f})",
                    ST["tbl_cell"],
                ),
                Paragraph(f"{float(d.get('area', 0)):.4f}", ST["tbl_cell"]),
                Paragraph(note or "—", ST["tbl_cell"]),
            ])
        cw = usable_w - (8 + 26 + 24 + 16 + 38) * mm
        dtbl = Table(rows, colWidths=[8 * mm, 26 * mm, 24 * mm, 16 * mm, 38 * mm, 22 * mm, cw], repeatRows=1)
        dtbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_CLR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return dtbl

    def _combined_visual_det_table(ST, usable_w, dets):
        rows = [
            [
                Paragraph("#", ST["tbl_hdr"]),
                Paragraph("Defect class", ST["tbl_hdr"]),
                Paragraph("Severity", ST["tbl_hdr"]),
                Paragraph("Score", ST["tbl_hdr"]),
                Paragraph("Bbox (norm.)", ST["tbl_hdr"]),
                Paragraph("Area (norm.)", ST["tbl_hdr"]),
            ]
        ]
        for di, d in enumerate(dets):
            sev_raw = str(d.get("severity", "low"))
            sev = sev_raw.lower()
            sc = SEV_COLOR.get(sev, TEXT_DARK)
            sb = SEV_BG.get(sev, WHITE)
            pill = Table(
                [[Paragraph(sev_raw.upper()[:12], ParagraphStyle(
                    f"cmb_vp_{di}", fontName="Helvetica-Bold", fontSize=7.5,
                    leading=10, textColor=sc, alignment=TA_CENTER))]],
                colWidths=[22 * mm],
            )
            pill.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), sb),
                ("BOX", (0, 0), (-1, -1), 0.5, sc),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]))
            bn = d.get("bbox_norm") or [0, 0, 0, 0]
            an = d.get("area_norm")
            try:
                astr = f"{float(an):.5f}" if an is not None else "—"
            except (TypeError, ValueError):
                astr = "—"
            rows.append([
                Paragraph(str(di + 1), ST["tbl_cell"]),
                Paragraph(str(d.get("class_name") or d.get("cls") or "").replace("_", " "), ST["tbl_cell_bold"]),
                pill,
                Paragraph(_conf_pct_cell(d), ST["tbl_cell"]),
                Paragraph(
                    f"({float(bn[0]):.3f},{float(bn[1]):.3f})-({float(bn[2]):.3f},{float(bn[3]):.3f})",
                    ST["tbl_cell"],
                ),
                Paragraph(astr, ST["tbl_cell"]),
            ])
        cw = usable_w - (8 + 32 + 24 + 16 + 40) * mm
        dtbl = Table(rows, colWidths=[8 * mm, 32 * mm, 24 * mm, 16 * mm, 40 * mm, cw], repeatRows=1)
        dtbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_CLR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return dtbl

    def _section(title, ST):
        return [
            Paragraph(title, ST["h2"]),
            HRFlowable(width="100%", thickness=1.5, color=BRAND_CYAN,
                       spaceAfter=8, spaceBefore=0),
        ]

    def _header_footer(canvas, doc, meta):
        canvas.saveState()
        W, H = PAGE_W, PAGE_H
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - 18 * mm, W, 18 * mm, fill=1, stroke=0)
        canvas.setFillColor(BRAND_CYAN)
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawString(PDF_MARGIN, H - 12 * mm, "NautiCAI")
        canvas.setFillColor(TEXT_LIGHT)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            PDF_MARGIN, H - 16 * mm,
            meta.get("header_tagline", "Side-Scan Sonar Inspection Report"),
        )
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(W - PDF_MARGIN, H - 10.5 * mm,
                               f"Report: {meta['report_id']}  |  {meta['date']}")
        canvas.drawRightString(W - PDF_MARGIN, H - 15 * mm,
                               f"Vessel: {meta['vessel']}  |  Inspector: {meta['inspector']}")
        canvas.setStrokeColor(BRAND_CYAN)
        canvas.setLineWidth(1.5)
        canvas.line(0, H - 18 * mm, W, H - 18 * mm)
        canvas.setStrokeColor(BORDER_CLR)
        canvas.setLineWidth(0.5)
        canvas.line(PDF_MARGIN, 10 * mm, W - PDF_MARGIN, 10 * mm)
        canvas.setFillColor(TEXT_LIGHT)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(PDF_MARGIN, 6 * mm,
                          "NautiCAI  |  Confidential  |  Singapore Maritime AI Systems Pte. Ltd.")
        canvas.drawRightString(W - PDF_MARGIN, 6 * mm, f"Page {doc.page}")
        canvas.restoreState()

    def build_sonar_pdf(
        results_data,
        image_files,
        vessel_name="",
        inspector="",
        inspection_mode="General Inspection",
        image_bytes_ordered=None,
    ):
        buf = io.BytesIO()
        usable_w = PAGE_W - 2 * PDF_MARGIN
        ts = datetime.utcnow().strftime("%Y-%m-%d  %H:%M:%S UTC")
        report_id = f"SONAR-{hashlib.sha256((ts + vessel_name).encode()).hexdigest()[:8].upper()}"
        meta = {"report_id": report_id, "vessel": vessel_name or "N/A",
                "inspector": inspector or "NautiCAI AutoScan v1.0", "date": ts}

        doc = SimpleDocTemplate(
            buf, pagesize=A4, leftMargin=PDF_MARGIN, rightMargin=PDF_MARGIN,
            topMargin=24 * mm, bottomMargin=16 * mm,
            title=f"NautiCAI Sonar Report - {report_id}",
            author="NautiCAI - Singapore Maritime AI Systems",
        )
        ST = _pdf_styles()
        story = []
        results_data = [x if isinstance(x, dict) else {} for x in results_data]

        # ── COVER ────────────────────────────────────────────────────
        cover = Table(
            [[Paragraph("NautiCAI", ParagraphStyle("ct", fontName="Helvetica-Bold",
                        fontSize=32, leading=38, textColor=WHITE))],
             [Paragraph("SIDE-SCAN SONAR<br/>INSPECTION REPORT",
                        ParagraphStyle("cs", fontName="Helvetica-Bold",
                        fontSize=14, leading=18, textColor=BRAND_CYAN))],
             [Spacer(1, 4)],
             [Paragraph(f"Report <b>{report_id}</b>&nbsp;&nbsp;|&nbsp;&nbsp;"
                        f"Vessel <b>{vessel_name or 'N/A'}</b>&nbsp;&nbsp;|&nbsp;&nbsp;"
                        f"Inspector <b>{inspector or 'AutoScan'}</b>",
                        ParagraphStyle("cm", fontName="Helvetica", fontSize=9.5,
                        leading=14, textColor=TEXT_LIGHT))],
             [Paragraph(f"{ts}&nbsp;&nbsp;|&nbsp;&nbsp;Mode: {inspection_mode}"
                        f"&nbsp;&nbsp;|&nbsp;&nbsp;Images: {len(results_data)}",
                        ParagraphStyle("cd", fontName="Helvetica", fontSize=9,
                        leading=13, textColor=colors.HexColor("#64748B")))]],
            colWidths=[usable_w],
        )
        cover.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (0, 0), 20),
            ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
            ("LEFTPADDING", (0, 0), (-1, -1), 20),
            ("RIGHTPADDING", (0, 0), (-1, -1), 20),
        ]))
        story.append(cover)
        story.append(Spacer(1, 14))

        # ── EXECUTIVE SUMMARY ────────────────────────────────────────
        story += _section("Executive Summary", ST)
        total_dets = sum(r.get("total_detections", 0) for r in results_data)
        total_crit = sum(r.get("critical_count", 0) for r in results_data)
        total_high = sum(r.get("high_count", 0) for r in results_data)
        total_med  = sum(r.get("medium_count", 0) for r in results_data)
        total_low  = sum(r.get("low_count", 0) for r in results_data)

        def _mcell(label, value, col=TEXT_DARK):
            return [
                Paragraph(str(value), ParagraphStyle(
                    f"mv_{label}", fontName="Helvetica-Bold", fontSize=22,
                    leading=26, textColor=col, alignment=TA_CENTER)),
                Paragraph(label.upper(), ParagraphStyle(
                    f"ml_{label}", fontName="Helvetica-Bold", fontSize=7,
                    leading=10, textColor=TEXT_LIGHT, alignment=TA_CENTER)),
            ]

        cw = usable_w / 5
        metrics = Table(
            [[_mcell("Images", len(results_data), BRAND_CYAN),
              _mcell("Total", total_dets, TEXT_DARK),
              _mcell("Critical", total_crit, SEV_COLOR["critical"] if total_crit else TEXT_DARK),
              _mcell("High", total_high, SEV_COLOR["high"] if total_high else TEXT_DARK),
              _mcell("Medium", total_med, SEV_COLOR["medium"] if total_med else TEXT_DARK)]],
            colWidths=[cw] * 5,
        )
        metrics.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PANEL),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
            ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER_CLR),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(metrics)
        story.append(Spacer(1, 8))

        # Status banner
        if total_crit > 0:
            msg = f"<b>CRITICAL ALERT:</b> {total_crit} critical finding(s). Immediate inspection recommended."
            mc, mb = SEV_COLOR["critical"], SEV_BG["critical"]
        elif total_high > 0:
            msg = f"<b>Action Required:</b> {total_high} high-severity finding(s). Schedule maintenance within 30 days."
            mc, mb = SEV_COLOR["high"], SEV_BG["high"]
        elif total_dets > 0:
            msg = f"<b>Monitor:</b> {total_dets} detection(s) recorded. Continue standard inspection cycle."
            mc, mb = SEV_COLOR["medium"], SEV_BG["medium"]
        else:
            msg = "<b>All Clear:</b> No anomalies detected across all scanned images."
            mc, mb = SEV_COLOR["low"], SEV_BG["low"]

        stbl = Table([[Paragraph(msg, ParagraphStyle("st", fontName="Helvetica",
                       fontSize=9.5, leading=14, textColor=TEXT_DARK))]], colWidths=[usable_w])
        stbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), mb), ("BOX", (0, 0), (-1, -1), 1.2, mc),
            ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(stbl)
        story.append(Spacer(1, 12))

        # ── PER-IMAGE PAGES ──────────────────────────────────────────
        for idx, r in enumerate(results_data):
            story.append(PageBreak())
            fname = r.get("filename", f"Image {idx+1}")
            st = r.get("overall_status", "healthy")
            story += _section(f"Image {idx+1} — {fname}", ST)

            im_data = [
                ["Image ID", r.get("image_id", "N/A"), "Status", st.upper()],
                ["Resolution", f"{r.get('image_width', 0)} x {r.get('image_height', 0)} px",
                 "Processing", f"{r.get('processing_time_ms', 0):.0f} ms"],
                ["Detections", str(r.get("total_detections", 0)),
                 "Detector", r.get("model_info", {}).get("detector", "N/A")],
            ]
            imt = Table(im_data, colWidths=[30*mm, 50*mm, 30*mm, 50*mm])
            imt.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (0, -1), TEXT_LIGHT),
                ("TEXTCOLOR", (2, 0), (2, -1), TEXT_LIGHT),
                ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
                ("TEXTCOLOR", (3, 0), (3, -1), TEXT_DARK),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER_CLR),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(imt)
            story.append(Spacer(1, 10))

            # Sonar image — prefer upload order (same as analyze loop), then filename keys
            img_key = r.get("filename") or ""
            img_bytes = None
            if image_bytes_ordered is not None and idx < len(image_bytes_ordered):
                cand = image_bytes_ordered[idx]
                if cand:
                    img_bytes = cand
            if img_bytes is None and img_key:
                if img_key in image_files:
                    img_bytes = image_files[img_key]
                if img_bytes is None:
                    sk = _sanitize_upload_filename(img_key)
                    if sk and sk in image_files:
                        img_bytes = image_files[sk]
                if img_bytes is None:
                    for k, v in image_files.items():
                        if not isinstance(k, str):
                            continue
                        if _sanitize_upload_filename(k) == img_key or k == img_key:
                            img_bytes = v
                            break

            if img_bytes is not None and PIL_AVAILABLE:
                try:
                    pil_img = PILImage.open(io.BytesIO(img_bytes))
                    pil_img.load()
                    story.append(Paragraph("Sonar Scan Image", ST["h3"]))
                    img_rl = _pil_to_rl(pil_img, max_w=usable_w, max_h=65 * mm)
                    img_rl.hAlign = "CENTER"
                    ifr = Table([[img_rl]], colWidths=[usable_w])
                    ifr.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]))
                    story.append(ifr)
                    story.append(Paragraph(f"Fig {idx+1} — Side-scan sonar image.", ST["caption"]))
                except Exception as ex:
                    story.append(Paragraph(
                        f"Sonar frame bytes could not be embedded ({ex!s}).",
                        ST["body_sm"],
                    ))
            elif img_bytes is not None and not PIL_AVAILABLE:
                story.append(Paragraph(
                    "Image bytes were uploaded but Pillow is not available on the server to rasterize them.",
                    ST["body_sm"],
                ))
            elif img_bytes is None:
                story.append(Paragraph(
                    "No image bytes for this page (upload count/order mismatch vs results, or files omitted). "
                    "Download PDF again immediately after analysis without clearing uploads.",
                    ST["body_sm"],
                ))

            # Detection table
            dets = r.get("detections", [])
            if dets:
                story.append(Paragraph("Detection Log", ST["h3"]))
                hdr = [Paragraph("#", ST["tbl_hdr"]), Paragraph("Class", ST["tbl_hdr"]),
                       Paragraph("Severity", ST["tbl_hdr"]), Paragraph("Conf.", ST["tbl_hdr"]),
                       Paragraph("Bbox (norm.)", ST["tbl_hdr"]), Paragraph("Area", ST["tbl_hdr"])]
                rows = [hdr]
                for di, d in enumerate(dets):
                    sev = d.get("severity", "low")
                    sc = SEV_COLOR.get(sev, TEXT_DARK)
                    sb = SEV_BG.get(sev, WHITE)
                    pill = Table(
                        [[Paragraph(sev.upper(), ParagraphStyle(
                            f"sp_{sev}_{idx}_{di}", fontName="Helvetica-Bold", fontSize=7.5,
                            leading=10, textColor=sc, alignment=TA_CENTER))]],
                        colWidths=[50])
                    pill.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), sb),
                        ("BOX", (0, 0), (-1, -1), 0.5, sc),
                        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ]))
                    bbox = d.get("bbox", [0, 0, 0, 0])
                    rows.append([
                        Paragraph(str(di+1), ST["tbl_cell"]),
                        Paragraph(d.get("class_name", "").replace("_", " "), ST["tbl_cell_bold"]),
                        pill,
                        Paragraph(f"{d.get('confidence', 0)*100:.1f}%", ST["tbl_cell"]),
                        Paragraph(f"({bbox[0]:.2f},{bbox[1]:.2f})-({bbox[2]:.2f},{bbox[3]:.2f})", ST["tbl_cell"]),
                        Paragraph(f"{d.get('area', 0):.4f}", ST["tbl_cell"]),
                    ])
                bcw = usable_w - (10+30+22+18+22)*mm
                dtbl = Table(rows, colWidths=[10*mm, 30*mm, 22*mm, 18*mm, bcw, 22*mm], repeatRows=1)
                dtbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                    ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                    ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
                    ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_CLR),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]))
                story.append(dtbl)
            else:
                story.append(Paragraph("No detections — seabed appears clear.", ST["body"]))
            story.append(Spacer(1, 8))

        # ── RECOMMENDATIONS ──────────────────────────────────────────
        story.append(PageBreak())
        story += _section("Recommendations", ST)
        recs = {
            "critical": ["Immediate ROV re-survey of flagged pipeline segments.",
                         "Deploy repair/intervention team within 7 days.",
                         "Notify asset integrity management team."],
            "high": ["Schedule detailed inspection within 30 days.",
                     "Monitor with bi-weekly sonar survey.",
                     "Cross-reference with historical survey data."],
            "medium": ["Document in pipeline maintenance log.",
                       "Schedule review at next planned survey.",
                       "Update digital twin baseline model."],
            "low": ["Monitor during quarterly inspection cycle.",
                    "No immediate action required."],
        }
        has_recs = False
        for sl in ["critical", "high", "medium", "low"]:
            cnt = {"critical": total_crit, "high": total_high,
                   "medium": total_med, "low": total_low}.get(sl, 0)
            if cnt == 0:
                continue
            has_recs = True
            sc = SEV_COLOR.get(sl, TEXT_DARK)
            story.append(Paragraph(
                f"<font color='{sc.hexval()}'><b>{sl.upper()}</b></font>"
                f"&nbsp;&nbsp;({cnt} finding{'s' if cnt != 1 else ''})", ST["h3"]))
            for item in recs.get(sl, []):
                story.append(Paragraph(f"&nbsp;&nbsp;\u2022&nbsp;&nbsp;{item}", ST["body"]))
            story.append(Spacer(1, 4))
        if not has_recs:
            story.append(Paragraph("No actionable recommendations — all clear.", ST["body"]))

        # ── DISCLAIMER ───────────────────────────────────────────────
        story.append(Spacer(1, 16))
        story.append(HRFlowable(width="100%", thickness=0.8, color=BORDER_CLR,
                                spaceAfter=6, spaceBefore=2))
        story.append(Paragraph(
            "All findings must be verified by a certified marine surveyor before "
            "operational decisions are made. This report is generated by an AI system "
            "and is advisory in nature.<br/>"
            "<b>NautiCAI  |  Singapore Maritime AI Systems Pte. Ltd.  |  Est. 2024</b>",
            ST["disclaimer"]))

        doc.build(story,
                  onFirstPage=lambda c, d: _header_footer(c, d, meta),
                  onLaterPages=lambda c, d: _header_footer(c, d, meta))
        buf.seek(0)
        return buf.getvalue()

    def build_combined_dual_pdf(
        payload: dict,
        vessel_name: str = "",
        inspector: str = "",
        image_files: Optional[dict] = None,
    ) -> bytes:
        """PDF from `/analyze-combined-v2` JSON; optional `image_files` maps filename → raw bytes."""
        buf = io.BytesIO()
        usable_w = PAGE_W - 2 * PDF_MARGIN
        ts = datetime.utcnow().strftime("%Y-%m-%d  %H:%M:%S UTC")
        report_id = f"CMB-{hashlib.sha256((ts + (vessel_name or '')).encode()).hexdigest()[:8].upper()}"
        meta = {
            "report_id": report_id,
            "vessel": vessel_name or "N/A",
            "inspector": inspector or "NautiCAI AutoScan v1.0",
            "date": ts,
            "header_tagline": "Combined Sonar + Visual Inspection Report",
        }

        doc = SimpleDocTemplate(
            buf, pagesize=A4, leftMargin=PDF_MARGIN, rightMargin=PDF_MARGIN,
            topMargin=22 * mm, bottomMargin=16 * mm,
            title=f"NautiCAI Combined Report — {report_id}",
        )
        ST = _pdf_styles()
        story = []
        imgs = image_files or {}

        cover = Table(
            [[Paragraph("NautiCAI", ParagraphStyle("ct", fontName="Helvetica-Bold",
                        fontSize=28, leading=34, textColor=WHITE))],
             [Paragraph("COMBINED SONAR + VISUAL<br/>INSPECTION SUMMARY",
                        ParagraphStyle("cs", fontName="Helvetica-Bold",
                        fontSize=13, leading=17, textColor=BRAND_CYAN))],
             [Spacer(1, 6)],
             [Paragraph(
                f"Report <b>{report_id}</b><br/>Vessel <b>{vessel_name or 'N/A'}</b> · "
                f"Inspector <b>{inspector or 'AutoScan'}</b><br/>{ts}",
                ParagraphStyle("cm", fontName="Helvetica", fontSize=9.5, leading=14, textColor=TEXT_LIGHT))]],
            colWidths=[usable_w],
        )
        cover.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (0, 0), 18),
            ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
            ("LEFTPADDING", (0, 0), (-1, -1), 18),
            ("RIGHTPADDING", (0, 0), (-1, -1), 18),
        ]))
        story.append(cover)
        story.append(Spacer(1, 14))

        cs = payload.get("combined_summary") or {}
        sonar_block = payload.get("sonar") or {}
        anomaly_block = payload.get("anomaly") or {}
        sonar_results = sonar_block.get("results") or []
        anomaly_results = anomaly_block.get("results") or []

        story += _section("Executive Summary", ST)
        summary_rows = [
            ["Total detections", str(cs.get("total_detections", 0))],
            ["Sonar branch", str(sonar_block.get("total_detections", 0))],
            ["Visual / anomaly branch", str(anomaly_block.get("total_detections", 0))],
            ["Critical (combined)", str(cs.get("total_critical", 0))],
        ]
        stbl = Table(summary_rows, colWidths=[72 * mm, usable_w - 72 * mm])
        stbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 0), (0, -1), TEXT_LIGHT),
            ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER_CLR),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(stbl)
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "<b>Figures in this report:</b> annotated thumbnails (class + model confidence) and "
            "per-detection tables. Re-export after analysis with the same files selected so images "
            "can be embedded.",
            ST["body_sm"],
        ))
        story.append(Spacer(1, 14))

        # ── SONAR detail pages ───────────────────────────────────────
        story.append(PageBreak())
        story += _section("Sonar branch — images & detections", ST)
        if not sonar_results:
            story.append(Paragraph("No sonar images in this run.", ST["body_sm"]))
        for idx, row in enumerate(sonar_results):
            if idx > 0:
                story.append(PageBreak())
            fn = row.get("filename", f"Image {idx + 1}")
            story.append(Paragraph(f"<b>{fn}</b>", ST["h3"]))
            meta_tbl = Table(
                [
                    ["Detections", str(row.get("total_detections", 0)), "Critical", str(row.get("critical_count", 0))],
                ],
                colWidths=[28 * mm, 32 * mm, 28 * mm, usable_w - 88 * mm],
            )
            meta_tbl.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (0, -1), TEXT_LIGHT),
                ("TEXTCOLOR", (2, 0), (2, -1), TEXT_LIGHT),
                ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
                ("TEXTCOLOR", (3, 0), (3, -1), TEXT_DARK),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(meta_tbl)
            story.append(Spacer(1, 8))

            dets = row.get("detections") or []
            pil_used = None
            if fn in imgs and PIL_AVAILABLE:
                try:
                    pil_used = PILImage.open(io.BytesIO(imgs[fn])).convert("RGB")
                    ann = _combined_annotate_image(pil_used, dets, "sonar")
                    story.append(Paragraph("Annotated sonar frame", ST["h3"]))
                    img_rl = _pil_to_rl(ann, max_w=usable_w, max_h=72 * mm)
                    img_rl.hAlign = "CENTER"
                    ifr = Table([[img_rl]], colWidths=[usable_w])
                    ifr.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]))
                    story.append(ifr)
                    story.append(Paragraph(f"Fig S{idx + 1} — {fn}", ST["caption"]))
                except Exception:
                    story.append(Paragraph(
                        "(Could not decode sonar image bytes for this filename.)",
                        ST["body_sm"],
                    ))
            elif not imgs:
                story.append(Paragraph(
                    "No image bytes supplied for PDF export — detection table only.",
                    ST["body_sm"],
                ))

            if dets:
                story.append(Spacer(1, 6))
                story.append(Paragraph("Detection log", ST["h3"]))
                story.append(_combined_sonar_det_table(ST, usable_w, dets))
            else:
                story.append(Paragraph("No detections for this frame.", ST["body_sm"]))

        # ── VISUAL detail pages ──────────────────────────────────────
        story.append(PageBreak())
        story += _section("Visual / ROV branch — images & detections", ST)
        if not anomaly_results:
            story.append(Paragraph("No visual inspection images in this run.", ST["body_sm"]))
        for idx, row in enumerate(anomaly_results):
            if idx > 0:
                story.append(PageBreak())
            fn = row.get("filename", f"Visual {idx + 1}")
            story.append(Paragraph(f"<b>{fn}</b>", ST["h3"]))
            meta_tbl = Table(
                [
                    [
                        "Detections",
                        str(row.get("total_detections", 0)),
                        "Grade / risk",
                        f"{row.get('grade', '—')} · {row.get('risk_score', '—')}%",
                    ],
                    [
                        "Resolution",
                        f"{row.get('image_width', '?')} × {row.get('image_height', '?')} px",
                        "Branch",
                        "NautiCAI visual (ROV still)",
                    ],
                ],
                colWidths=[28 * mm, 28 * mm, 28 * mm, usable_w - 84 * mm],
            )
            meta_tbl.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, 0), "Helvetica-Bold"),
                ("FONTNAME", (2, 1), (2, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 0), (0, -1), TEXT_LIGHT),
                ("TEXTCOLOR", (2, 0), (2, 1), TEXT_LIGHT),
                ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
                ("TEXTCOLOR", (3, 0), (3, -1), TEXT_DARK),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(meta_tbl)
            story.append(Spacer(1, 8))

            dets = row.get("detections") or []
            if fn in imgs and PIL_AVAILABLE:
                try:
                    pil_used = PILImage.open(io.BytesIO(imgs[fn])).convert("RGB")
                    ann = _combined_annotate_image(pil_used, dets, "visual")
                    story.append(Paragraph("Annotated ROV frame", ST["h3"]))
                    img_rl = _pil_to_rl(ann, max_w=usable_w, max_h=72 * mm)
                    img_rl.hAlign = "CENTER"
                    ifr = Table([[img_rl]], colWidths=[usable_w])
                    ifr.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_CLR),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]))
                    story.append(ifr)
                    story.append(Paragraph(f"Fig V{idx + 1} — {fn}", ST["caption"]))
                except Exception:
                    story.append(Paragraph(
                        "(Could not decode visual image bytes for this filename.)",
                        ST["body_sm"],
                    ))
            elif not imgs:
                story.append(Paragraph(
                    "No image bytes supplied for PDF export — detection table only.",
                    ST["body_sm"],
                ))

            if dets:
                story.append(Spacer(1, 6))
                story.append(Paragraph("Detection log", ST["h3"]))
                story.append(_combined_visual_det_table(ST, usable_w, dets))
            else:
                story.append(Paragraph("No defects logged for this frame.", ST["body_sm"]))

        story.append(Spacer(1, 14))
        story.append(Paragraph(
            "Sonar detections use the SubPipe-style tracker; visual defects use the active NautiCAI "
            "inspection head. Confidence scores are model outputs — verify critical findings in situ.",
            ST["body_sm"],
        ))

        doc.build(story,
                  onFirstPage=lambda c, d: _header_footer(c, d, meta),
                  onLaterPages=lambda c, d: _header_footer(c, d, meta))
        buf.seek(0)
        return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@router.get("/health")
async def sonar_health():
    return {
        "status": "online",
        "detection_model":      "loaded" if get_detection_model() else "mock",
        "classification_model": "loaded" if get_classification_model() else "mock",
    }


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_sonar_image(
    file: UploadFile = File(...),
    confidence_threshold: float = 0.25,
):
    try:
        contents = await file.read()
        return run_sonar_analysis_core(contents, file.filename or "upload.png", confidence_threshold)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sonar analyze failed: {e!s}") from e


@router.post("/analyze/batch")
async def analyze_batch(files: List[UploadFile] = File(...), confidence_threshold: float = 0.25):
    results = []
    for file in files:
        result = await analyze_sonar_image(file, confidence_threshold)
        results.append(result)
    return {
        "total_images": len(results),
        "total_detections": sum(r.total_detections for r in results),
        "total_critical": sum(r.critical_count for r in results),
        "results": results,
    }


@router.post("/analyze-combined-v2")
async def analyze_combined_v2(
    sonar_files: Optional[List[UploadFile]] = File(None),
    anomaly_files: Optional[List[UploadFile]] = File(None),
    confidence_threshold: float = Form(0.25),
    conf_thr: float = Form(0.25),
    iou_thr: float = Form(0.45),
    mode: str = Form("general"),
    sev_filter: str = Form("All Detections"),
):
    """Dual upload: side-scan sonar stack + ROV inspection images in one request."""
    sf = sonar_files or []
    af = anomaly_files or []
    if not sf and not af:
        raise HTTPException(400, "Upload at least one sonar image and/or one inspection image")

    sonar_rows = []
    for f in sf:
        contents = await f.read()
        ar = run_sonar_analysis_core(contents, f.filename or "sonar.png", confidence_threshold)
        sonar_rows.append(_sonar_row(ar))

    anomaly_rows = []
    for f in af:
        raw_name = f.filename or "image.jpg"
        contents = await f.read()
        if not PIL_AVAILABLE:
            raise HTTPException(500, "Pillow is required for visual inspection branch")
        try:
            pil_img = PILImage.open(io.BytesIO(contents)).convert("RGB")
        except Exception:
            raise HTTPException(400, f"Could not decode inspection image: {raw_name}")

        enhanced = full_enhance(
            pil_img,
            use_clahe=True,
            use_green=True,
            turb_in=0.0,
            corr_turb=True,
            use_edge=False,
            clahe_clip=3.0,
            marine_snow=False,
        )
        eff = conf_thr
        dets = run_detection(enhanced, eff, iou_thr, mode)
        if not dets and conf_thr > 0.05:
            eff = 0.05
            dets = run_detection(enhanced, eff, iou_thr, mode)
        if not dets and conf_thr > 0.02:
            eff = 0.02
            dets = run_detection(enhanced, eff, iou_thr, mode)

        dets, eff = _retry_if_only_pipeline_visual(enhanced, iou_thr, mode, eff, dets)

        defects = _finalize_anomaly_detections(dets, mode, sev_filter)
        risk = compute_risk(defects)
        grade = score_to_grade(risk)
        det_out = []
        for d in defects:
            x1 = float(d.get("x1", 0))
            y1 = float(d.get("y1", 0))
            x2 = float(d.get("x2", 0))
            y2 = float(d.get("y2", 0))
            bw = max(1e-6, ew)
            bh = max(1e-6, eh)
            det_out.append({
                "class_name": d.get("cls"),
                "cls": d.get("cls"),
                "severity": d.get("severity"),
                "confidence": d.get("conf"),
                "conf": d.get("conf"),
                "bbox_norm": [
                    max(0.0, min(1.0, x1 / bw)),
                    max(0.0, min(1.0, y1 / bh)),
                    max(0.0, min(1.0, x2 / bw)),
                    max(0.0, min(1.0, y2 / bh)),
                ],
                "area_norm": max(0.0, (x2 - x1) * (y2 - y1)) / (bw * bh),
            })
        anomaly_rows.append({
            "filename": raw_name,
            "image_width": pil_img.width,
            "image_height": pil_img.height,
            "total_detections": len(defects),
            "grade": grade,
            "risk_score": risk,
            "detections": det_out,
        })

    st = sum(r["total_detections"] for r in sonar_rows)
    at = sum(r["total_detections"] for r in anomaly_rows)
    tc = (
        sum(r["critical_count"] for r in sonar_rows)
        + sum(_critical_anomaly_count(r["detections"]) for r in anomaly_rows)
    )

    return {
        "combined_summary": {
            "total_detections": st + at,
            "total_critical": tc,
        },
        "sonar": {
            "total_detections": st,
            "results": sonar_rows,
        },
        "anomaly": {
            "total_detections": at,
            "results": anomaly_rows,
        },
    }


@router.post("/report/combined-pdf")
async def generate_combined_pdf_from_json(
    results_json: str = Form(...),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
    sonar_files: Optional[List[UploadFile]] = File(None),
    anomaly_files: Optional[List[UploadFile]] = File(None),
):
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(500, "reportlab is not installed on this server")
    try:
        payload = json.loads(results_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid results JSON")

    image_files: dict = {}
    for f in sonar_files or []:
        raw = await f.read()
        name = f.filename or ""
        if name:
            image_files[name] = raw
    for f in anomaly_files or []:
        raw = await f.read()
        name = f.filename or ""
        if name:
            image_files[name] = raw

    pdf_bytes = build_combined_dual_pdf(
        payload,
        vessel_name=vessel_name,
        inspector=inspector,
        image_files=image_files if image_files else None,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=NautiCAI_Combined_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            )
        },
    )


@router.post("/report/pdf")
async def generate_sonar_pdf(
    files: List[UploadFile] = File(...),
    results_json: str = Form(...),
    vessel_name: str = Form(""),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
    inspection_mode: str = Form("General Inspection"),
):
    """Generate a professional PDF report for sonar analysis results."""
    if not REPORTLAB_AVAILABLE:
        raise HTTPException(500, "reportlab is not installed on this server")

    try:
        results_data = json.loads(results_json)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid results JSON")
    if isinstance(results_data, str):
        try:
            results_data = json.loads(results_data)
        except json.JSONDecodeError:
            raise HTTPException(400, "results_json was double-encoded or invalid")
    if isinstance(results_data, dict) and "results" in results_data:
        results_data = results_data["results"]
    if not isinstance(results_data, list):
        raise HTTPException(
            400,
            "results_json must be a JSON array of sonar analysis objects (or an object with key 'results').",
        )

    image_files = {}
    ordered_bytes: List[bytes] = []
    for f in files:
        contents = await f.read()
        ordered_bytes.append(contents)
        raw_name = f.filename or "upload.png"
        image_files[raw_name] = contents
        image_files[_sanitize_upload_filename(raw_name)] = contents

    pdf_bytes = build_sonar_pdf(
        results_data=results_data,
        image_files=image_files,
        vessel_name=vessel_name,
        inspector=inspector,
        inspection_mode=inspection_mode,
        image_bytes_ordered=ordered_bytes,
    )
    return Response(
        content=pdf_bytes, media_type="application/pdf",
        headers={"Content-Disposition":
                 f"attachment; filename=NautiCAI_Sonar_Report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"},
    )


@router.get("/stats")
async def get_stats():
    return {"total_analyses": len(analysis_history),
            "total_anomalies": sum(h["total_detections"] for h in analysis_history)}


@router.get("/history")
async def get_history(limit: int = 20):
    return {"total": len(analysis_history), "results": analysis_history[-limit:][::-1]}


@router.get("/classes")
async def get_classes():
    return {"detection_classes": DETECTION_CLASSES, "severity_levels": SEVERITY_MAP}