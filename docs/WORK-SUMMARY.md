# NautiCAI — Work Summary

**Prepared by:** NautiCAI Engineering
**Date:** 13 August 2026
**Project:** NautiCAI — Underwater Infrastructure Inspection System

---

## 1. What the system does

An AI inspection platform that detects structural defects on underwater assets —
**subsea pipelines, cables, vessel hulls and port structures** — from still images and ROV
video, then scores risk and generates survey-ready reports automatically.

Input (image / video) → visibility enhancement → deep-vision detection → severity &
risk scoring → annotated output + PDF / CSV report.

All findings are advisory and flagged for verification by a certified marine surveyor.

---

## 2. Delivered so far

### Detection engine
- Multi-model detection service with **runtime model switching** (`/api/models`, `/api/models/switch`) — the active model persists across restarts.
- Purpose-trained checkpoints for different survey types (general 19-class, ship-hull taxonomy, subsea-pipeline taxonomy, plus focused models for corrosion, cracks, debris, paint/fouling and biofouling).
- **Defect taxonomies** defined as config-driven YAMLs — 26 ship-hull classes (`configs/ship_hull_defects.yaml`), 18 subsea-pipeline classes (`configs/subsea_pipeline_defects.yaml`), and the official 19-label severity table (`configs/nauticai_official_19.yaml`).
- **False-positive filtering** (`backend/detection_filter.py`): per-class confidence floors, box-size sanity limits, and marine-life (fish) suppression so live organisms are not reported as defects.
- Asset-vs-defect separation, severity filtering, and a Critical/High/Medium/Low severity model driving a 0–100 risk score with an A–D grade.

### Visibility enhancement
CLAHE local contrast, green-water colour correction, turbidity/haze removal, edge estimation, and marine-snow simulation for robustness testing.

### Backend API (FastAPI)
~20 endpoints covering single and batch detection, video detection and annotated-video export, image enhancement, CSV export, PDF report generation (image / batch / video), model and taxonomy introspection, health checks, sign-up capture, and WhatsApp delivery of alerts and reports.

Extended modules: sonar analysis and combined sonar+vision analysis, weld inspection, ABS/DNV-style report generation, biofouling CO₂ impact, corrosion-velocity modelling, environmental risk scoring, acoustic-emission classification, marine-growth classification, and a blockchain-style audit trail.

### Frontend (React)
14-tab operator console: Anomaly Scan, Hull Inspect, Video Analysis, Pipeline, Sub-sea Cable, Deadlines, Dashboard, Mission Memory, Weld Inspect, Compliance, Zero-Shot, Sonar Analysis, Combined, Roadmap.
Includes **3D hull visualisation** with defect overlays, live video analysis with tracking, 2D pipeline mapping, and per-tab upload state so operators can work several assets in parallel.

### Reporting
- Branded **11-section A4 PDF** (cover, mission details, executive summary, annotated image, risk heatmap, detection log, severity chart, recommendations, edge-deployment specs, QR + SHA-256 verification, disclaimer).
- Batch and video report variants.
- **Inspection provenance** capture (model, weights, thresholds, environment) embedded in reports for auditability.

### Deployment & ops
Dockerised backend and frontend with `docker-compose` and nginx; deploy paths documented and scripted for **AWS** and **GCP**; Streamlit Cloud demo build; marketing/landing site; and health-check scripts (`scripts/check_stack_health.py`, `scripts/tomorrow-demo-health.ps1`) to verify the full stack before a demo.

---

## 3. Currently in progress

| Item | Status |
|---|---|
| **Diver-style hull-cleaning report pack** (`app/diver_style_hull_pdf.py`) — conventional hull-cleaning / propeller-polishing job PDF: cover, index, vessel block, scope, fouling grid, photo sections by hull zone, closing certificates | Built, being wired through `/api/report/pdf/batch` via a `report_style` switch |
| **Taxonomy-model passthrough** — hull/subsea models can now return their richer class sets (barnacles, algae, mussels…) instead of being collapsed to the 19 official labels | Working, under test |
| **Auto-registration of local weights** — any `weights/*.pt` becomes a selectable model with no code change | Working |
| **3D hull viewer rebuild** — more realistic vessel geometry, lighting and deck/superstructure detail | In progress |
| Clickable company URL + job metadata (IMO, place, activity, job number) in report footers | Working |

---

## 4. Model & performance snapshot

Trained on ~15,845 images across 6 public datasets (underwater pipelines, subsea structures, biofouling, marine growth, ship-hull defects).

| Metric | Value |
|---|---|
| Precision | 94.2% |
| Recall | 89.1% |
| mAP@0.5 | 91.4% |
| mAP@0.5:0.95 | 78.3% |
| Inference (GPU, FP32) | ~28 ms (~35 FPS) |
| Jetson AGX Orin (INT8 TensorRT) | ~18 ms (~55 FPS) |

Edge path validated via TensorRT export for NVIDIA Jetson Orin.

---

## 5. Suggested next steps

1. Finish and commit the diver-style hull report pack; review the layout against a real customer job PDF.
2. Validate the hull/subsea taxonomy models on real client footage and tune the false-positive filter thresholds per class.
3. Complete the 3D hull viewer work and land it.
4. Reduce weight sprawl in `weights/` — pick the shipping checkpoints per survey type and archive the rest.
5. Full end-to-end demo rehearsal on the deployed stack using the health-check scripts.

---

*Happy to walk through any section in more detail, or demo the live stack.*
