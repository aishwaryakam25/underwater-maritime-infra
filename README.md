# NautiCAI — Underwater Infrastructure Inspection System

<div align="center">

![NautiCAI Banner](https://img.shields.io/badge/NautiCAI-v1.0.4-0A84FF?style=for-the-badge)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit)](https://nauticai-maritime-zpt9twkwjwgvjkjffseclh.streamlit.app/)
[![Model](https://img.shields.io/badge/Model-HuggingFace-FFD21F?style=for-the-badge&logo=huggingface)](https://huggingface.co/aishwarya252525/nauticai-yolov8)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-8A2BE2?style=for-the-badge)](https://ultralytics.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**AI-powered subsea defect detection · Real-time risk scoring · Automated PDF reporting**

*Singapore Maritime AI Systems Pte. Ltd. · Est. 2024*

[Live Demo](https://nauticai-maritime-zpt9twkwjwgvjkjffseclh.streamlit.app/) · [Model Weights](https://huggingface.co/aishwarya252525/nauticai-yolov8) · [Report Issue](https://github.com/aishwaryaV25/nauticAI-maritime/issues)

</div>

---

## Overview

NautiCAI is a production-grade AI inspection system for detecting structural defects in underwater infrastructure — **subsea pipelines, cables, vessel hulls, and port structures** — from images and ROV video feeds.

The system replaces manual inspection workflows that traditionally cost **USD 500,000+ per survey** and take several days, delivering equivalent analysis in **seconds** through computer vision and automated reporting.

> ⚠️ All findings must be verified by a certified marine surveyor before operational decisions are made. This system is advisory in nature.

---

## Key Capabilities

| Capability | Detail |
|---|---|
| **Defect Detection** | 19-class YOLOv8s model — Corrosion, Crack, Fracture, Marine Growth, Biofouling, Scaling, Weld Defect + 12 more |
| **Visibility Enhancement** | CLAHE · Green-Water Filter · Turbidity Correction · Edge Estimator · Marine Snow Simulation |
| **Risk Assessment** | Structural Risk Score (0–100) with Grade A–D classification |
| **Reporting** | Auto-generated 11-section PDF with annotated images, heatmaps, detection logs, and QR verification |
| **Video Support** | Frame-by-frame ROV footage analysis with best-frame selection |
| **Edge Deployment** | NVIDIA Jetson Orin ~55 FPS via TensorRT INT8 |

---

## Model Performance

<div align="center">

| Metric | Score |
|:---:|:---:|
| Precision | **94.2%** |
| Recall | **89.1%** |
| mAP@0.5 | **91.4%** |
| mAP@0.5:0.95 | **78.3%** |
| F1 Score | **91.6%** |
| Inference (GPU) | **28 ms** |

*Trained on ~15,845 images across 6 datasets · 80 epochs · YOLOv8s · NVIDIA RTX 3050 Ti*

</div>

---

## Inference Speed

| Platform | Precision | Latency | Throughput |
|---|---|---|---|
| NVIDIA Jetson AGX Orin 64GB | INT8 TensorRT | ~18 ms | **~55 FPS** |
| NVIDIA Jetson Orin NX 16GB | FP16 TensorRT | ~22 ms | **~45 FPS** |
| RTX 3050 Ti (Development) | FP32 PyTorch | ~28 ms | **~35 FPS** |
| Streamlit Cloud (CPU) | FP32 PyTorch | ~500 ms | **~2 FPS** |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        NautiCAI Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   Input (Image / Video)                                      │
│         │                                                    │
│         ▼                                                    │
│   Visibility Enhancement                                     │
│   ├── CLAHE (Local contrast)                                 │
│   ├── Green-Water Filter (Colour correction)                 │
│   ├── Turbidity Correction (Haze removal)                    │
│   ├── Edge Estimator (Canny overlay)                         │
│   └── Marine Snow Simulation (Robustness)                    │
│         │                                                    │
│         ▼                                                    │
│   YOLOv8s Inference (19 classes)                             │
│         │                                                    │
│         ▼                                                    │
│   Post-Processing                                            │
│   ├── Transparent bounding box annotation                    │
│   ├── Gaussian risk heatmap (plasma colourmap)               │
│   ├── Risk Score (0–100) + Grade (A–D)                       │
│   └── Session state storage                                  │
│         │                                                    │
│         ▼                                                    │
│   Output                                                     │
│   ├── Annotated image display                                │
│   ├── 11-section PDF report (ReportLab)                      │
│   ├── CSV export (Pandas)                                    │
│   └── QR + SHA-256 digital verification                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Severity Classification

| Severity | Colour | Defect Classes | Risk Weight |
|---|---|---|:---:|
| 🔴 **Critical** | Red | Corrosion · Crack · Fracture · Leakage | 25 |
| 🟠 **High** | Orange | Marine Growth · Biofouling · Weld Defect · Anode Damage · CP Failure | 12 |
| 🔵 **Medium** | Blue | Pitting · Paint Damage · Coating Failure · Deformation · Blockage | 6 |
| 🟢 **Low** | Green | Dent · Scaling · Spalling · Disbondment · Foreign Object | 2 |

**Risk Score:** `Score = max(0, min(100, 100 − Σ severity_weights))` · **Grade:** A ≥76 · B ≥51 · C ≥26 · D <26

---

## Inspection Modes

| Tab | Mode | Classes |
|---|---|---|
| 🔍 Infrastructure Scan | General inspection | All 19 |
| 🚢 Hull Inspection | Vessel hull + enhancement comparison | All 19 |
| 🎥 Video Analysis | ROV footage, frame sampling | All 19 |
| 🔩 Pipeline & Subsea | Pipe integrity | Corrosion · Crack · Coating Failure · Pitting · Leakage · Weld Defect · Blockage |
| ⚡ Cable Anomaly | Subsea cable health | Fracture · Deformation · Foreign Object · Biofouling · Marine Growth · Dent |
| 📊 Mission Dashboard | Fleet history + risk trends | — |
| 📄 Report & Export | PDF · CSV · QR | — |
| 🗺️ Roadmap | Feature phases v1.0 → v2.0 | — |

---

## Training Datasets

| # | Dataset | Source | Images |
|---|---|---|:---:|
| 1 | Underwater Pipelines | Roboflow | 1,131 |
| 2 | Subsea Structures | Roboflow | 7,105 |
| 3 | Biofouling Detection | Roboflow | 4,259 |
| 4 | Marine Growth (small) | Roboflow | 70 |
| 5 | Marine Growth (large) | Roboflow | 781 |
| 6 | Ship Hull Defects | Roboflow | 1,187 |
| | **Total** | **6 public datasets** | **~15,845** |

---

## Tech Stack

| Library | Version | Purpose |
|---|---|---|
| `streamlit` | ≥1.28.0 | Web UI — tabs, file uploader, session state |
| `ultralytics` | ≥8.0.0 | YOLOv8s model loading and inference |
| `opencv-python-headless` | ≥4.8.0 | CLAHE, turbidity, edge detection, video capture |
| `Pillow` | ≥10.0.0 | Transparent bounding box annotation |
| `reportlab` | ≥4.0.0 | A4 PDF report generation |
| `scipy` | ≥1.11.0 | Gaussian filter for risk heatmap |
| `matplotlib` | ≥3.7.0 | Severity distribution charts |
| `pandas` | ≥2.0.0 | Detection DataFrame and CSV export |
| `numpy` | ≥1.24.0 | Image array operations |
| `qrcode[pil]` | ≥7.4.2 | QR code + SHA-256 digital verification |
| `huggingface_hub` | latest | Model weights download at runtime |

---

## Project Structure

```
nauticai-maritime/
├── app/
│   ├── streamlit_app.py       # Main application — UI, detection, session state
│   ├── pdf_report.py          # build_pdf() — 11-section ReportLab A4 report
│   ├── severity.py            # Severity classification and colour mapping
│   └── turbidity.py           # Visibility enhancement pipeline
├── scripts/
│   ├── train.py               # YOLOv8s training script (80 epochs)
│   ├── convert_hull.py        # Hull dataset → YOLO format conversion
│   └── merge_datasets.py      # 6 datasets → data/merged/ + data.yaml
├── .streamlit/
│   └── config.toml            # Headless server · dark theme · 200MB upload
├── packages.txt               # Linux system deps (libgl1-mesa-glx)
├── requirements.txt           # Python dependencies
└── README.md
```

> **Note:** `data/`, `*.pt`, and `runs/` are gitignored. Model weights are hosted on [Hugging Face](https://huggingface.co/aishwarya252525/nauticai-yolov8) and auto-downloaded at runtime.

---

## Installation

### Prerequisites
- Python 3.9+
- pip

### Local Setup

```bash
# 1. Clone repository
git clone https://github.com/aishwaryaV25/nauticAI-maritime.git
cd nauticAI-maritime

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run application
streamlit run app/streamlit_app.py
```

The model weights (`best.pt`, 20MB) are automatically downloaded from Hugging Face on first run.

---

## Edge Deployment — NVIDIA Jetson Orin

### Export to TensorRT
```bash
yolo export model=best.pt format=engine device=0
```

### Deployment Pipeline
```
RTSP Stream → GStreamer → OpenCV → TensorRT Inference → Results
```

### Jetson Performance

| Device | Engine | Latency | FPS | Power |
|---|---|---|---|---|
| Jetson AGX Orin 64GB | TensorRT INT8 | 18 ms | ~55 FPS | 15–60W |
| Jetson Orin NX 16GB | TensorRT FP16 | 22 ms | ~45 FPS | 10–25W |

---

## PDF Report Structure

Each generated report contains:

| Section | Content |
|---|---|
| 1. Cover | Mission ID · Vessel · Inspector · Timestamp · Scan Mode |
| 2. Mission Details | Full scan parameter table |
| 3. Executive Summary | Risk Score · Grade · Critical/High counts · Status |
| 4. Annotated Image | Transparent severity-coded bounding boxes |
| 5. Risk Heatmap | Gaussian kernel density map (plasma colourmap) |
| 6. Detection Log | Full table — class · severity · confidence · coordinates · area |
| 7. Severity Chart | Matplotlib bar chart — Critical/High/Medium/Low counts |
| 8. Recommendations | Action items per severity level |
| 9. Edge Deployment | Jetson Orin specs · TensorRT FPS · export command |
| 10. QR Verification | SHA-256 digital fingerprint + scannable URL |
| 11. Disclaimer | Advisory notice — requires certified marine surveyor |

---

## Author

**Aishwarya V**

- GitHub: [@aishwaryaV25](https://github.com/aishwaryaV25)
- Model: [aishwarya252525/nauticai-yolov8](https://huggingface.co/aishwarya252525/nauticai-yolov8)

---

<div align="center">

**NautiCAI · Singapore Maritime AI Systems Pte. Ltd. · Est. 2024**

*"Explore Safer Seas Now"*

</div>
