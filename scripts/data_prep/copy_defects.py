import os, shutil
BASE = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\sonar_detect_dataset"
OUTPUT = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\sonar_defect_images"
os.makedirs(OUTPUT, exist_ok=True)
copied = 0
for split in ["train", "val"]:
    label_dir = os.path.join(BASE, "labels", split)
    image_dir = os.path.join(BASE, "images", split)
    if not os.path.exists(label_dir):
        continue
    for lf in sorted(os.listdir(label_dir)):
        if not lf.endswith(".txt") or "cache" in lf:
            continue
        if os.path.getsize(os.path.join(label_dir, lf)) == 0:
            continue
        stem = os.path.splitext(lf)[0]
        for ext in [".png", ".jpg"]:
            ip = os.path.join(image_dir, stem + ext)
            if os.path.exists(ip):
                shutil.copy2(ip, os.path.join(OUTPUT, split + "_" + stem + ext))
                copied += 1
                break
print(f"Copied {copied} defect images to {OUTPUT}")