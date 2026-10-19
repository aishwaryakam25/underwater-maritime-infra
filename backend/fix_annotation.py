path = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\backend\detection.py"

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

old = '''        cv2.rectangle(
            canvas,
            (tx1, ty_top),
            (tx1 + tw + pad_x * 2, ty_bl),
            (0, 0, 0),
            -1,
        )
        cv2.putText(
            canvas,
            tag,
            (tx1 + pad_x, ty_bl - pad_y),
            font,
            tag_s,
            color,
            1,
            cv2.LINE_AA,
        )'''

new = '''        # Draw label above the box: "ClassName 85%"
        label = f"{cls}  {conf*100:.0f}%"
        label_scale = 0.48
        (lw, lh), _ = cv2.getTextSize(label, font, label_scale, 1)
        lx1 = x1
        ly1 = max(0, y1 - lh - 6)
        cv2.rectangle(canvas, (lx1, ly1), (lx1 + lw + 6, ly1 + lh + 6), color, -1)
        cv2.putText(canvas, label, (lx1 + 3, ly1 + lh + 2), font, label_scale, (255, 255, 255), 1, cv2.LINE_AA)'''

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Done! Label will now appear above each bounding box.")
else:
    print("Pattern not found — check indentation in detection.py")