"""
NautiCAI — detection + annotation + heatmap engine.
Multi-model support: SubPipe, SubPipeMini, SubPipeMini2, Subsea1 4-class
RESTORED TO ORIGINAL - NO FALSE POSITIVE FILTERING
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
    canonical_official_class,
    remap_to_inspection_label,
)
from defect_taxonomy import severity_for_taxonomy_label

ROOT = Path(__file__).resolve().parent.parent
ACTIVE_MODEL_FILE = (Path(__file__).resolve().parent / ".active_model_key")

# ── Available Models ──────────────────────────────────────────────────────
AVAILABLE_MODELS = {
    "merged_original":  "weights/best_merged_original.pt",
    "subpipe_full":     "weights/best_subpipe_full.pt",
    "subpipemini":      "weights/best_subpipemini.pt",
    "subpipemini2":     "weights/best_subpipemini2.pt",
    "subsea1_4class":   "weights/best_subsea1_4class.pt",
    "archive":          "weights/best_archive.pt",
    "official_19":      "weights/best_official_19.pt",
    "subsea_taxonomy":  "weights/best_subsea_taxonomy.pt",
    "hull_taxonomy":    "weights/best_hull_taxonomy.pt",
}

TAXONOMY_MODEL_KEYS = frozenset({"subsea_taxonomy", "hull_taxonomy"})
OFFICIAL_19_MODEL_KEYS = frozenset({"official_19"})
MULTICLASS_INSPECTION_KEYS = TAXONOMY_MODEL_KEYS | OFFICIAL_19_MODEL_KEYS
# When the active head only localises structure (e.g. archive → Pipeline) try these in order.
# merged_original first — matches older deployments that often label fouled metal as Corrosion etc.;
# official_19 second for taxonomy-aligned Marine Growth / Biofouling when merged finds nothing.
_INSPECTION_HEAD_FALLBACK_KEYS = ("merged_original", "official_19")

MODEL_DESCRIPTIONS = {
    "merged_original":  "NautiCAI Merged Dataset — Original Production Model — Multi-class",
    "subpipe_full":     "SubPipe Full 21K Images — Pipeline Segmentation",
    "subpipemini":      "SubPipeMini — Pipeline Segmentation — 99.5% mAP",
    "subpipemini2":     "SubPipeMini2 — Pipeline Segmentation — 99.5% mAP",
    "subsea1_4class":   "Subsea Pipeline v2 — Anode, Corner, Flange, Pipe — 99.5% mAP",
    "archive":          "Legacy archive head (asset/part names) → UI uses CLASS_REMAP to official 19",
    "official_19":      "Your YOLO trained on configs/nauticai_official_19.yaml (inspection 19, no remap)",
    "subsea_taxonomy":  "Your trained subsea pipeline defect model (configs/subsea_pipeline_defects.yaml)",
    "hull_taxonomy":    "Your trained ship hull defect model (configs/ship_hull_defects.yaml)",
}

def _slugify_key(s: str) -> str:
    out = []
    for ch in str(s):
        if ch.isalnum():
            out.append(ch.lower())
        else:
            out.append("_")
    key = "".join(out).strip("_")
    while "__" in key:
        key = key.replace("__", "_")
    return key or "model"


def _register_custom_weights() -> None:
    """Auto-register any local `weights/*.pt` as selectable model keys.

    This makes it easy to drop trained checkpoints into `weights/` without editing code.
    Keys are added as: `custom_<filename_stem>`.
    """
    try:
        wdir = ROOT / "weights"
        if not wdir.exists():
            return
        for p in sorted(wdir.glob("*.pt")):
            rel = f"weights/{p.name}"
            if rel in AVAILABLE_MODELS.values():
                continue
            key = f"custom_{_slugify_key(p.stem)}"
            base = key
            i = 2
            while key in AVAILABLE_MODELS:
                key = f"{base}_{i}"
                i += 1
            AVAILABLE_MODELS[key] = rel
            MODEL_DESCRIPTIONS.setdefault(key, f"Custom weights: {p.name}")
    except Exception:
        return


_register_custom_weights()


def _load_persisted_model_key(default: str) -> str:
    try:
        if ACTIVE_MODEL_FILE.exists():
            key = ACTIVE_MODEL_FILE.read_text(encoding="utf-8").strip()
            if key:
                return key
    except Exception:
        pass
    return default


_active_model_key = _load_persisted_model_key(os.environ.get("NAUTICAI_DEFAULT_MODEL", "merged_original"))


def set_active_model(model_key: str):
    global _active_model_key, _model_cache
    if model_key in AVAILABLE_MODELS:
        _active_model_key = model_key
        _model_cache = {}
        try:
            ACTIVE_MODEL_FILE.write_text(model_key, encoding="utf-8")
        except Exception:
            pass


def get_active_model_key():
    return _active_model_key


def is_taxonomy_model_key(model_key: str) -> bool:
    return model_key in TAXONOMY_MODEL_KEYS


def get_model_descriptions():
    return MODEL_DESCRIPTIONS


# ── Model loading ─────────────────────────────────────────────────────────
_model_cache = {}


def _load_yolo_for_key(model_key: str):
    """Load a specific model by key without changing global active model."""
    rel = AVAILABLE_MODELS.get(model_key)
    if not rel:
        return None, None
    p = ROOT / rel
    if not p.exists():
        return None, None
    key = str(p)
    if key not in _model_cache:
        from ultralytics import YOLO
        print(f"Loading model: {p.name}")
        _model_cache[key] = YOLO(key)
    return _model_cache[key], p


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


def get_resolved_weights_path():
    """Filesystem path to the weights file actually used by ``load_yolo()`` (or None)."""
    return _find_model()


# ── Detection ─────────────────────────────────────────────────────────────
def _pool_for_mode(mode: str):
    if mode == "pipeline":
        return PIPELINE_DEFECTS
    elif mode == "cable":
        return CABLE_DEFECTS
    return DEFECT_CLASSES


def split_asset_and_defects(dets: list, mode: str) -> tuple[list, list]:
    """Split detections into asset boxes vs defect boxes.

    `Pipeline` from archive/subsea heads is a pipe *localization* class (STRUCTURE), not one of the
    inspection defects — exclude it from counts, risk, heatmap, and defect tables in every UI mode.
    """
    assets, defects = [], []
    for d in dets:
        cls = str(d.get("cls", ""))
        if cls == "Pipeline":
            assets.append(d)
        else:
            defects.append(d)
    return assets, defects


def boxes_for_visualization(assets: list, defects: list, mode: str) -> list:
    """Which boxes to draw: pipeline mode shows pipe localisation + defects; general/hull/cable show defects only."""
    if mode == "pipeline":
        return assets + defects
    return list(defects)


def _box_area_px(d: dict) -> int:
    return max(1, (d["x2"] - d["x1"]) * (d["y2"] - d["y1"]))


def _bbox_center_inside(inner: dict, outer: dict) -> bool:
    cx = (inner["x1"] + inner["x2"]) / 2
    cy = (inner["y1"] + inner["y2"]) / 2
    return outer["x1"] <= cx <= outer["x2"] and outer["y1"] <= cy <= outer["y2"]


def suppress_nested_boxes(items: list, area_ratio: float) -> list:
    """Drop smaller boxes whose center falls inside another box at least `area_ratio`× larger (same-class group).

    IoU-NMS often keeps a huge + tiny duplicate on one fouling patch because IoU stays low.
    """
    if len(items) <= 1:
        return items
    survivors = []
    for d in sorted(items, key=lambda x: float(x.get("conf", 0)), reverse=True):
        ad = _box_area_px(d)
        redundant = False
        for other in items:
            if other is d:
                continue
            ao = _box_area_px(other)
            if ao >= ad * area_ratio and _bbox_center_inside(d, other):
                redundant = True
                break
        if not redundant:
            survivors.append(d)
    return survivors


def _run_yolo_predict(model, model_tag: str, img, conf_thr, iou_thr, mode: str) -> list:
    results = model.predict(img, conf=conf_thr, iou=iou_thr, agnostic_nms=True, verbose=False)[0]
    dets = []
    det_id = 0
    img_w = img.width if hasattr(img, "width") else img.shape[1]
    img_h = img.height if hasattr(img, "height") else img.shape[0]
    img_area = img_w * img_h

    has_masks = hasattr(results, "masks") and results.masks is not None

    try:
        min_cov = float(os.environ.get("NAUTICAI_MIN_BOX_COVERAGE", "0.0005"))
    except Exception:
        min_cov = 0.0005
    try:
        max_cov = float(os.environ.get("NAUTICAI_MAX_BOX_COVERAGE", "0.88"))
    except Exception:
        max_cov = 0.88

    for i, box in enumerate(results.boxes):
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])
        cls_i = int(box.cls[0])
        box_area = (x2 - x1) * (y2 - y1)
        coverage = box_area / img_area if img_area > 0 else 0
        if coverage > max_cov or coverage < min_cov:
            continue
        cls_name = model.names.get(cls_i, DEFECT_CLASSES[cls_i % len(DEFECT_CLASSES)])
        cls_key = str(cls_name).strip()
        cls_key_l = cls_key.lower()

        if model_tag == "archive":
            if cls_key_l == "pipeline":
                cls = "Pipeline"
                sev = SEVERITY_MAP.get("Pipeline", "Low")
            else:
                cls = remap_to_inspection_label(cls_key)
                sev = SEVERITY_MAP.get(cls, "Medium")
        elif model_tag in TAXONOMY_MODEL_KEYS:
            cls = cls_key
            sev = severity_for_taxonomy_label(cls)
        elif model_tag in OFFICIAL_19_MODEL_KEYS:
            cls = canonical_official_class(cls_key) or cls_key.replace("_", " ").strip().title()
            sev = SEVERITY_MAP.get(cls, "Medium")
        elif mode == "pipeline" and cls_key_l == "pipeline":
            cls = "Pipeline"
            sev = SEVERITY_MAP.get(cls, "Low")
        else:
            cls = remap_to_inspection_label(cls_key)
            sev = SEVERITY_MAP.get(cls, "Medium")
        det_id += 1

        det = dict(
            id=det_id,
            cls=cls,
            severity=sev,
            conf=conf,
            x1=x1, y1=y1, x2=x2, y2=y2,
            area=box_area,
            model=model_tag,
        )

        if has_masks and i < len(results.masks.data):
            mask = results.masks.data[i].cpu().numpy()
            mask_coverage = float(mask.sum()) / (mask.shape[0] * mask.shape[1])
            det["mask_coverage"] = round(mask_coverage * 100, 2)

        dets.append(det)

    def _iou(a, b) -> float:
        ax1, ay1, ax2, ay2 = a["x1"], a["y1"], a["x2"], a["y2"]
        bx1, by1, bx2, by2 = b["x1"], b["y1"], b["x2"], b["y2"]
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        inter = iw * ih
        if inter <= 0:
            return 0.0
        area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
        area_b = max(1, (bx2 - bx1) * (by2 - by1))
        return inter / float(area_a + area_b - inter)

    def _dedupe_class(items, thr: float, max_keep: int | None):
        kept = []
        for d in sorted(items, key=lambda x: float(x.get("conf", 0)), reverse=True):
            if any(_iou(d, k) >= thr for k in kept):
                continue
            kept.append(d)
            if max_keep is not None and len(kept) >= max_keep:
                break
        return kept

    try:
        dedupe_iou = float(os.environ.get("NAUTICAI_DEDUPE_IOU", "0.65"))
    except Exception:
        dedupe_iou = 0.65
    cap_marine = int(os.environ.get("NAUTICAI_MAX_MARINE_GROWTH", "3"))
    cap_bio = int(os.environ.get("NAUTICAI_MAX_BIOFOULING", "3"))
    try:
        nested_ratio = float(os.environ.get("NAUTICAI_NESTED_AREA_RATIO", "1.2"))
    except Exception:
        nested_ratio = 1.2
    suppress_nested = os.environ.get("NAUTICAI_SUPPRESS_NESTED_BIO", "true").strip().lower() not in (
        "0", "false", "no", "off",
    )

    by_cls = {}
    for d in dets:
        by_cls.setdefault(d.get("cls", "—"), []).append(d)
    out = []

    def _norm_cls(name: str) -> str:
        return str(name).strip().lower().replace(" ", "_")

    def _marine_texture(name: str) -> bool:
        return _norm_cls(name) in {"marine_growth", "algae", "mussels", "barnacles", "slime_layer"}

    def _bio_texture(name: str) -> bool:
        return _norm_cls(name) in {"biofouling", "biofouling_light", "biofouling_heavy"}

    for cls_name, items in by_cls.items():
        if cls_name == "Marine Growth" or _marine_texture(cls_name):
            merged = _dedupe_class(items, dedupe_iou, cap_marine)
            if suppress_nested:
                merged = suppress_nested_boxes(merged, nested_ratio)
            out.extend(merged)
        elif cls_name == "Biofouling" or _bio_texture(cls_name):
            merged = _dedupe_class(items, dedupe_iou, cap_bio)
            if suppress_nested:
                merged = suppress_nested_boxes(merged, nested_ratio)
            out.extend(merged)
        else:
            out.extend(_dedupe_class(items, dedupe_iou, None))

    out = sorted(out, key=lambda x: float(x.get("conf", 0)), reverse=True)
    for idx, d in enumerate(out, start=1):
        d["id"] = idx
    return out


def _detect_real(img, conf_thr, iou_thr, mode: str = "general") -> list:
    if mode == "pipeline" and _active_model_key not in MULTICLASS_INSPECTION_KEYS:
        model, _ = _load_yolo_for_key("subpipe_full")
        model_tag = "subpipe_full"
    else:
        model, _ = load_yolo()
        model_tag = _active_model_key
    if model is None:
        return []
    return _run_yolo_predict(model, model_tag, img, conf_thr, iou_thr, mode)


def _detect_real_with_model_key(img, conf_thr, iou_thr, mode: str, model_key: str) -> list:
    model, _ = _load_yolo_for_key(model_key)
    if model is None:
        return []
    return _run_yolo_predict(model, model_key, img, conf_thr, iou_thr, mode)


def _inspection_fallback_enabled() -> bool:
    v = os.environ.get("NAUTICAI_INSPECTION_FALLBACK", "true").strip().lower()
    return v not in ("0", "false", "no", "off")


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
    primary, _ = load_yolo()
    if primary is None:
        return _detect_synthetic(img, conf_thr, pool)

    dets = _detect_real(img, conf_thr, iou_thr, mode)
    if not dets:
        return _detect_synthetic(img, conf_thr, pool)

    _, defects = split_asset_and_defects(dets, mode)
    if defects:
        return dets

    # Primary returned boxes but none are inspection defects (common with best_archive.pt: Pipeline-only).
    if not _inspection_fallback_enabled():
        return dets

    active = get_active_model_key()
    for key in _INSPECTION_HEAD_FALLBACK_KEYS:
        if key == active:
            continue
        d2 = _detect_real_with_model_key(img, conf_thr, iou_thr, mode, key)
        _, def2 = split_asset_and_defects(d2, mode)
        if not def2:
            continue
        pipes = [d for d in dets if d.get("cls") == "Pipeline"]
        if pipes:
            non_pipe = [d for d in d2 if d.get("cls") != "Pipeline"]
            merged = pipes + non_pipe
            for i, d in enumerate(merged, 1):
                d["id"] = i
            return merged
        return d2

    return dets


# ── Annotation ────────────────────────────────────────────────────────────

SEV_COLOR = {
    "Critical": (0,   0,   220),
    "High":     (0,  100,  255),
    "Medium":   (0,  180,  255),
    "Low":      (50, 200,   50),
    "Unknown":  (150, 150, 150),
}


def annotate_image(image, detections, mode: str = "general"):
    """
    Draw bounding boxes + smart non-overlapping labels on image.
    Accepts both PIL Image and numpy array.
    """
    if not detections:
        return image

    from PIL import Image as PILImage
    is_pil = isinstance(image, PILImage.Image)
    if is_pil:
        img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    else:
        img = image.copy()

    h, w = img.shape[:2]

    for d in detections:
        bbox = d.get("bbox") or d.get("bounding_box") or {}
        x1 = int(bbox.get("xmin", d.get("x1", 0)))
        y1 = int(bbox.get("ymin", d.get("y1", 0)))
        x2 = int(bbox.get("xmax", d.get("x2", w)))
        y2 = int(bbox.get("ymax", d.get("y2", h)))

        sev = d.get("severity", "Unknown")
        color = SEV_COLOR.get(sev, SEV_COLOR["Unknown"])
        thickness = 3 if sev == "Critical" else 2

        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness)

        if sev == "Critical":
            cl = 12
            for cx, cy, dx, dy in [(x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)]:
                cv2.line(img, (cx, cy), (cx + dx * cl, cy), color, 3)
                cv2.line(img, (cx, cy), (cx, cy + dy * cl), color, 3)

    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.48
    font_thick = 1
    pad = 5
    label_h = 18
    occupied = []

    def overlaps(r1, r2):
        return not (r1[2] < r2[0] or r1[0] > r2[2] or r1[3] < r2[1] or r1[1] > r2[3])

    def find_label_pos(x1, y1, x2, y2, lw, lh):
        candidates = [
            (x1, y1 - lh - 2, x1 + lw, y1 - 2),
            (x2 - lw, y1 - lh - 2, x2, y1 - 2),
            (x1, y2 + 2, x1 + lw, y2 + lh + 2),
            (x1, y1 + 2, x1 + lw, y1 + lh + 2),
        ]
        for rect in candidates:
            rx1, ry1, rx2, ry2 = rect
            if rx1 < 0:
                rx1, rx2 = 0, lw
            if rx2 > w:
                rx1, rx2 = w - lw, w
            if ry1 < 0:
                ry1, ry2 = 0, lh
            if ry2 > h:
                ry1, ry2 = h - lh, h
            rect = (rx1, ry1, rx2, ry2)
            if not any(overlaps(rect, o) for o in occupied):
                return rect
        rx1, ry1 = max(0, x1), max(0, y1 - lh - 2)
        return (rx1, ry1, rx1 + lw, ry1 + lh)

    sev_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Unknown": 4}
    sorted_dets = sorted(
        detections,
        key=lambda d: sev_order.get(d.get("severity", "Unknown"), 4),
        reverse=True,
    )

    for d in sorted_dets:
        bbox = d.get("bbox") or d.get("bounding_box") or {}
        x1 = int(bbox.get("xmin", d.get("x1", 0)))
        y1 = int(bbox.get("ymin", d.get("y1", 0)))
        x2 = int(bbox.get("xmax", d.get("x2", w)))
        y2 = int(bbox.get("ymax", d.get("y2", h)))
        sev = d.get("severity", "Unknown")
        color = SEV_COLOR.get(sev, SEV_COLOR["Unknown"])
        cls = d.get("cls") or d.get("class_name") or "unknown"
        conf = d.get("conf", 0)
        idx = d.get("id", "")
        role = ""
        if mode == "pipeline" and cls == "Pipeline":
            role = " [asset]"
        label = f"[{str(idx).zfill(2)}] {cls}{role} {conf * 100:.0f}%"

        (tw, _), _ = cv2.getTextSize(label, font, font_scale, font_thick)
        lw = tw + pad * 2
        lh = label_h

        rx1, ry1, rx2, ry2 = find_label_pos(x1, y1, x2, y2, lw, lh)
        occupied.append((rx1, ry1, rx2, ry2))

        overlay = img.copy()
        cv2.rectangle(overlay, (rx1, ry1), (rx2, ry2), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.65, img, 0.35, 0, img)

        cv2.rectangle(img, (rx1, ry1), (rx1 + 3, ry2), color, -1)
        cv2.rectangle(img, (rx1, ry1), (rx2, ry2), color, 1)

        cv2.putText(img, label, (rx1 + pad + 2, ry1 + lh - 5),
                    font, font_scale, (255, 255, 255), font_thick, cv2.LINE_AA)

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
        sig = max(30, math.sqrt(avg_area) * 0.35)
        heat = gaussian_filter(heat, sigma=sig)
        heat = (heat / heat.max() * 255).astype(np.uint8)
    cmap = matplotlib.colormaps.get_cmap("plasma")
    hmap = (cmap(heat / 255.0)[:, :, :3] * 255).astype(np.uint8)
    dark = ImageEnhance.Brightness(pil_img).enhance(0.4)
    return Image.blend(dark, Image.fromarray(hmap).resize((W, H)), alpha=0.62)
