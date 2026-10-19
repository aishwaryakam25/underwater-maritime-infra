"""
NautiCAI Negative Example Curator
Helps prepare background/negative class data for YOLO training
"""

import os
import shutil
from pathlib import Path
import cv2
import numpy as np
from typing import List, Dict
import json

class NegativeExampleCurator:
    """
    Prepares negative examples to teach the model what NOT to detect
    """
    
    def __init__(self, output_dir: str = "curated_negative_examples"):
        self.output_dir = Path(output_dir)
        self.categories = {
            'clean_pipeline': 'Pipeline sections with no visible defects',
            'rov_equipment': 'ROV arms, manipulators, tools, thrusters',
            'human_artifacts': 'Hands, gloves, divers, equipment',
            'marine_life': 'Fish, coral, seaweed, organisms',
            'sediment': 'Sand, mud, rocks, seafloor',
            'background': 'Open water, clean backgrounds'
        }
        
        # Create directory structure
        for category in self.categories.keys():
            (self.output_dir / 'images' / category).mkdir(parents=True, exist_ok=True)
            (self.output_dir / 'labels' / category).mkdir(parents=True, exist_ok=True)
    
    def extract_background_patches(
        self, 
        image_path: str,
        detection_boxes: List[List[float]] = None,
        patch_size: int = 416,
        num_patches: int = 5
    ) -> List[np.ndarray]:
        """
        Extract random patches from image that DON'T contain detections
        These become negative training examples
        
        Args:
            image_path: Path to sonar image
            detection_boxes: List of [x1, y1, x2, y2] normalized boxes (if any)
            patch_size: Size of patches to extract
            num_patches: Number of patches per image
        """
        image = cv2.imread(image_path)
        if image is None:
            return []
        
        h, w = image.shape[:2]
        patches = []
        
        for _ in range(num_patches * 3):  # Try more times to get clean patches
            if len(patches) >= num_patches:
                break
            
            # Random crop
            if w - patch_size > 0 and h - patch_size > 0:
                x = np.random.randint(0, w - patch_size)
                y = np.random.randint(0, h - patch_size)
                
                patch = image[y:y+patch_size, x:x+patch_size]
                
                # Normalize coordinates
                patch_box = [
                    x / w, y / h,
                    (x + patch_size) / w, (y + patch_size) / h
                ]
                
                # Check if patch overlaps with any detections
                is_clean = True
                if detection_boxes:
                    for det_box in detection_boxes:
                        if self._boxes_overlap(patch_box, det_box):
                            is_clean = False
                            break
                
                if is_clean:
                    patches.append(patch)
        
        return patches
    
    def _boxes_overlap(self, box1: List[float], box2: List[float], threshold: float = 0.1) -> bool:
        """Check if two boxes overlap by more than threshold"""
        x1_min, y1_min, x1_max, y1_max = box1
        x2_min, y2_min, x2_max, y2_max = box2
        
        # Calculate intersection
        inter_x_min = max(x1_min, x2_min)
        inter_y_min = max(y1_min, y2_min)
        inter_x_max = min(x1_max, x2_max)
        inter_y_max = min(y1_max, y2_max)
        
        if inter_x_max < inter_x_min or inter_y_max < inter_y_min:
            return False
        
        inter_area = (inter_x_max - inter_x_min) * (inter_y_max - inter_y_min)
        box1_area = (x1_max - x1_min) * (y1_max - y1_min)
        
        overlap_ratio = inter_area / box1_area if box1_area > 0 else 0
        return overlap_ratio > threshold
    
    def create_empty_yolo_label(self, image_name: str, category: str):
        """
        Create empty YOLO label file for negative examples
        Empty .txt file = no objects in image = background/negative
        """
        label_path = self.output_dir / 'labels' / category / f"{image_name}.txt"
        label_path.touch()  # Create empty file
        return label_path
    
    def organize_existing_images(
        self,
        source_dirs: Dict[str, str],
        auto_categorize: bool = True
    ):
        """
        Organize existing images into negative example categories
        
        Args:
            source_dirs: {category: directory_path} mapping
            auto_categorize: Use simple heuristics to categorize uncategorized images
        """
        for category, source_dir in source_dirs.items():
            source_path = Path(source_dir)
            if not source_path.exists():
                print(f"Warning: {source_path} does not exist")
                continue
            
            dest_img_dir = self.output_dir / 'images' / category
            dest_label_dir = self.output_dir / 'labels' / category
            
            for img_file in source_path.glob("*.jpg") + list(source_path.glob("*.png")):
                # Copy image
                shutil.copy(img_file, dest_img_dir / img_file.name)
                
                # Create empty label
                self.create_empty_yolo_label(img_file.stem, category)
                
                print(f"Added {img_file.name} to {category}")
    
    def generate_yolo_dataset(self, train_split: float = 0.8) -> Dict:
        """
        Convert curated negative examples into YOLO format dataset
        Combines with existing positive examples
        
        Returns:
            Dataset statistics and paths
        """
        all_images = []
        all_labels = []
        
        # Collect all negative examples
        for category in self.categories.keys():
            img_dir = self.output_dir / 'images' / category
            label_dir = self.output_dir / 'labels' / category
            
            for img_path in img_dir.glob("*.jpg") + list(img_dir.glob("*.png")):
                all_images.append(img_path)
                label_path = label_dir / f"{img_path.stem}.txt"
                all_labels.append(label_path)
        
        # Split train/val
        num_train = int(len(all_images) * train_split)
        indices = np.random.permutation(len(all_images))
        
        train_indices = indices[:num_train]
        val_indices = indices[num_train:]
        
        # Create YOLO dataset structure
        dataset_dir = self.output_dir / 'yolo_dataset'
        (dataset_dir / 'images' / 'train').mkdir(parents=True, exist_ok=True)
        (dataset_dir / 'images' / 'val').mkdir(parents=True, exist_ok=True)
        (dataset_dir / 'labels' / 'train').mkdir(parents=True, exist_ok=True)
        (dataset_dir / 'labels' / 'val').mkdir(parents=True, exist_ok=True)
        
        # Copy files
        for idx in train_indices:
            shutil.copy(all_images[idx], dataset_dir / 'images' / 'train' / all_images[idx].name)
            shutil.copy(all_labels[idx], dataset_dir / 'labels' / 'train' / all_labels[idx].name)
        
        for idx in val_indices:
            shutil.copy(all_images[idx], dataset_dir / 'images' / 'val' / all_images[idx].name)
            shutil.copy(all_labels[idx], dataset_dir / 'labels' / 'val' / all_labels[idx].name)
        
        # Create dataset.yaml
        yaml_content = f"""
# NautiCAI Dataset with Negative Examples
path: {dataset_dir.absolute()}
train: images/train
val: images/val

# Classes (including background for negative examples)
names:
  0: pipeline
  1: cp_failure
  2: corrosion
  3: scaling
  4: blockage
  5: background  # Empty labels = background class

# Training notes:
# - Images with empty .txt files are negative examples
# - Model will learn to NOT detect anything in those regions
# - Reduces false positives on ROV equipment, hands, marine life
"""
        
        yaml_path = dataset_dir / 'dataset.yaml'
        with open(yaml_path, 'w') as f:
            f.write(yaml_content)
        
        stats = {
            'total_negative_examples': len(all_images),
            'train_samples': len(train_indices),
            'val_samples': len(val_indices),
            'categories': {cat: len(list((self.output_dir / 'images' / cat).glob("*"))) 
                          for cat in self.categories.keys()},
            'dataset_path': str(dataset_dir.absolute()),
            'yaml_path': str(yaml_path.absolute())
        }
        
        return stats
    
    def analyze_false_positives(
        self,
        detection_log_path: str,
        visualize: bool = True
    ):
        """
        Analyze logged false positives to identify patterns
        Helps prioritize what negative examples to collect
        """
        # Load detection logs (assuming JSON format)
        with open(detection_log_path, 'r') as f:
            logs = json.load(f)
        
        false_positive_stats = {
            'by_class': {},
            'by_confidence_range': {'<0.3': 0, '0.3-0.5': 0, '0.5-0.7': 0, '>0.7': 0},
            'common_patterns': []
        }
        
        # Aggregate statistics
        for log_entry in logs:
            if log_entry.get('false_positive'):
                cls = log_entry['class']
                conf = log_entry['confidence']
                
                false_positive_stats['by_class'][cls] = \
                    false_positive_stats['by_class'].get(cls, 0) + 1
                
                if conf < 0.3:
                    false_positive_stats['by_confidence_range']['<0.3'] += 1
                elif conf < 0.5:
                    false_positive_stats['by_confidence_range']['0.3-0.5'] += 1
                elif conf < 0.7:
                    false_positive_stats['by_confidence_range']['0.5-0.7'] += 1
                else:
                    false_positive_stats['by_confidence_range']['>0.7'] += 1
        
        return false_positive_stats


# Usage guide
def print_usage_guide():
    guide = """
╔══════════════════════════════════════════════════════════════╗
║  NautiCAI Negative Example Curator - Usage Guide            ║
╚══════════════════════════════════════════════════════════════╝

STEP 1: Collect Negative Examples
─────────────────────────────────
Gather images that should NOT trigger detections:

1. Clean pipeline sections (no defects)
2. ROV equipment (arms, tools, thrusters)
3. Human artifacts (hands, gloves, divers)
4. Marine life (fish, coral, seaweed)
5. Sediment/seafloor
6. Open water backgrounds

STEP 2: Organize Images
───────────────────────
curator = NegativeExampleCurator()

# Option A: Auto-organize from directories
curator.organize_existing_images({
    'clean_pipeline': 'path/to/clean_pipelines/',
    'rov_equipment': 'path/to/rov_images/',
    'human_artifacts': 'path/to/hands_and_divers/'
})

# Option B: Extract patches from existing sonar images
patches = curator.extract_background_patches(
    image_path='sonar_scan_001.jpg',
    detection_boxes=existing_detections,  # Avoid labeled regions
    num_patches=10
)

STEP 3: Generate YOLO Dataset
─────────────────────────────
stats = curator.generate_yolo_dataset(train_split=0.8)
print(f"Dataset ready: {stats['dataset_path']}")

STEP 4: Retrain Model
────────────────────
# Use the generated dataset.yaml in YOLO training
# Empty label files tell YOLO "nothing to detect here"

from ultralytics import YOLO
model = YOLO('yolov8x.pt')

results = model.train(
    data='curated_negative_examples/yolo_dataset/dataset.yaml',
    epochs=100,
    imgsz=640,
    batch=16
)

KEY INSIGHTS:
────────────
• Empty .txt labels = background/negative examples
• Model learns to suppress false positives
• Aim for 20-30% negative examples in dataset
• Focus on actual false positive patterns you're seeing
"""
    print(guide)


if __name__ == "__main__":
    print_usage_guide()
