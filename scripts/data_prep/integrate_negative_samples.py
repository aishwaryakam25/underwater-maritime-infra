import os
import shutil
import yaml
from pathlib import Path

project_root = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly"

existing_dataset = os.path.join(project_root, "sonar_defect_images")
fish_negatives = os.path.join(project_root, "fish_negative_samples")
combined_dataset = os.path.join(project_root, "combined_dataset_with_negatives")
os.makedirs(combined_dataset, exist_ok=True)

print("Creating combined dataset with positive and negative samples...")

for split in ['train', 'val']:
    for subdir in ['images', 'labels']:
        os.makedirs(os.path.join(combined_dataset, split, subdir), exist_ok=True)

def copy_dataset(source_base, dest_base, prefix):
    counts = {'train': 0, 'val': 0}
    for split in ['train', 'val']:
        source_images = os.path.join(source_base, 'images', split) if 'sonar' in source_base else os.path.join(source_base, split, 'images')
        source_labels = os.path.join(source_base, 'labels', split) if 'sonar' in source_base else os.path.join(source_base, split, 'labels')
        dest_images = os.path.join(dest_base, split, 'images')
        dest_labels = os.path.join(dest_base, split, 'labels')
        
        if not os.path.exists(source_images):
            print(f"Warning: {source_images} not found, skipping...")
            continue
            
        for img_file in Path(source_images).glob('*'):
            if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
                new_name = f"{prefix}_{counts[split]:05d}{img_file.suffix}"
                shutil.copy2(img_file, os.path.join(dest_images, new_name))
                label_file = Path(source_labels) / f"{img_file.stem}.txt"
                if label_file.exists():
                    shutil.copy2(label_file, os.path.join(dest_labels, f"{prefix}_{counts[split]:05d}.txt"))
                counts[split] += 1
    return counts

print("\n1. Copying existing defect detection images (positive samples)...")
positive_counts = copy_dataset(existing_dataset, combined_dataset, "defect")
print(f"   Train: {positive_counts['train']} images")
print(f"   Val: {positive_counts['val']} images")

print("\n2. Copying fish negative samples...")
negative_counts = copy_dataset(fish_negatives, combined_dataset, "fish_neg")
print(f"   Train: {negative_counts['train']} images")
print(f"   Val: {negative_counts['val']} images")

total_train = positive_counts['train'] + negative_counts['train']
total_val = positive_counts['val'] + negative_counts['val']

print(f"\n{'='*60}")
print(f"COMBINED DATASET SUMMARY")
print(f"{'='*60}")
print(f"Training:   {total_train} images ({positive_counts['train']} positive + {negative_counts['train']} negative)")
print(f"Validation: {total_val} images ({positive_counts['val']} positive + {negative_counts['val']} negative)")
print(f"Total:      {total_train + total_val} images")
print(f"{'='*60}")

yaml_config = {
    'path': combined_dataset,
    'train': 'train/images',
    'val': 'val/images',
    'names': {0: 'pipeline'},
    'nc': 1
}

yaml_path = os.path.join(combined_dataset, 'dataset.yaml')
with open(yaml_path, 'w', encoding='utf-8') as f:
    yaml.dump(yaml_config, f, default_flow_style=False)

print(f"\nYAML config created: {yaml_path}")
print(f"\nDataset ready for training!")