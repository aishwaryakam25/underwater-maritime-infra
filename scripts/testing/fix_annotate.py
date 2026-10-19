import re

new_func = '''def annotate_image(image, detections):
    if not detections:
        return image

    from PIL import Image as PILImage
    is_pil = isinstance(image, PILImage.Image)
    if is_pil:
        img = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2BGR)
    else:
        img = image.copy()

    h, w = img.shape[:2]
    font = cv2.FONT_HERSHEY_SIMPLEX

    for rank, d in enumerate(detections):
        bbox = d.get("bbox") or d.get("bounding_box") or {}
        x1 = int(bbox.get("xmin", d.get("x1", 0)))
        y1 = int(bbox.get("ymin", d.get("y1", 0)))
        x2 = int(bbox.get("xmax", d.get("x2", w)))
        y2 = int(bbox.get("ymax", d.get("y2", h)))
        sev = d.get("severity", "Unknown")
        color = SEV_COLOR.get(sev, SEV_COLOR["Unknown"])
        cls = d.get("cls") or d.get("class_name") or "unknown"
        conf = float(d.get("conf", 0))

        # Draw box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # Auto font scale based on box width
        box_w = max(x2 - x1, 1)
        label = f"[{str(rank+1).zfill(2)}] {cls} {conf*100:.0f}%"
        fs = min(0.5, max(0.3, box_w / 200.0))
        (lw, lh), _ = cv2.getTextSize(label, font, fs, 1)

        # Place label above box; fall back to inside top if no room
        if y1 - lh - 6 >= 0:
            ly = y1 - 4
            bg_y1, bg_y2 = ly - lh - 2, ly + 3
        else:
            ly = y1 + lh + 4
            bg_y1, bg_y2 = y1, y1 + lh + 6

        # Clamp label to image width
        lx = min(x1, w - lw - 8)
        cv2.rectangle(img, (lx, bg_y1), (lx + lw + 6, bg_y2), color, -1)
        cv2.putText(img, label, (lx + 3, ly), font, fs, (255, 255, 255), 1, cv2.LINE_AA)

    if is_pil:
        return PILImage.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    return img
'''

content = open('backend/detection.py').read()
pattern = r'def annotate_image\(image, detections\):.*?(?=\ndef |\Z)'
new_content = re.sub(pattern, new_func, content, flags=re.DOTALL)
open('backend/detection.py', 'w').write(new_content)
print('Done!')