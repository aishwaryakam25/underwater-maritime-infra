import os
import shutil
from pathlib import Path
import random

project_root = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly"
fish_download_path = input("Enter the path where fish images were downloaded: ")
negative_samples_dir = os.path.join(project_root, "fish_negative_samples")

images_dir = os.path.join(negative_samples_dir, "images")
labels_dir = os.path.join(negative_samples_dir, "labels")
os.makedirs(images_dir, exist_ok=True)
os.makedirs(labels_dir, exist_ok=True)

print(f"Setting up negative samples in: {negative_samples_dir}")

fish_image_extensions = ['.jpg', '.jpeg', '.png', '.bmp']
fish_images = []

for root, dirs, files in os.walk(fish_download_path):
    for file in files:
        if any(file.lower().endswith(ext) for ext in fish_image_extensions):
            fish_images.append(os.path.join(root, file))

print(f"\nFound {len(fish_images)} fish images")

copied_count = 0
for img_path in fish_images:
    try:
        img_name = os.path.basename(img_path)
        new_img_name = f"fish_negative_{copied_count:05d}{os.path.splitext(img_name)[1]}"
        new_img_path = os.path.join(images_dir, new_img_name)
        shutil.copy2(img_path, new_img_path)
        label_name = f"fish_negative_{copied_count:05d}.txt"
        label_path = os.path.join(labels_dir, label_name)
        with open(label_path, 'w', encoding='utf-8') as f:
            pass
        copied_count += 1
        if copied_count % 100 == 0:
            print(f"Processed {copied_count} fish images...")
    except Exception as e:
        print(f"Error: {e}")

print(f"\nSuccessfully prepared {copied_count} fish images as negative samples")

all_images = list(Path(images_dir).glob('*'))
random.shuffle(all_images)
split_idx = int(len(all_images) * 0.8)
train_images = all_images[:split_idx]
val_images = all_images[split_idx:]

print(f"\nTraining: {len(train_images)} images")
print(f"Validation: {len(val_images)} images")

train_images_dir = os.path.join(negative_samples_dir, "train", "images")
train_labels_dir = os.path.join(negative_samples_dir, "train", "labels")
val_images_dir = os.path.join(negative_samples_dir, "val", "images")
val_labels_dir = os.path.join(negative_samples_dir, "val", "labels")

for d in [train_images_dir, train_labels_dir, val_images_dir, val_labels_dir]:
    os.makedirs(d, exist_ok=True)

for img in train_images:
    base_name = img.stem
    shutil.move(str(img), os.path.join(train_images_dir, img.name))
    label_file = Path(labels_dir) / f"{base_name}.txt"
    if label_file.exists():
        shutil.move(str(label_file), os.path.join(train_labels_dir, label_file.name))

for img in val_images:
    base_name = img.stem
    shutil.move(str(img), os.path.join(val_images_dir, img.name))
    label_file = Path(labels_dir) / f"{base_name}.txt"
    if label_file.exists():
        shutil.move(str(label_file), os.path.join(val_labels_dir, label_file.name))

shutil.rmtree(images_dir)
shutil.rmtree(labels_dir)

print("\nDone! Negative samples ready.")