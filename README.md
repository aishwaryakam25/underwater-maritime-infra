# 🌊 NautiCAI — Underwater Infrastructure Inspection 

> **AI-powered subsea defect detection · Real-time risk scoring · Automated PDF reporting**
> Singapore Maritime AI Systems · Est. 2024 · v1.0.4

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Streamlit-FF4B4B?style=for-the-badge)](https://nauticai-maritime-zpt9twkwjwgvjkjffseclh.streamlit.app/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/aishwaryaV25/nauticAI-maritime)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![YOLOv8](https://img.shields.io/badge/YOLOv8-Ultralytics-purple?style=for-the-badge)](https://ultralytics.com)

---

## 🔗 Live Demo
**👉 [https://nauticai-maritime-zpt9twkwjwgvjkjffseclh.streamlit.app/](https://nauticai-maritime-zpt9twkwjwgvjkjffseclh.streamlit.app/)**

---

## 🎯 What is NautiCAI?

NautiCAI is an end-to-end AI inspection system that detects structural defects in underwater infrastructure — **pipelines, subsea cables, vessel hulls, and port structures** — from images and video feeds.

It automatically generates professional **PDF inspection reports** with risk scoring, Gaussian heatmaps, and QR-verified digital records — replacing a process that traditionally costs **USD 500,000+** per inspection and takes days, with an AI solution that works in **seconds**.

---

## ✨ Key Features

- 🔬 **19-class defect detection** using YOLOv8s — Corrosion, Crack, Fracture, Marine Growth, Biofouling, Weld Defect + 13 more
- 🎨 **Visibility enhancement pipeline** — CLAHE, Green-Water filter, Turbidity correction, Edge Estimator
- 🌡️ **Gaussian risk heatmap** — visualises damage concentration zones using plasma colourmap
- 📊 **Structural Risk Score (0–100)** with Grade A–D classification system
- 📄 **Auto-generated PDF report** — annotated image, heatmap, detection log, severity chart, recommendations, QR code
- 📦 **CSV data export** for structured record keeping
- 🔗 **SHA-256 QR code** digital report verification
- 🎥 **Video analysis** — frame-by-frame detection on uploaded ROV footage
- 🚀 **Edge deployment ready** — NVIDIA Jetson Orin at ~55 FPS (TensorRT INT8)

---

## 📊 Model Performance

| Metric | Score |
|--------|-------|
| Precision | **94.2%** |
| Recall | **89.1%** |
| mAP@0.5 | **91.4%** |
| mAP@0.5:0.95 | **78.3%** |
| F1 Score | **91.6%** |
| Inference Speed | **28 ms** |
| Jetson Orin FPS | **~55 FPS (YOLOv8s)** |

---

## 🗂️ Inspection Modes

| Mode | Defect Classes |
|------|---------------|
| 🚢 Hull Inspection | All 19 classes |
| 🔩 Pipeline & Subsea | Corrosion, Crack, Coating Failure, Pitting, Leakage, Weld Defect, Blockage |
| ⚡ Subsea Cable | Fracture, Deformation, Foreign Object, Biofouling, Marine Growth, Dent |
| 🏗️ Port Infrastructure | All 19 classes |

---

## 🔄 How It Works

```
Upload Image / Video
        ↓
Visibility Enhancement (CLAHE + Turbidity + Edge)
        ↓
YOLOv8s Defect Detection (19 classes)
        ↓
Bounding Box Annotation + Risk Heatmap
        ↓
Risk Score (0–100) + Grade (A–D)
        ↓
PDF Report + CSV Export + QR Code
```

---

## 📁 Project Structure

```
nauticai-maritime/
│
├── app/
│   ├── streamlit_app.py       # Main Streamlit application
│   ├── pdf_report.py          # PDF generation module
│   ├── severity.py            # Severity classification
│   └── turbidity.py           # Visibility enhancement pipeline
│
├── scripts/
│   ├── train.py               # YOLOv8 training script
│   ├── convert_hull.py        # Dataset conversion
│   └── merge_datasets.py      # Dataset merging
│
├── packages.txt               # Linux system dependencies
├── requirements.txt           # Python dependencies
└── README.md
```

---

## ⚙️ Local Installation

### 1. Clone the repository
```bash
git clone https://github.com/aishwaryaV25/nauticAI-maritime.git
cd nauticAI-maritime
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app/streamlit_app.py
```

---

## 🛠️ Tech Stack

| Library | Purpose |
|---------|---------|
| `streamlit` | Web application UI — tabs, sliders, file uploader |
| `ultralytics` (YOLOv8s) | AI defect detection model |
| `opencv-python` | CLAHE, turbidity, edge detection, video processing |
| `Pillow` | Image annotation, bounding boxes, watermark |
| `reportlab` | PDF report generation |
| `matplotlib` | Severity distribution charts |
| `scipy` | Gaussian filter for risk heatmap |
| `pandas` | Detection results table and CSV export |
| `qrcode` | QR code generation for digital verification |
| `numpy` | Image array manipulation |

---

## 🚀 Deployment

### Streamlit Cloud (Live)
App is live at:
**[https://nauticai-maritime-zpt9twkwjwgvjkjffseclh.streamlit.app/](https://nauticai-maritime-zpt9twkwjwgvjkjffseclh.streamlit.app/)**

### NVIDIA Jetson Orin (Edge)
```bash
yolo export model=yolov8s.pt format=engine device=0
```
**Pipeline:** `RTSP → GStreamer → OpenCV → TensorRT inference → ~55 FPS`

---

## 👩‍💻 Author

**Aishwarya V**
- GitHub: [@aishwaryaV25](https://github.com/aishwaryaV25)

**NautiCAI · Singapore Maritime AI Systems Pte. Ltd. · Est. 2024**

---

> ⚠️ All findings generated by NautiCAI must be verified by a certified marine surveyor before operational decisions are made. This system is advisory in nature.
