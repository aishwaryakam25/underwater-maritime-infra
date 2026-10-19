import os
import shutil
import yaml
from pathlib import Path

project_root = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly"

# Source datasets
sonar_dataset = os.path.join(project_root, "sonar_detect_dataset")
fish_negatives = os.path.join(project_root, "fish_negative_samples")

# Combined output
combined_dataset = os.path.join(project_root, "combined_dataset_with_negatives")
os.makedirs(combined_dataset, exist_ok=True)

print("="*70)
print("COMBINING DATASETS: Pipeline Detection + Fish Negatives")
print("="*70)

# Create structure
for split in ['train', 'val']:
    for subdir in ['images', 'labels']:
        os.makedirs(os.path.join(combined_dataset, split, subdir), exist_ok=True)

def copy_dataset(source_base, dest_base, prefix, split):
    """Copy images and labels from source to destination"""
    source_images = os.path.join(source_base, 'images', split)
    source_labels = os.path.join(source_base, 'labels', split)
    dest_images = os.path.join(dest_base, split, 'images')
    dest_labels = os.path.join(dest_base, split, 'labels')
    
    if not os.path.exists(source_images):
        print(f"  Warning: {source_images} not found")
        return 0
    
    count = 0
    for img_file in Path(source_images).glob('*'):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
            # Copy image
            new_name = f"{prefix}_{count:05d}{img_file.suffix}"
            shutil.copy2(img_file, os.path.join(dest_images, new_name))
            
            # Copy label (if exists)
            label_file = Path(source_labels) / f"{img_file.stem}.txt"
            if label_file.exists():
                shutil.copy2(label_file, os.path.join(dest_labels, f"{prefix}_{count:05d}.txt"))
            
            count += 1
    
    return count

# Copy pipeline detection dataset
print("\n1. Copying Pipeline Detection Dataset (sonar_detect_dataset)...")
train_pipeline = copy_dataset(sonar_dataset, combined_dataset, "pipeline", "train")
val_pipeline = copy_dataset(sonar_dataset, combined_dataset, "pipeline", "val")
print(f"   Train: {train_pipeline} images")
print(f"   Val: {val_pipeline} images")

# Copy fish negatives
print("\n2. Copying Fish Negative Samples...")
train_fish = copy_dataset(fish_negatives, combined_dataset, "fish_neg", "train")
val_fish = copy_dataset(fish_negatives, combined_dataset, "fish_neg", "val")
print(f"   Train: {train_fish} images")
print(f"   Val: {val_fish} images")

# Summary
total_train = train_pipeline + train_fish
total_val = val_pipeline + val_fish

print(f"\n{'='*70}")
print(f"COMBINED DATASET SUMMARY")
print(f"{'='*70}")
print(f"Training:   {total_train:6,} images ({train_pipeline:,} pipeline + {train_fish:,} fish)")
print(f"Validation: {total_val:6,} images ({val_pipeline:,} pipeline + {val_fish:,} fish)")
print(f"Total:      {total_train + total_val:6,} images")
print(f"{'='*70}")

# Create YAML config
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
print(f"\nDataset location: {combined_dataset}")
print(f"\nNext step: Compress and upload to Kaggle!")
print("="*70)