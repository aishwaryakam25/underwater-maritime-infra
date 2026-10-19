"""Inspection PDF audit trail — weights hash, thresholds, preprocessing (survey-style provenance)."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

NAUTICAI_API_VERSION = "1.0.5"


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def seal_inspection_provenance(provenance: dict) -> dict:
    """Add ``provenance_digest_sha256`` over all other keys."""
    body = {k: provenance[k] for k in sorted(provenance.keys()) if k != "provenance_digest_sha256"}
    out = dict(provenance)
    out["provenance_digest_sha256"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return out


def collect_inspection_provenance(
    *,
    mission_id: str,
    mode: str,
    conf_thr: float,
    iou_thr: float,
    use_clahe: bool,
    clahe_clip: float,
    use_green: bool,
    use_edge: bool,
    turbidity_in: float,
    corr_turb: bool,
    marine_snow: bool,
    sev_filter: str | None = None,
    sample_stride: int | None = None,
    weights_path_override: Path | str | None = None,
    model_key_override: str | None = None,
    model_display_override: str | None = None,
    official_19_only_override: bool | None = None,
) -> dict:
    """Snapshot of inference configuration for PDF audit trail."""
    from severity import official_19_only_outputs
    from detection import get_active_model_key, get_model_name, get_resolved_weights_path

    repo_root = Path(__file__).resolve().parent.parent

    if weights_path_override is not None:
        wpath = Path(weights_path_override).resolve() if weights_path_override else None
        if wpath is not None and not wpath.is_file():
            wpath = None
    else:
        wpath = get_resolved_weights_path()
        if wpath is not None:
            wpath = Path(wpath).resolve()

    rel = None
    if wpath is not None:
        try:
            rel = str(wpath.relative_to(repo_root.resolve()))
        except ValueError:
            rel = str(wpath)

    sha = _sha256_file(wpath) if wpath else None
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    iso = utc_now.strftime("%Y-%m-%dT%H:%M:%SZ")

    size_b = None
    try:
        if wpath is not None and wpath.is_file():
            size_b = wpath.stat().st_size
    except OSError:
        pass

    m_key = model_key_override if model_key_override is not None else get_active_model_key()
    m_disp = model_display_override if model_display_override is not None else get_model_name()
    off19 = (
        official_19_only_override
        if official_19_only_override is not None
        else official_19_only_outputs()
    )

    return seal_inspection_provenance(
        {
            "schema_version": 1,
            "mission_id": mission_id,
            "generated_at_utc": iso,
            "api_version": NAUTICAI_API_VERSION,
            "scan_mode": mode,
            "model_key": m_key,
            "model_weights_display_name": m_disp,
            "model_weights_filename": wpath.name if wpath else None,
            "model_weights_relative_path": rel,
            "weights_sha256": sha,
            "weights_size_bytes": size_b,
            "conf_threshold": round(float(conf_thr), 6),
            "iou_threshold": round(float(iou_thr), 6),
            "use_clahe": bool(use_clahe),
            "clahe_clip": round(float(clahe_clip), 6),
            "use_green_channel_boost": bool(use_green),
            "use_edge_estimator": bool(use_edge),
            "turbidity_in": round(float(turbidity_in), 6),
            "correct_turbidity": bool(corr_turb),
            "marine_snow": bool(marine_snow),
            "official_19_only_outputs": off19,
            "severity_filter": sev_filter,
            "video_sample_stride_frames": sample_stride,
        }
    )
