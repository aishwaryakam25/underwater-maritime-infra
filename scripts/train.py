"""
NautiCAI — YOLOv8s Training Script
Dataset: 15,845 images across 6 public datasets
Classes: 19 (10 subsea + 9 hull)
GPU: NVIDIA RTX 3050 Ti
"""
from ultralytics import YOLO

import torch
model = YOLO("yolov8s.pt")  # auto-downloads on first run

# Use GPU if available, else CPU
device = 0 if torch.cuda.is_available() else "cpu"

results = model.train(
    data="data/merged/data.yaml",
    epochs=80,
    imgsz=640,
    batch=16,           # reduce to 8 if memory error
    lr0=0.01,
    momentum=0.937,
    weight_decay=0.0005,
    warmup_epochs=3,
    workers=0,          # fixes Windows multiprocessing error

    # ── Underwater-specific augmentation ──────────────────────────────────
    hsv_h=0.015,        # hue shift — simulates water colour variation
    hsv_s=0.7,          # saturation — simulates green/blue cast
    hsv_v=0.4,          # value — simulates depth light attenuation
    degrees=10.0,       # rotation
    translate=0.1,
    scale=0.5,
    flipud=0.3,         # valid underwater — no gravity cue
    fliplr=0.5,
    mosaic=1.0,         # handles partial occlusion by marine growth
    mixup=0.1,          # improves turbidity robustness

    project="runs/detect",
    name="nauticai_v1",
    exist_ok=True,
    patience=20,
    device=device,
)

print("✅ Training complete!")
print("Best model: runs/detect/nauticai_v1/weights/best.pt")