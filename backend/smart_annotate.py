import cv2
import numpy as np
from PIL import Image as PILImage

SEV_COLOR = {
    "Critical": (0, 0, 220),
    "High": (0, 100, 255),
    "Medium": (0, 180, 255),
    "Low": (50, 200, 50),
    "Unknown": (150, 150, 150),
}

def annotate_image_smart(image, detections):
    """Annotate with collision-avoiding label placement"""
    if not detections:
        return image
    
    is_pil = isinstance(image, PILImage.Image)
    if is_pil:
        img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    else:
        img = image.copy()
    
    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX
    placed_rects = []
    
    for rank, d in enumerate(detections):
        x1 = d.get("x1", 0)
        y1 = d.get("y1", 0)
        x2 = d.get("x2", w)
        y2 = d.get("y2", h)
        sev = d.get("severity", "Unknown")
        color = SEV_COLOR.get(sev, SEV_COLOR["Unknown"])
        cls = d.get("cls", "unknown")
        conf = d.get("conf", 0)
        
        # Draw box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
        
        # Prepare label
        label = f"[{str(rank+1).zfill(2)}] {cls} {int(conf*100)}%"
        box_w = max(x2 - x1, 1)
        fs = min(0.5, max(0.3, box_w / 200.0))
        (lw, lh), _ = cv2.getTextSize(label, font, fs, 1)
        
        # Try candidate positions: above, below, right, left
        candidates = [
            (x1, y1 - lh - 8, "above"),
            (x1, y2 + 4, "below"),
            (x2 + 4, y1, "right"),
            (x1 - lw - 8, y1, "left"),
        ]
        
        chosen = None
        for lx, ly, pos in candidates:
            # Check bounds
            if lx < 0 or ly < 0 or lx + lw > w or ly + lh > h:
                continue
            # Check collision with existing labels
            label_rect = (lx, ly, lx + lw + 6, ly + lh + 6)
            if not any(rects_overlap(label_rect, pr) for pr in placed_rects):
                chosen = (lx, ly)
                placed_rects.append(label_rect)
                break
        
        # Fallback: clamp to image
        if chosen is None:
            chosen = (min(x1, w - lw - 8), max(0, y1 - lh - 8))
        
        lx, ly = chosen
        # Draw label background
        cv2.rectangle(img, (lx, ly), (lx + lw + 6, ly + lh + 6), color, -1)
        cv2.putText(img, label, (lx + 3, ly + lh), font, fs, (255, 255, 255), 1, cv2.LINE_AA)
    
    if is_pil:
        return PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return img

def rects_overlap(a, b):
    """Check if two rects (x1,y1,x2,y2) overlap"""
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])