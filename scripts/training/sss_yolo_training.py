

import os
import sys
import shutil
import random
import argparse
from pathlib import Path
from PIL import Image
from tqdm import tqdm

# ============================================================
# CONFIGURATION - EDIT THIS PATH
# ============================================================
SUBPIPE_PATH = "C:/Users/RAMNATH VENKAT/Downloads/SubPipe/SubPipe"
OUTPUT_DIR = "C:/Users/RAMNATH VENKAT/Documents/nauticai-underwater-anomaly/sonar_dataset"
TRAIN_SPLIT = 0.85  # 85% train, 15% val
USE_HF = True        # Use High Frequency sonar images
USE_LF = True        # Use Low Frequency sonar images
IMG_FORMAT = "png"    # Output format: png or jpg


def find_chunks(subpipe_path):
    """Find all data chunks in SubPipe dataset."""
    data_dir = os.path.join(subpipe_path, "DATA")
    if not os.path.exists(data_dir):
        # Maybe the path IS the data dir
        data_dir = subpipe_path
    
    chunks = []
    for item in sorted(os.listdir(data_dir)):
        chunk_path = os.path.join(data_dir, item)
        if os.path.isdir(chunk_path) and item.startswith("Chunk"):
            chunks.append(chunk_path)
    
    if not chunks:
        print(f"[ERROR] No Chunk folders found in {data_dir}")
        print(f"  Contents: {os.listdir(data_dir)}")
        sys.exit(1)
    
    return chunks


def find_sss_data(chunk_path):
    """Find SSS images and their YOLO annotations in a chunk."""
    results = []
    
    # Check for HF and LF sonar folders
    sss_folders = []
    if USE_HF:
        hf_path = os.path.join(chunk_path, "SSS_HF_images")
        if os.path.exists(hf_path):
            sss_folders.append(("HF", hf_path))
    if USE_LF:
        lf_path = os.path.join(chunk_path, "SSS_LF_images")
        if os.path.exists(lf_path):
            sss_folders.append(("LF", lf_path))
    
    for freq_type, folder in sss_folders:
        # Find all image files
        image_files = []
        for f in os.listdir(folder):
            if f.lower().endswith(('.pbm', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff')):
                image_files.append(f)
        
        # Look for YOLO annotation files (.txt)
        # They could be in same folder, or in a labels subfolder, or annotations subfolder
        label_dirs_to_check = [
            folder,
            os.path.join(folder, "labels"),
            os.path.join(folder, "annotations"),
            os.path.join(folder, "yolo"),
            os.path.join(chunk_path, f"SSS_{freq_type}_labels"),
            os.path.join(chunk_path, f"SSS_{freq_type}_annotations"),
            os.path.join(chunk_path, "labels", f"SSS_{freq_type}_images"),
            os.path.join(chunk_path, "annotations", freq_type),
        ]
        
        label_dir = None
        for ld in label_dirs_to_check:
            if os.path.exists(ld):
                txt_files = [f for f in os.listdir(ld) if f.endswith('.txt')]
                if txt_files:
                    label_dir = ld
                    break
        
        for img_file in image_files:
            img_path = os.path.join(folder, img_file)
            stem = Path(img_file).stem
            
            # Try to find matching label
            label_path = None
            if label_dir:
                label_file = os.path.join(label_dir, stem + ".txt")
                if os.path.exists(label_file):
                    label_path = label_file
            
            results.append({
                "image_path": img_path,
                "label_path": label_path,
                "freq_type": freq_type,
                "chunk": os.path.basename(chunk_path),
                "stem": stem,
            })
    
    return results


def convert_pbm_to_png(src_path, dst_path):
    """Convert PBM image to PNG/JPG."""
    try:
        img = Image.open(src_path)
        # Convert to RGB if grayscale (sonar images are usually grayscale)
        if img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(dst_path)
        return True
    except Exception as e:
        print(f"  [WARN] Failed to convert {src_path}: {e}")
        return False


def setup_yolo_structure(output_dir):
    """Create YOLO training directory structure."""
    dirs = [
        os.path.join(output_dir, "images", "train"),
        os.path.join(output_dir, "images", "val"),
        os.path.join(output_dir, "labels", "train"),
        os.path.join(output_dir, "labels", "val"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    return dirs


def create_data_yaml(output_dir):
    """Create YOLO data.yaml config file."""
    yaml_content = f"""# NautiCAI Sonar Pipeline Detection Dataset
# Generated from SubPipe Side-Scan Sonar data

path: {output_dir}
train: images/train
val: images/val

# Classes - pipeline detection from side-scan sonar
nc: 1
names:
  0: pipeline
"""
    yaml_path = os.path.join(output_dir, "data.yaml")
    with open(yaml_path, 'w') as f:
        f.write(yaml_content)
    print(f"[OK] Created {yaml_path}")
    return yaml_path


def main():
    parser = argparse.ArgumentParser(description="NautiCAI SSS YOLO Training Setup")
    parser.add_argument("--subpipe_path", type=str, default=SUBPIPE_PATH,
                        help="Path to extracted SubPipe folder")
    parser.add_argument("--output_dir", type=str, default=OUTPUT_DIR,
                        help="Output directory for YOLO dataset")
    parser.add_argument("--train_only", action="store_true",
                        help="Skip data prep, just run training")
    parser.add_argument("--epochs", type=int, default=100,
                        help="Training epochs")
    parser.add_argument("--batch", type=int, default=8,
                        help="Batch size")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Image size for training")
    parser.add_argument("--model", type=str, default="yolov8m.pt",
                        help="Base model (yolov8n/s/m/l/x)")
    args = parser.parse_args()

    if not args.train_only:
        # ============================================================
        # STEP 1: Find all SSS data
        # ============================================================
        print("=" * 60)
        print("STEP 1: Scanning SubPipe dataset...")
        print("=" * 60)
        
        chunks = find_chunks(args.subpipe_path)
        print(f"Found {len(chunks)} chunks: {[os.path.basename(c) for c in chunks]}")
        
        all_data = []
        for chunk in chunks:
            chunk_data = find_sss_data(chunk)
            all_data.extend(chunk_data)
            labeled = sum(1 for d in chunk_data if d["label_path"])
            print(f"  {os.path.basename(chunk)}: {len(chunk_data)} SSS images, {labeled} with YOLO labels")
        
        print(f"\nTotal: {len(all_data)} SSS images")
        labeled_total = sum(1 for d in all_data if d["label_path"])
        print(f"With YOLO labels: {labeled_total}")
        
        if labeled_total == 0:
            print("\n[WARNING] No YOLO label files found!")
            print("Looking for COCO annotations instead...")
            
            # Search for COCO JSON files
            coco_files = []
            for root, dirs, files in os.walk(args.subpipe_path):
                for f in files:
                    if f.endswith('.json') and ('coco' in f.lower() or 'annotation' in f.lower()):
                        coco_files.append(os.path.join(root, f))
            
            if coco_files:
                print(f"Found COCO annotation files:")
                for cf in coco_files:
                    print(f"  {cf}")
                print("\nWill convert COCO to YOLO format...")
                # Convert COCO to YOLO
                all_data = convert_coco_to_yolo(coco_files, all_data, args.subpipe_path)
                labeled_total = sum(1 for d in all_data if d["label_path"])
                print(f"After conversion: {labeled_total} images with labels")
            else:
                print("\n[INFO] No annotation files found. Checking all .txt and .json files...")
                for root, dirs, files in os.walk(args.subpipe_path):
                    for f in files:
                        if f.endswith(('.txt', '.json', '.xml', '.csv')):
                            fpath = os.path.join(root, f)
                            fsize = os.path.getsize(fpath)
                            if fsize > 100:  # Skip tiny files
                                print(f"  {os.path.relpath(fpath, args.subpipe_path)} ({fsize} bytes)")
                
                print("\nPlease check the folder structure and update label paths.")
                print("Continuing with unlabeled images for now...")
        
        # ============================================================
        # STEP 2: Setup YOLO directory structure
        # ============================================================
        print("\n" + "=" * 60)
        print("STEP 2: Setting up YOLO directory structure...")
        print("=" * 60)
        
        setup_yolo_structure(args.output_dir)
        
        # Filter to only labeled images for training (if available)
        if labeled_total > 0:
            train_data = [d for d in all_data if d["label_path"]]
        else:
            train_data = all_data
        
        # Shuffle and split
        random.seed(42)
        random.shuffle(train_data)
        split_idx = int(len(train_data) * TRAIN_SPLIT)
        train_set = train_data[:split_idx]
        val_set = train_data[split_idx:]
        
        print(f"Train: {len(train_set)} images")
        print(f"Val: {len(val_set)} images")
        
        # ============================================================
        # STEP 3: Convert and copy files
        # ============================================================
        print("\n" + "=" * 60)
        print("STEP 3: Converting PBM to PNG and organizing files...")
        print("=" * 60)
        
        for split_name, split_data in [("train", train_set), ("val", val_set)]:
            print(f"\nProcessing {split_name} set ({len(split_data)} images)...")
            
            success = 0
            for item in tqdm(split_data, desc=f"  {split_name}"):
                src_img = item["image_path"]
                # Create unique filename using chunk + freq + original name
                new_name = f"{item['chunk']}_{item['freq_type']}_{item['stem']}"
                
                dst_img = os.path.join(args.output_dir, "images", split_name, f"{new_name}.{IMG_FORMAT}")
                
                # Convert image
                if src_img.lower().endswith('.pbm'):
                    ok = convert_pbm_to_png(src_img, dst_img)
                else:
                    try:
                        shutil.copy2(src_img, dst_img)
                        ok = True
                    except Exception as e:
                        print(f"  [WARN] Copy failed: {e}")
                        ok = False
                
                if ok:
                    success += 1
                
                # Copy label if exists
                if item["label_path"]:
                    dst_label = os.path.join(args.output_dir, "labels", split_name, f"{new_name}.txt")
                    try:
                        shutil.copy2(item["label_path"], dst_label)
                    except Exception as e:
                        print(f"  [WARN] Label copy failed: {e}")
            
            print(f"  {split_name}: {success}/{len(split_data)} images converted successfully")
        
        # ============================================================
        # STEP 4: Create data.yaml
        # ============================================================
        print("\n" + "=" * 60)
        print("STEP 4: Creating data.yaml...")
        print("=" * 60)
        
        yaml_path = create_data_yaml(args.output_dir)
        
        # Print summary
        print("\n" + "=" * 60)
        print("DATASET READY!")
        print("=" * 60)
        train_imgs = len(os.listdir(os.path.join(args.output_dir, "images", "train")))
        val_imgs = len(os.listdir(os.path.join(args.output_dir, "images", "val")))
        train_labels = len(os.listdir(os.path.join(args.output_dir, "labels", "train")))
        val_labels = len(os.listdir(os.path.join(args.output_dir, "labels", "val")))
        print(f"  Train images: {train_imgs}")
        print(f"  Train labels: {train_labels}")
        print(f"  Val images:   {val_imgs}")
        print(f"  Val labels:   {val_labels}")
        print(f"  data.yaml:    {yaml_path}")
    
    else:
        yaml_path = os.path.join(args.output_dir, "data.yaml")
    
    # ============================================================
    # STEP 5: Train YOLOv8
    # ============================================================
    print("\n" + "=" * 60)
    print("STEP 5: Starting YOLOv8 Training...")
    print("=" * 60)
    
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics not installed. Run: pip install ultralytics")
        sys.exit(1)
    
    model = YOLO(args.model)
    
    results = model.train(
        data=yaml_path if not args.train_only else os.path.join(args.output_dir, "data.yaml"),
        epochs=args.epochs,
        batch=args.batch,
        imgsz=args.imgsz,
        project=os.path.join(args.output_dir, "runs"),
        name="nauticai_sonar_pipeline",
        patience=20,
        save=True,
        save_period=10,
        plots=True,
        verbose=True,
        # Augmentation for sonar images
        flipud=0.5,     # Vertical flip (sonar can be flipped)
        fliplr=0.5,     # Horizontal flip
        mosaic=0.5,     # Mosaic augmentation
        hsv_h=0.0,      # No hue shift (sonar is grayscale-like)
        hsv_s=0.1,      # Minimal saturation
        hsv_v=0.3,      # Some brightness variation
        scale=0.3,      # Scale augmentation
        translate=0.1,   # Translation
    )
    
    print("\n" + "=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)
    print(f"Best weights: {results.save_dir}/weights/best.pt")
    print(f"Results: {results.save_dir}")


def convert_coco_to_yolo(coco_files, all_data, subpipe_path):
    """Convert COCO JSON annotations to YOLO format."""
    import json
    
    # Build image path lookup
    img_lookup = {}
    for item in all_data:
        fname = os.path.basename(item["image_path"])
        stem = Path(fname).stem
        img_lookup[fname] = item
        img_lookup[stem] = item
    
    temp_label_dir = os.path.join(subpipe_path, "_yolo_labels_converted")
    os.makedirs(temp_label_dir, exist_ok=True)
    
    for coco_file in coco_files:
        print(f"  Converting: {os.path.basename(coco_file)}")
        with open(coco_file, 'r') as f:
            coco = json.load(f)
        
        # Build image id -> info mapping
        images_info = {}
        for img in coco.get("images", []):
            images_info[img["id"]] = img
        
        # Group annotations by image_id
        img_annotations = {}
        for ann in coco.get("annotations", []):
            img_id = ann["image_id"]
            if img_id not in img_annotations:
                img_annotations[img_id] = []
            img_annotations[img_id].append(ann)
        
        # Convert each image's annotations to YOLO format
        for img_id, anns in img_annotations.items():
            if img_id not in images_info:
                continue
            
            img_info = images_info[img_id]
            img_w = img_info["width"]
            img_h = img_info["height"]
            img_fname = img_info["file_name"]
            stem = Path(img_fname).stem
            
            yolo_lines = []
            for ann in anns:
                bbox = ann["bbox"]  # COCO format: [x, y, width, height] (absolute)
                x, y, w, h = bbox
                
                # Convert to YOLO format: [class, cx, cy, w, h] (normalized)
                cx = (x + w / 2) / img_w
                cy = (y + h / 2) / img_h
                nw = w / img_w
                nh = h / img_h
                
                # Clamp values
                cx = max(0, min(1, cx))
                cy = max(0, min(1, cy))
                nw = max(0, min(1, nw))
                nh = max(0, min(1, nh))
                
                # Class 0 = pipeline
                yolo_lines.append(f"0 {cx:.6f} {cy:.6f} {nw:.6f} {nh:.6f}")
            
            if yolo_lines:
                label_path = os.path.join(temp_label_dir, f"{stem}.txt")
                with open(label_path, 'w') as f:
                    f.write("\n".join(yolo_lines))
                
                # Update the matching data item
                if img_fname in img_lookup:
                    img_lookup[img_fname]["label_path"] = label_path
                elif stem in img_lookup:
                    img_lookup[stem]["label_path"] = label_path
    
    converted = sum(1 for d in all_data if d["label_path"])
    print(f"  Converted {converted} annotations to YOLO format")
    return all_data


if __name__ == "__main__":
    main()
