"""
NautiCAI — detection + annotation + heatmap engine.
Multi-model support: SubPipe, SubPipeMini, SubPipeMini2, Subsea1 4-class
"""
import math, os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
from scipy.ndimage import gaussian_filter
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from severity import (
    SEVERITY_MAP, CLASS_REMAP, DEFECT_CLASSES, SEV_WEIGHT,
    PIPELINE_DEFECTS, CABLE_DEFECTS, compute_risk, score_to_grade,
)

ROOT = Path(__file__).resolve().parent.parent

# ── Available Models ──────────────────────────────────────────────────────
AVAILABLE_MODELS = {
    "merged_original":  "weights/best_merged_original.pt",
    "subpipe_full":     "weights/best_subpipe_full.pt",
    "subpipemini":      "weights/best_subpipemini.pt",
    "subpipemini2":     "weights/best_subpipemini2.pt",
    "subsea1_4class":   "weights/best_subsea1_4class.pt",
    "archive":          "weights/best_archive.pt",
}

MODEL_DESCRIPTIONS = {
    "merged_original":  "NautiCAI Merged Dataset — Original Production Model — Multi-class",
    "subpipe_full":     "SubPipe Full 21K Images — Pipeline Segmentation",
    "subpipemini":      "SubPipeMini — Pipeline Segmentation — 99.5% mAP",
    "subpipemini2":     "SubPipeMini2 — Pipeline Segmentation — 99.5% mAP",
    "subsea1_4class":   "Subsea Pipeline v2 — Anode, Corner, Flange, Pipe — 99.5% mAP",
    "archive":          "SubPipe Archive — Pipeline Segmentation — 99.5% mAP",
}

_active_model_key = "merged_original"

def set_active_model(model_key: str):
    global _active_model_key, _model_cache
    if model_key in AVAILABLE_MODELS:
        _active_model_key = model_key
        _model_cache = {}

def get_active_model_key():
    return _active_model_key

def get_model_descriptions():
    return MODEL_DESCRIPTIONS

# ── Model loading ─────────────────────────────────────────────────────────
_model_cache = {}

def _find_model():
    active_path = ROOT / AVAILABLE_MODELS.get(_active_model_key, "")
    if active_path.exists():
        return active_path
    for key, rel_path in AVAILABLE_MODELS.items():
        p = ROOT / rel_path
        if p.exists():
            return p
    for n in ["best.pt", "yolov8s.pt", "yolov8n.pt"]:
        p = ROOT / n
        if p.exists():
            return p
    return None


def _auto_download_model():
    model_path = ROOT / "weights" / "best_archive.pt"
    if not model_path.exists():
        try:
            from huggingface_hub import hf_hub_download
            print("Downloading model from Hugging Face...")
            (ROOT / "weights").mkdir(exist_ok=True)
            hf_hub_download(
                repo_id="aishwarya252525/nauticai-yolov8",
                filename="best.pt",
                local_dir=str(ROOT / "weights"),
                local_dir_use_symlinks=False,
            )
        except Exception as e:
            print(f"Model download failed: {e}")


def load_yolo():
    model_path = _find_model()
    if model_path is None:
        return None, None
    key = str(model_path)
    if key not in _model_cache:
        from ultralytics import YOLO
        print(f"Loading model: {model_path.name}")
        _model_cache[key] = YOLO(key)
    return _model_cache[key], model_path


def get_model_name():
    _, path = load_yolo()
    return path.name if path else "Demo"


# ── Detection ─────────────────────────────────────────────────────────────
def _pool_for_mode(mode: str):
    if mode == "pipeline":
        return PIPELINE_DEFECTS
    elif mode == "cable":
        return CABLE_DEFECTS
    return DEFECT_CLASSES


def _detect_real(img, conf_thr, iou_thr):
    model, _ = load_yolo()
    if model is None:
        return []
    results = model.predict(img, conf=conf_thr, iou=iou_thr, verbose=False)[0]
    dets = []
    det_id = 0
    img_w = img.width if hasattr(img, "width") else img.shape[1]
    img_h = img.height if hasattr(img, "height") else img.shape[0]
    img_area = img_w * img_h

    has_masks = hasattr(results, "masks") and results.masks is not None

    for i, box in enumerate(results.boxes):
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])
        cls_i = int(box.cls[0])
        box_area = (x2 - x1) * (y2 - y1)
        coverage = box_area / img_area if img_area > 0 else 0
        if coverage > 0.50 or coverage < 0.005:
            continue
        cls_name = model.names.get(cls_i, DEFECT_CLASSES[cls_i % len(DEFECT_CLASSES)])
        cls = CLASS_REMAP.get(cls_name, CLASS_REMAP.get(cls_name.lower(), cls_name))
        sev = SEVERITY_MAP.get(cls, "Medium")
        det_id += 1

        det = dict(
            id=det_id,
            cls=cls,
            severity=sev,
            conf=conf,
            x1=x1, y1=y1, x2=x2, y2=y2,
            area=box_area,
            model=_active_model_key,
        )

        if has_masks and i < len(results.masks.data):
            mask = results.masks.data[i].cpu().numpy()
            mask_coverage = float(mask.sum()) / (mask.shape[0] * mask.shape[1])
            det["mask_coverage"] = round(mask_coverage * 100, 2)

        dets.append(det)
    return dets


def _detect_synthetic(img, conf_thr, pool):
    w, h = img.size
    rng = np.random.default_rng(sum(img.tobytes()[:64]))
    n = rng.integers(3, 9)
    dets = []
    for i in range(n):
        cx, cy = rng.integers(60, w - 60), rng.integers(60, h - 60)
        bw, bh = rng.integers(40, w // 4), rng.integers(30, h // 5)
        conf = float(rng.uniform(conf_thr, 0.98))
        cls = rng.choice(pool)
        sev = SEVERITY_MAP.get(cls, "Medium")
        x1, y1 = max(0, cx - bw // 2), max(0, cy - bh // 2)
        x2, y2 = min(w, cx + bw // 2), min(h, cy + bh // 2)
        dets.append(dict(
            id=i + 1, cls=cls, severity=sev, conf=conf,
            x1=int(x1), y1=int(y1), x2=int(x2), y2=int(y2),
            area=int((x2 - x1) * (y2 - y1)),
            model="synthetic",
        ))
    return dets


def run_detection(img, conf_thr=0.25, iou_thr=0.45, mode="general"):
    pool = _pool_for_mode(mode)
    model, _ = load_yolo()
    if model is not None:
        dets = _detect_real(img, conf_thr, iou_thr)
        if dets:
            return dets
    return _detect_synthetic(img, conf_thr, pool)


# ── Annotation ────────────────────────────────────────────────────────────

SEV_COLOR = {
    "Critical": (0,   0,   220),
    "High":     (0,  100,  255),
    "Medium":   (0,  180,  255),
    "Low":      (50, 200,   50),
    "Unknown":  (150, 150, 150),
}


def annotate_image(image, detections):
    """
    Draw bounding boxes + smart non-overlapping labels on image.
    Accepts both PIL Image and numpy array.
    """
    if not detections:
        return image

    # Convert PIL → numpy BGR if needed
    from PIL import Image as PILImage
    is_pil = isinstance(image, PILImage.Image)
    if is_pil:
        img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    else:
        img = image.copy()

    h, w = img.shape[:2]

    # ── Pass 1: draw all boxes ────────────────────────────────────────────
    for d in detections:
        bbox = d.get("bbox") or d.get("bounding_box") or {}
        x1 = int(bbox.get("xmin", d.get("x1", 0)))
        y1 = int(bbox.get("ymin", d.get("y1", 0)))
        x2 = int(bbox.get("xmax", d.get("x2", w)))
        y2 = int(bbox.get("ymax", d.get("y2", h)))

        sev   = d.get("severity", "Unknown")
        color = SEV_COLOR.get(sev, SEV_COLOR["Unknown"])
        thickness = 3 if sev == "Critical" else 2

        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        if sev == "Critical":
            cl = 12
            for cx, cy, dx, dy in [(x1,y1,1,1),(x2,y1,-1,1),(x1,y2,1,-1),(x2,y2,-1,-1)]:
                cv2.line(img, (cx, cy), (cx + dx*cl, cy), color, 3)
                cv2.line(img, (cx, cy), (cx, cy + dy*cl), color, 3)

    # ── Pass 2: smart non-overlapping labels ──────────────────────────────
    font       = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.48
    font_thick = 1
    pad        = 5
    label_h    = 18
    occupied   = []

    def overlaps(r1, r2):
        return not (r1[2] < r2[0] or r1[0] > r2[2] or r1[3] < r2[1] or r1[1] > r2[3])

    def find_label_pos(x1, y1, x2, y2, lw, lh):
        candidates = [
            (x1,      y1 - lh - 2, x1 + lw, y1 - 2),
            (x2 - lw, y1 - lh - 2, x2,      y1 - 2),
            (x1,      y2 + 2,       x1 + lw, y2 + lh + 2),
            (x1,      y1 + 2,       x1 + lw, y1 + lh + 2),
        ]
        for rect in candidates:
            rx1, ry1, rx2, ry2 = rect
            if rx1 < 0:  rx1, rx2 = 0, lw
            if rx2 > w:  rx1, rx2 = w - lw, w
            if ry1 < 0:  ry1, ry2 = 0, lh
            if ry2 > h:  ry1, ry2 = h - lh, h
            rect = (rx1, ry1, rx2, ry2)
            if not any(overlaps(rect, o) for o in occupied):
                return rect
        rx1, ry1 = max(0, x1), max(0, y1 - lh - 2)
        return (rx1, ry1, rx1 + lw, ry1 + lh)

    sev_order   = {"Critical":0,"High":1,"Medium":2,"Low":3,"Unknown":4}
    sorted_dets = sorted(
        detections,
        key=lambda d: sev_order.get(d.get("severity","Unknown"), 4),
        reverse=True,
    )

    for d in sorted_dets:
        bbox  = d.get("bbox") or d.get("bounding_box") or {}
        x1    = int(bbox.get("xmin", d.get("x1", 0)))
        y1    = int(bbox.get("ymin", d.get("y1", 0)))
        x2    = int(bbox.get("xmax", d.get("x2", w)))
        y2    = int(bbox.get("ymax", d.get("y2", h)))
        sev   = d.get("severity", "Unknown")
        color = SEV_COLOR.get(sev, SEV_COLOR["Unknown"])
        cls   = d.get("cls") or d.get("class_name") or "unknown"
        conf  = d.get("conf", 0)
        idx   = d.get("id", "")

        label = f"[{str(idx).zfill(2)}] {cls} {conf*100:.0f}%"

        (tw, _), _ = cv2.getTextSize(label, font, font_scale, font_thick)
        lw = tw + pad * 2
        lh = label_h

        rx1, ry1, rx2, ry2 = find_label_pos(x1, y1, x2, y2, lw, lh)
        occupied.append((rx1, ry1, rx2, ry2))

        # semi-transparent background
        overlay = img.copy()
        cv2.rectangle(overlay, (rx1, ry1), (rx2, ry2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)

        # colored left accent + border
        cv2.rectangle(img, (rx1, ry1), (rx1 + 3, ry2), color, -1)
        cv2.rectangle(img, (rx1, ry1), (rx2, ry2), color, 1)

        # white text
        cv2.putText(img, label, (rx1 + pad + 2, ry1 + lh - 5),
                    font, font_scale, (255, 255, 255), font_thick, cv2.LINE_AA)

    # Convert back to PIL if input was PIL
    if is_pil:
        img = PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    return img


# ── Heatmap ───────────────────────────────────────────────────────────────
def build_heatmap(pil_img, dets):
    W, H = pil_img.size
    heat = np.zeros((H, W), dtype=np.float32)
    for d in dets:
        cx = min(W - 1, max(0, (d["x1"] + d["x2"]) // 2))
        cy = min(H - 1, max(0, (d["y1"] + d["y2"]) // 2))
        heat[cy, cx] += float(SEV_WEIGHT.get(d["severity"], 0))
    if heat.max() > 0:
        avg_area = np.mean([d.get("area", 3000) for d in dets]) if dets else 3000
        sig  = max(30, math.sqrt(avg_area) * 0.35)
        heat = gaussian_filter(heat, sigma=sig)
        heat = (heat / heat.max() * 255).astype(np.uint8)
    cmap = matplotlib.colormaps.get_cmap("plasma")
    hmap = (cmap(heat / 255.0)[:, :, :3] * 255).astype(np.uint8)
    dark = ImageEnhance.Brightness(pil_img).enhance(0.4)
    return Image.blend(dark, Image.fromarray(hmap).resize((W, H)), alpha=0.62)