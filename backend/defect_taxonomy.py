"""
Target defect taxonomy for reporting and future multi-head / multi-model training.

The archive YOLO weights (`best_archive.pt`) expose 19 *dataset image categories*,
not this full defect vocabulary. Use `ARCHIVE_MODEL_CLASSES_19` from severity.py for
raw model outputs; use this module for inspection checklists and UI taxonomy.
"""

from typing import Any

# ── Subsea Pipeline — defect / condition classes ─────────────────────────────
SUBSEA_PIPELINE_DEFECTS: list[str] = [
    "corrosion",
    "pitting_corrosion",
    "coating_damage",
    "coating_disbondment",
    "anode_damage",
    "crack",
    "weld_defect",
    "dent",
    "buckle",
    "ovality",
    "free_span",
    "exposed_pipeline",
    "buried_pipeline",
    "scouring",
    "debris",
    "marine_growth",
    "sediment_cover",
    "leakage",
]

SUBSEA_PIPELINE_STRUCTURE: dict[str, Any] = {
    "domain": "subsea_pipeline",
    "title": "Subsea Pipeline — Detection Classes",
    "categories": [
        {
            "name": "Defects & conditions",
            "classes": SUBSEA_PIPELINE_DEFECTS,
        }
    ],
    "flat_classes": SUBSEA_PIPELINE_DEFECTS,
}

# ── Ship Hull — grouped defect classes ───────────────────────────────────────
SHIP_HULL_STRUCTURE: dict[str, Any] = {
    "domain": "ship_hull",
    "title": "Ship Hull — Defect Classes",
    "categories": [
        {
            "name": "Corrosion & surface degradation",
            "classes": [
                "corrosion",
                "pitting_corrosion",
                "galvanic_corrosion",
                "stray_current_corrosion",
            ],
        },
        {
            "name": "Structural defects",
            "classes": [
                "crack",
                "hull_deformation",
                "dent",
                "plate_buckling",
                "weld_defect",
            ],
        },
        {
            "name": "Coating / paint issues",
            "classes": [
                "coating_damage",
                "paint_peeling",
                "blistering",
                "coating_erosion",
            ],
        },
        {
            "name": "Biofouling (marine growth)",
            "classes": [
                "biofouling_light",
                "biofouling_heavy",
                "barnacles",
                "algae",
                "mussels",
                "slime_layer",
            ],
        },
        {
            "name": "Impact / external damage",
            "classes": [
                "anchor_damage",
                "collision_damage",
                "grounding_damage",
            ],
        },
        {
            "name": "Propulsion & appendages",
            "classes": [
                "propeller_damage",
                "cavitation_damage",
                "rudder_damage",
                "thruster_damage",
            ],
        },
    ],
}

SHIP_HULL_FLAT: list[str] = []
for _cat in SHIP_HULL_STRUCTURE["categories"]:
    SHIP_HULL_FLAT.extend(_cat["classes"])
SHIP_HULL_STRUCTURE["flat_classes"] = SHIP_HULL_FLAT


def all_taxonomy_classes() -> list[str]:
    """Union of subsea pipeline + hull defect ids (deduped, stable order)."""
    seen: set[str] = set()
    out: list[str] = []
    for c in SUBSEA_PIPELINE_DEFECTS + SHIP_HULL_FLAT:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


TRAINING_CONFIG_PATHS = {
    "subsea_pipeline": "configs/subsea_pipeline_defects.yaml",
    "ship_hull": "configs/ship_hull_defects.yaml",
}

# Weights filenames (copy your trained `best.pt` here — see training_roadmap).
TAXONOMY_WEIGHT_FILES = {
    "subsea_taxonomy": "weights/best_subsea_taxonomy.pt",
    "hull_taxonomy": "weights/best_hull_taxonomy.pt",
}

_CRITICAL_SLUGS = frozenset({
    "leakage", "crack", "buckle", "free_span", "collision_damage", "grounding_damage",
    "anchor_damage", "plate_buckling",
})
_HIGH_SLUGS = frozenset({
    "corrosion", "pitting_corrosion", "galvanic_corrosion", "stray_current_corrosion",
    "marine_growth", "coating_disbondment", "anode_damage", "weld_defect", "hull_deformation",
    "biofouling_heavy", "barnacles", "mussels", "propeller_damage", "rudder_damage",
    "thruster_damage", "cavitation_damage",
})
_LOW_SLUGS = frozenset({"buried_pipeline"})


def severity_for_taxonomy_label(cls_id: str) -> str:
    """Map snake_case (or Title Case) taxonomy label to Critical/High/Medium/Low for risk UI."""
    key = str(cls_id).strip().lower().replace(" ", "_")
    if key in _CRITICAL_SLUGS:
        return "Critical"
    if key in _HIGH_SLUGS:
        return "High"
    if key in _LOW_SLUGS:
        return "Low"
    return "Medium"


def training_roadmap() -> dict[str, Any]:
    """What you must do for the neural net to predict every taxonomy class."""
    return {
        "reality_check": (
            "A model can only output classes it was trained on. Your current `best_archive.pt` "
            "does not include most of these labels. Labels below are the *target schema*."
        ),
        "recommended_approach": "two_specialist_models",
        "why_two_models": (
            "Subsea pipeline and ship hull images look different (ROV vs hull surveys). "
            "Training one YOLO with both domains forces one shared backbone to learn both; "
            "two checkpoints (subsea + hull) usually generalizes better and avoids class confusion."
        ),
        "if_you_already_trained": [
            "If you trained on `configs/nauticai_official_19.yaml` (the Severity Table 19), copy `best.pt` to "
            "`weights/best_official_19.pt` and switch `model_key=official_19` — no CLASS_REMAP.",
            f"If you trained extended subsea/hull YAMLs: copy best weights to `{TAXONOMY_WEIGHT_FILES['subsea_taxonomy']}` "
            f"and `{TAXONOMY_WEIGHT_FILES['hull_taxonomy']}` (create `weights/` if needed).",
            "Class indices in the checkpoint must match your training YAML class order.",
            "Switch models: POST `/api/models/switch` with Form field `model_key=…`.",
            "GET `/api/models` lists keys and whether each weight file exists.",
        ],
        "steps": [
            "Collect real inspection images (or licensed datasets) for each domain.",
            "Annotate bounding boxes with labels exactly matching snake_case names in this API "
            "(use CVAT, Label Studio, or Roboflow; export YOLOv8 format).",
            "Put images under train/ and val/ and point `path`, `train`, `val` in the YAML files "
            f"({TRAINING_CONFIG_PATHS['subsea_pipeline']}, {TRAINING_CONFIG_PATHS['ship_hull']}).",
            "Train Ultralytics YOLO, e.g.: "
            "`yolo detect train data=configs/subsea_pipeline_defects.yaml model=yolov8m.pt imgsz=640 epochs=150` "
            "and separately for ship hull YAML.",
            "Copy each run's `weights/best.pt` into this repo (e.g. `weights/best_subsea_full.pt`, "
            "`weights/best_hull_full.pt`).",
            "Register keys in `backend/detection.py` `AVAILABLE_MODELS` and select by inspection mode "
            "(or add UI model picker). For those weights, disable CLASS_REMAP so raw names match taxonomy.",
            "Validate per-class precision/recall; add images for weak classes before demo/interviews.",
        ],
        "alternative_unified_model": (
            "Merge both domains into one dataset with `nc` = len(combined_flat_unique) from "
            "`/api/defect-taxonomy`. Harder to balance classes; only if you need one file everywhere."
        ),
        "min_data_rule_of_thumb": (
            "Aim for hundreds of instances per class across varied lighting/turbidity; rare classes "
            "need oversampling or weighted loss."
        ),
        "training_yaml_templates": TRAINING_CONFIG_PATHS,
    }


def taxonomy_payload() -> dict[str, Any]:
    return {
        "subsea_pipeline": SUBSEA_PIPELINE_STRUCTURE,
        "ship_hull": SHIP_HULL_STRUCTURE,
        "combined_flat_unique": all_taxonomy_classes(),
        "counts": {
            "subsea_pipeline": len(SUBSEA_PIPELINE_DEFECTS),
            "ship_hull": len(SHIP_HULL_FLAT),
            "combined_unique": len(all_taxonomy_classes()),
        },
        "model_note": (
            "Current default detector (`best_archive.pt`) outputs 19 dataset categories "
            "(see /api/model/classes), not this full taxonomy. To predict these labels end-to-end, "
            "train or load a model whose class head matches this schema (or use per-domain models)."
        ),
        "training_roadmap": training_roadmap(),
    }
