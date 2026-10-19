import sys
from ultralytics import YOLO
from pathlib import Path
import cv2
import json

# Usage: python predict.py image.jpg
if len(sys.argv) < 2:
    print("Usage: python predict.py <image_path>")
    sys.exit(1)

image_path = sys.argv[1]
model_path = Path("weights/best.pt") if Path("weights/best.pt").exists() else Path("yolov8s.pt")
model = YOLO(str(model_path))

results = model(image_path)

# Save annotated image
annotated = results[0].plot()
output_img = Path(image_path).stem + "_annotated.jpg"
cv2.imwrite(output_img, annotated)

# Save JSON
detections = []
for r in results:
    for box in r.boxes:
        detections.append({
            "class": int(box.cls[0]),
            "confidence": float(box.conf[0]),
            "bbox": [float(x) for x in box.xyxy[0].tolist()]
        })
output_json = Path(image_path).stem + "_detections.json"
with open(output_json, "w") as f:
    json.dump(detections, f, indent=2)

print(f"Annotated image saved as {output_img}")
print(f"Detections saved as {output_json}")