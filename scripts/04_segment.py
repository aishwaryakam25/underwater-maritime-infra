"""
=============================================================================
04_segment.py — YOLOv8-seg: pixel-level segmentation masks
=============================================================================
Replaces bounding boxes with actual pixel masks.
Mask data is used to:
  1. Draw accurate defect outlines on images
  2. Calculate real defect area in pixels
  3. Map precise location onto 2D/3D pipeline model
=============================================================================
"""

import cv2
import numpy as np
import base64
import json
from pathlib import Path
from ultralytics import YOLO


CLASSES = [
    "corrosion", "crack", "biofouling", "coating_damage",
    "anode_depletion", "marine_growth", "dent",
    "weld_defect", "leak", "free_span",
]

SEV_MAP = {
    "corrosion":       "Critical",
    "crack":           "Critical",
    "leak":            "Critical",
    "weld_defect":     "High",
    "anode_depletion": "High",
    "free_span":       "High",
    "coating_damage":  "Medium",
    "dent":            "Medium",
    "marine_growth":   "Low",
    "biofouling":      "Low",
}

SEV_COLOR_BGR = {
    "Critical": (0,   0,   239),   # red
    "High":     (0,   113, 249),   # orange
    "Medium":   (11,  158, 245),   # yellow
    "Low":      (78,  197, 34),    # green
}


def pil_to_b64(img_bgr: np.ndarray) -> str:
    _, buf = cv2.imencode(".jpg", img_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buf).decode()


def run_segmentation(
    image_path: str,
    weights:    str = "weights/best_seg.pt",
    conf_thr:   float = 0.25,
    iou_thr:    float = 0.45,
    img_w:      int = 1280,
) -> dict:
    """
    Run YOLOv8-seg on an image.
    Returns detections with:
      - bbox (xmin, ymin, xmax, ymax)
      - mask_polygon (contour points for frontend rendering)
      - mask_area_px (real pixel area of defect)
      - centroid (cx, cy) of mask
      - pipe_pos (0-1 along pipe length from centroid)
      - angle (0-1 around circumference from centroid)
    """
    model = YOLO(weights)
    img   = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"Cannot load: {image_path}")

    h, w = img.shape[:2]
    results = model.predict(img, conf=conf_thr, iou=iou_thr, verbose=False)
    result  = results[0]

    annotated = img.copy()
    detections = []

    if result.masks is not None:
        for i, (box, mask) in enumerate(zip(result.boxes, result.masks)):
            cls_id   = int(box.cls[0])
            cls_name = CLASSES[cls_id] if cls_id < len(CLASSES) else f"class_{cls_id}"
            conf     = float(box.conf[0])
            severity = SEV_MAP.get(cls_name, "Unknown")
            color    = SEV_COLOR_BGR.get(severity, (128, 128, 128))

            # bbox
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            # mask as binary array
            mask_data = mask.data[0].cpu().numpy()
            mask_bin  = (cv2.resize(mask_data, (w, h)) > 0.5).astype(np.uint8)

            # contours for polygon
            contours, _ = cv2.findContours(mask_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # simplify polygon for frontend
            polygon = []
            if contours:
                cnt = max(contours, key=cv2.contourArea)
                eps = 0.005 * cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, eps, True)
                polygon = approx.reshape(-1, 2).tolist()

            # real area
            mask_area = int(mask_bin.sum())

            # centroid
            M  = cv2.moments(mask_bin)
            cx = int(M["m10"] / M["m00"]) if M["m00"] > 0 else (x1 + x2) // 2
            cy = int(M["m01"] / M["m00"]) if M["m00"] > 0 else (y1 + y2) // 2

            # pipe coordinates from centroid
            pipe_pos = cx / w
            angle    = cy / h

            # draw filled mask with transparency
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [np.array(polygon, dtype=np.int32)], color)
            cv2.addWeighted(overlay, 0.35, annotated, 0.65, 0, annotated)

            # draw contour
            cv2.drawContours(annotated, contours, -1, color, 2)

            # label
            label = f"{cls_name} {conf:.0%}"
            cv2.rectangle(annotated, (x1, y1 - 20), (x1 + len(label) * 8, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            detections.append({
                "id":           i,
                "cls":          cls_name,
                "conf":         round(conf, 4),
                "severity":     severity,
                "bbox": {
                    "xmin": x1, "ymin": y1,
                    "xmax": x2, "ymax": y2,
                },
                "mask_polygon": polygon,   # list of [x,y] points
                "mask_area_px": mask_area, # real defect area in pixels
                "centroid":     {"cx": cx, "cy": cy},
                "pipe_pos":     round(pipe_pos, 4),  # 0-1 along pipe
                "angle":        round(angle, 4),     # 0-1 around pipe
            })

    else:
        # fallback to bbox-only if no masks
        for i, box in enumerate(result.boxes):
            cls_id   = int(box.cls[0])
            cls_name = CLASSES[cls_id] if cls_id < len(CLASSES) else f"class_{cls_id}"
            conf     = float(box.conf[0])
            severity = SEV_MAP.get(cls_name, "Unknown")
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            detections.append({
                "id":           i,
                "cls":          cls_name,
                "conf":         round(conf, 4),
                "severity":     severity,
                "bbox":         {"xmin":x1,"ymin":y1,"xmax":x2,"ymax":y2},
                "mask_polygon": [],
                "mask_area_px": (x2-x1)*(y2-y1),
                "centroid":     {"cx":cx,"cy":cy},
                "pipe_pos":     round(cx/w, 4),
                "angle":        round(cy/h, 4),
            })

    return {
        "annotated_b64": pil_to_b64(annotated),
        "detections":    detections,
        "total":         len(detections),
        "img_width":     w,
        "img_height":    h,
    }
