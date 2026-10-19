"""
NautiCAI — Severity mapping for detected classes.
"""

SEVERITY_MAP = {
    # Official 19 defect classes (+ asset helper — not in the 19)
    "Corrosion": "Critical", "Crack": "Critical", "Fracture": "Critical", "Leakage": "Critical",
    "Marine Growth": "High", "Biofouling": "High", "Weld Defect": "High", "Anode Damage": "High",
    "CP Failure": "High", "Pitting": "Medium", "Paint Damage": "Medium", "Coating Failure": "Medium",
    "Deformation": "Medium", "Blockage": "Medium", "Dent": "Low", "Scaling": "Low",
    "Spalling": "Low", "Disbondment": "Low", "Foreign Object": "Low",
    "Pipeline": "Low",
}

# Official inspection defect vocabulary (matches Severity Classification table).
OFFICIAL_DEFECT_CLASSES_19 = [
    "Corrosion", "Crack", "Fracture", "Leakage",
    "Marine Growth", "Biofouling", "Weld Defect", "Anode Damage", "CP Failure",
    "Pitting", "Paint Damage", "Coating Failure", "Deformation", "Blockage",
    "Dent", "Scaling", "Spalling", "Disbondment", "Foreign Object",
]

# Raw YOLO class ids for `best_archive.pt` (dataset categories — remapped to OFFICIAL_DEFECT_CLASSES_19).
ARCHIVE_MODEL_CLASSES_19 = [
    "Pipeline",
    "Leakage",
    "Pipe Coupling",
    "Concrete",
    "Anode",
    "Flange",
    "Buoy",
    "Bend Restrictor",
    "Biofouling",
    "Anomaly",
    "Bilge Keel",
    "Draft Mark",
    "Hull",
    "Propeller",
    "Ropeguard",
    "Rudder",
    "Sea Chest",
    "Thruster Blades",
    "Thruster Grating",
]

CLASS_REMAP = {
    # Raw YOLO / legacy labels → official 19 only (pipeline handled separately in detection.py).
    "concrete": "Marine Growth", "hull": "Paint Damage",
    "propeller": "Biofouling", "anode": "Anode Damage", "leakage": "Leakage",
    "anomaly": "Crack", "biofouling": "Biofouling", "bilge_keel": "Coating Failure",
    "draft_mark": "Paint Damage", "ropeguard": "Foreign Object", "rudder": "Deformation",
    "sea_chest": "Blockage", "thruster_blades": "Weld Defect", "thruster_grating": "Disbondment",
    "flange": "Weld Defect", "buoy": "Foreign Object", "bend_restrictor": "Deformation",
    "pipe_coupling": "Coating Failure", "free_span": "Fracture", "healthy": "Foreign Object",
}

SEV_WEIGHT = {"Critical": 25, "High": 12, "Medium": 6, "Low": 2}

# Canonical list for UI, synthetic fallback, and training target (`configs/nauticai_official_19.yaml`).
DEFECT_CLASSES = list(OFFICIAL_DEFECT_CLASSES_19)

# Normalize YOLO output (any casing / snake_case) → exact string in OFFICIAL_DEFECT_CLASSES_19.
_OFFICIAL_BY_SLUG: dict[str, str] = {
    o.lower().replace(" ", "_").replace("-", "_"): o for o in OFFICIAL_DEFECT_CLASSES_19
}


def canonical_official_class(raw: str) -> str | None:
    """If raw matches one of the official 19 labels, return that label; else None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if s in OFFICIAL_DEFECT_CLASSES_19:
        return s
    slug = s.lower().replace(" ", "_").replace("-", "_")
    return _OFFICIAL_BY_SLUG.get(slug)


def _label_slug(raw: str) -> str:
    return str(raw).strip().lower().replace(" ", "_").replace("-", "_")


def remap_to_inspection_label(raw: str) -> str:
    """Turn raw YOLO class text (Title Case, snake_case, etc.) into the inspection label.

    Order: exact official 19 match → CLASS_REMAP by slug → CLASS_REMAP by lowercase → title fallback.
    Fixes archive heads that emit \"Pipe Coupling\" while CLASS_REMAP only had pipe_coupling.
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    hit = canonical_official_class(s)
    if hit:
        return hit
    slug = _label_slug(s)
    if slug in CLASS_REMAP:
        return CLASS_REMAP[slug]
    lo = s.lower()
    if lo in CLASS_REMAP:
        return CLASS_REMAP[lo]
    return s.replace("_", " ").strip().title()


_OFFICIAL_19_SET = frozenset(OFFICIAL_DEFECT_CLASSES_19)


def official_19_only_outputs() -> bool:
    """When True (default), API/PDF only expose the Severity Table 19 — no extra taxonomy labels."""
    import os

    v = os.environ.get("NAUTICAI_OFFICIAL_19_ONLY", "true").strip().lower()
    return v not in ("0", "false", "no", "off")


def filter_defects_to_official_19(defects: list) -> list:
    """Drop non-official classes; set cls + severity from the inspection table."""
    out = []
    for d in defects:
        c = canonical_official_class(str(d.get("cls", "")))
        if c is None or c not in _OFFICIAL_19_SET:
            continue
        dd = dict(d)
        dd["cls"] = c
        dd["severity"] = SEVERITY_MAP.get(c, "Medium")
        out.append(dd)
    for i, dd in enumerate(out, 1):
        dd["id"] = i
    return out


PIPELINE_DEFECTS = list(OFFICIAL_DEFECT_CLASSES_19)
CABLE_DEFECTS = ["Fracture", "Deformation", "Foreign Object", "Biofouling", "Marine Growth", "Dent"]


def compute_risk(dets: list) -> int:
    """Health-style score 0–100 (higher is better).

    A plain sum of per-detection severity weights collapses to 0 on long videos with
    hundreds of boxes. Use a saturating curve so aggregates stay interpretable.
    Tune with env ``NAUTICAI_RISK_AGGREGATE_K`` (default 120): larger K → gentler penalty.
    """
    import os

    if not dets:
        return 100
    raw = float(sum(SEV_WEIGHT.get(d.get("severity", "Medium"), 0) for d in dets))
    try:
        k = float(os.environ.get("NAUTICAI_RISK_AGGREGATE_K", "120"))
    except (TypeError, ValueError):
        k = 120.0
    k = max(k, 1e-6)
    health = 100.0 / (1.0 + raw / k)
    return max(0, min(100, int(round(health))))


def score_to_grade(s: int) -> str:
    if s >= 76:
        return "A"
    elif s >= 51:
        return "B"
    elif s >= 26:
        return "C"
    return "D"
