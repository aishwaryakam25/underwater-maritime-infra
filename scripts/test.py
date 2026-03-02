"""
YOLOv8 Model Evaluation Script for NautiCAI
Evaluates trained model on validation set and prints mAP, precision, recall.
"""
from ultralytics import YOLO
import sys
from pathlib import Path

# Usage: python scripts/test.py [model_path] [data_yaml]
def main():
    model_path = sys.argv[1] if len(sys.argv) > 1 else "runs/detect/nauticai_v1/weights/best.pt"
    data_yaml = sys.argv[2] if len(sys.argv) > 2 else "data/merged/data.yaml"
    model = YOLO(model_path)
    results = model.val(data=data_yaml)
    print("\n--- Evaluation Results ---")
    print(f"Model: {model_path}")
    print(f"Data: {data_yaml}")
    print(f"mAP@0.5: {results.box.map50:.4f}")
    print(f"mAP@0.5:0.95: {results.box.map:.4f}")
    print(f"Precision: {results.box.precision:.4f}")
    print(f"Recall: {results.box.recall:.4f}")
    print("-------------------------\n")

if __name__ == "__main__":
    main()
