import os, shutil, random
from pathlib import Path
from PIL import Image
from ultralytics import YOLO

BASE = "C:/Users/RAMNATH VENKAT/Documents/nauticai-underwater-anomaly"
SUBPIPE = f"{BASE}/SubPipe/DATA"
OUT = f"{BASE}/sonar_detect_dataset"

for d in ["images/train","images/val","labels/train","labels/val"]:
    os.makedirs(f"{OUT}/{d}", exist_ok=True)

all_items = []
for chunk in sorted(os.listdir(SUBPIPE)):
    chunk_path = f"{SUBPIPE}/{chunk}"
    if not os.path.isdir(chunk_path):
        continue
    for freq in ["SSS_HF_images", "SSS_LF_images"]:
        img_dir = f"{chunk_path}/{freq}/Image"
        label_dir = f"{chunk_path}/{freq}/YOLO_Annotation"
        if not os.path.exists(img_dir):
            continue
        for f in os.listdir(img_dir):
            if f.endswith(('.pbm','.png','.jpg')):
                stem = Path(f).stem
                label = f"{label_dir}/{stem}.txt"
                has_label = os.path.exists(label)
                all_items.append({"img": f"{img_dir}/{f}", "label": label if has_label else None, "name": f"{chunk}_{freq}_{stem}"})

print(f"Total SSS images: {len(all_items)}")
labeled = sum(1 for x in all_items if x["label"])
print(f"With YOLO labels: {labeled}")

random.seed(42)
random.shuffle(all_items)
split = int(len(all_items) * 0.85)
sets = {"train": all_items[:split], "val": all_items[split:]}

for split_name, items in sets.items():
    ok = 0
    for item in items:
        dst_img = f"{OUT}/images/{split_name}/{item['name']}.png"
        try:
            img = Image.open(item["img"]).convert("RGB")
            img.save(dst_img)
            ok += 1
        except:
            continue
        if item["label"]:
            shutil.copy2(item["label"], f"{OUT}/labels/{split_name}/{item['name']}.txt")
    print(f"{split_name}: {ok} images converted")

with open(f"{OUT}/data.yaml", "w") as f:
    f.write(f"path: {OUT}\ntrain: images/train\nval: images/val\nnc: 1\nnames:\n  0: pipeline\n")

print("Starting training...")
model = YOLO("yolov8m.pt")
model.train(data=f"{OUT}/data.yaml", epochs=100, batch=4, imgsz=640, project=f"{BASE}/runs", name="sonar_pipeline_detect", patience=20, save=True, plots=True, flipud=0.5, fliplr=0.5, hsv_h=0.0, hsv_s=0.1, hsv_v=0.3)