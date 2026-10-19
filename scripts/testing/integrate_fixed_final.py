import os
import shutil
import yaml
from pathlib import Path

project_root = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly"

sonar_dataset = os.path.join(project_root, "sonar_detect_dataset")
fish_negatives = os.path.join(project_root, "fish_negative_samples")
combined_dataset = os.path.join(project_root, "combined_dataset_with_negatives")

print("="*70)
print("COMBINING DATASETS: Pipeline Detection + Fish Negatives (FIXED)")
print("="*70)

# Clear and recreate combined dataset
if os.path.exists(combined_dataset):
    shutil.rmtree(combined_dataset)
os.makedirs(combined_dataset, exist_ok=True)

for split in ['train', 'val']:
    for subdir in ['images', 'labels']:
        os.makedirs(os.path.join(combined_dataset, split, subdir), exist_ok=True)

def copy_sonar_dataset(split):
    """Copy sonar_detect_dataset (images/split structure)"""
    source_images = os.path.join(sonar_dataset, 'images', split)
    source_labels = os.path.join(sonar_dataset, 'labels', split)
    dest_images = os.path.join(combined_dataset, split, 'images')
    dest_labels = os.path.join(combined_dataset, split, 'labels')
    
    count = 0
    for img_file in Path(source_images).glob('*'):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
            new_name = f"pipeline_{count:05d}{img_file.suffix}"
            shutil.copy2(img_file, os.path.join(dest_images, new_name))
            label_file = Path(source_labels) / f"{img_file.stem}.txt"
            if label_file.exists():
                shutil.copy2(label_file, os.path.join(dest_labels, f"pipeline_{count:05d}.txt"))
            count += 1
    return count

def copy_fish_negatives(split):
    """Copy fish_negative_samples (split/images structure)"""
    source_images = os.path.join(fish_negatives, split, 'images')
    source_labels = os.path.join(fish_negatives, split, 'labels')
    dest_images = os.path.join(combined_dataset, split, 'images')
    dest_labels = os.path.join(combined_dataset, split, 'labels')
    
    if not os.path.exists(source_images):
        print(f"  ERROR: {source_images} not found!")
        return 0
    
    count = 0
    for img_file in Path(source_images).glob('*'):
        if img_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']:
            new_name = f"fish_neg_{count:05d}{img_file.suffix}"
            shutil.copy2(img_file, os.path.join(dest_images, new_name))
            label_file = Path(source_labels) / f"{img_file.stem}.txt"
            if label_file.exists():
                shutil.copy2(label_file, os.path.join(dest_labels, f"fish_neg_{count:05d}.txt"))
            count += 1
    return count

# Copy pipeline detection
print("\n1. Copying Pipeline Detection Dataset...")
train_pipeline = copy_sonar_dataset('train')
val_pipeline = copy_sonar_dataset('val')
print(f"   Train: {train_pipeline:,} images")
print(f"   Val: {val_pipeline:,} images")

# Copy fish negatives
print("\n2. Copying Fish Negative Samples...")
train_fish = copy_fish_negatives('train')
val_fish = copy_fish_negatives('val')
print(f"   Train: {train_fish:,} images")
print(f"   Val: {val_fish:,} images")

total_train = train_pipeline + train_fish
total_val = val_pipeline + val_fish

print(f"\n{'='*70}")
print(f"COMBINED DATASET SUMMARY")
print(f"{'='*70}")
print(f"Training:   {total_train:6,} images ({train_pipeline:,} pipeline + {train_fish:,} fish)")
print(f"Validation: {total_val:6,} images ({val_pipeline:,} pipeline + {val_fish:,} fish)")
print(f"Total:      {total_train + total_val:6,} images")
print(f"{'='*70}")

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

print(f"\nYAML config: {yaml_path}")
print(f"Dataset location: {combined_dataset}")
print("\nNext: Compress and upload to Kaggle!")
print("="*70)