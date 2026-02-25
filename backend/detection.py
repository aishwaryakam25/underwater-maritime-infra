"""
NautiCAI — detection + annotation + heatmap engine.
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

# ── Model loading ────────────────────────────────────────────────────────
_model_cache = {}

def _find_model():
    for n in ["best.pt", "yolov8s.pt", "yolov8n.pt"]:
        p = ROOT / n
        if p.exists():
            return p
    return None


def _auto_download_model():
    model_path = ROOT / "best.pt"
    if not model_path.exists():
        try:
            from huggingface_hub import hf_hub_download
            print("Downloading model from Hugging Face...")
            hf_hub_download(
                repo_id="aishwarya252525/nauticai-yolov8",
                filename="best.pt",
                local_dir=str(ROOT),
                local_dir_use_symlinks=False,
            )
        except Exception as e:
            print(f"Model download failed: {e}")


def load_yolo():
    model_path = _find_model()
    if model_path is None:
        _auto_download_model()
        model_path = _find_model()
    if model_path is None:
        return None, None
    key = str(model_path)
    if key not in _model_cache:
        from ultralytics import YOLO
        _model_cache[key] = YOLO(key)
    return _model_cache[key], model_path


def get_model_name():
    _, path = load_yolo()
    return path.name if path else "Demo"


# ── Detection ────────────────────────────────────────────────────────────
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
    for box in results.boxes:
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
        dets.append(dict(id=det_id, cls=cls, severity=sev, conf=conf,
                         x1=x1, y1=y1, x2=x2, y2=y2, area=box_area))
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
        dets.append(dict(id=i + 1, cls=cls, severity=sev, conf=conf,
                         x1=int(x1), y1=int(y1), x2=int(x2), y2=int(y2),
                         area=int((x2 - x1) * (y2 - y1))))
    return dets


def run_detection(img, conf_thr=0.25, iou_thr=0.45, mode="general"):
    pool = _pool_for_mode(mode)
    model, _ = load_yolo()
    if model is not None:
        dets = _detect_real(img, conf_thr, iou_thr)
        if dets:
            return dets
    return _detect_synthetic(img, conf_thr, pool)


# ── Annotation ───────────────────────────────────────────────────────────
SEVERITY_COLORS = {
    "Critical": (255, 50, 50),
    "High": (255, 165, 0),
    "Medium": (30, 144, 255),
    "Low": (50, 205, 50),
}


def annotate_image(pil_img, dets):
    img = pil_img.copy().convert("RGBA")
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for det in dets:
        x1, y1, x2, y2 = int(det["x1"]), int(det["y1"]), int(det["x2"]), int(det["y2"])
        sev = det.get("severity", "Medium")
        color = SEVERITY_COLORS.get(sev, (30, 144, 255))
        draw.rectangle([x1, y1, x2, y2], fill=(*color, 40), outline=(*color, 255), width=3)
        label = f"[{det['id']:02d}] {det['cls']} {det['conf'] * 100:.0f}%"
        draw.rectangle([x1, y1 - 20, x1 + len(label) * 7, y1], fill=(*color, 200))
        draw.text((x1 + 2, y1 - 18), label, fill=(255, 255, 255, 255))

    result = Image.alpha_composite(img, overlay)
    return result.convert("RGB")


def build_heatmap(pil_img, dets):
    W, H = pil_img.size
    heat = np.zeros((H, W), dtype=np.float32)
    for d in dets:
        cx = min(W - 1, max(0, (d["x1"] + d["x2"]) // 2))
        cy = min(H - 1, max(0, (d["y1"] + d["y2"]) // 2))
        heat[cy, cx] += float(SEV_WEIGHT.get(d["severity"], 0))
    if heat.max() > 0:
        avg_area = np.mean([d.get("area", 3000) for d in dets]) if dets else 3000
        sig = max(30, math.sqrt(avg_area) * 0.35)
        heat = gaussian_filter(heat, sigma=sig)
        heat = (heat / heat.max() * 255).astype(np.uint8)
    cmap = matplotlib.colormaps.get_cmap("plasma")
    hmap = (cmap(heat / 255.0)[:, :, :3] * 255).astype(np.uint8)
    dark = ImageEnhance.Brightness(pil_img).enhance(0.4)
    return Image.blend(dark, Image.fromarray(hmap).resize((W, H)), alpha=0.62)
