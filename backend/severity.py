"""
NautiCAI — Severity mapping for detected classes.
"""

SEVERITY_MAP = {
    "Corrosion": "Critical", "Crack": "Critical", "Fracture": "Critical", "Leakage": "Critical",
    "Marine Growth": "High", "Biofouling": "High", "Weld Defect": "High", "Anode Damage": "High",
    "CP Failure": "High", "Pitting": "Medium", "Paint Damage": "Medium", "Coating Failure": "Medium",
    "Deformation": "Medium", "Blockage": "Medium", "Dent": "Low", "Scaling": "Low",
    "Spalling": "Low", "Disbondment": "Low", "Foreign Object": "Low",
    "Free Span": "Critical", "No Defect": "Low",
}

CLASS_REMAP = {
    "pipeline": "Corrosion", "concrete": "Marine Growth", "hull": "Paint Damage",
    "propeller": "Biofouling", "anode": "Anode Damage", "leakage": "Leakage",
    "anomaly": "Crack", "biofouling": "Biofouling", "bilge_keel": "Coating Failure",
    "draft_mark": "Paint Damage", "ropeguard": "Foreign Object", "rudder": "Deformation",
    "sea_chest": "Blockage", "thruster_blades": "Weld Defect", "thruster_grating": "Disbondment",
    "flange": "Weld Defect", "buoy": "Foreign Object", "bend_restrictor": "Deformation",
    "pipe_coupling": "Coating Failure", "free_span": "Free Span", "healthy": "No Defect",
}

SEV_WEIGHT = {"Critical": 25, "High": 12, "Medium": 6, "Low": 2}

DEFECT_CLASSES = [
    "Corrosion", "Crack", "Marine Growth", "Biofouling", "Paint Damage", "Pitting",
    "Weld Defect", "Anode Damage", "Coating Failure", "Dent", "Deformation", "Fracture",
    "Spalling", "Scaling", "Disbondment", "CP Failure", "Leakage", "Blockage", "Foreign Object",
    "Free Span", "No Defect",
]

PIPELINE_DEFECTS = ["Corrosion", "Crack", "Coating Failure", "Pitting", "Leakage", "Weld Defect", "Blockage"]
CABLE_DEFECTS = ["Fracture", "Deformation", "Foreign Object", "Biofouling", "Marine Growth", "Dent"]


def compute_risk(dets: list) -> int:
    return max(0, min(100, 100 - sum(SEV_WEIGHT.get(d["severity"], 0) for d in dets)))


def score_to_grade(s: int) -> str:
    if s >= 76:
        return "A"
    elif s >= 51:
        return "B"
    elif s >= 26:
        return "C"
    return "D"
