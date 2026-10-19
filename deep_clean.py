import os
import shutil
import glob

os.chdir(r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly")

print("DEEP CLEAN - Moving ALL datasets and old files...")

# Move ALL dataset folders
datasets = ['sonar_defect_images', 'sonar_detect_dataset', 'SubPipe', 'Marine_PULSE', 
            'AI4Shipwrecks', 'acoustic-leakage-dataset-GPLA-12-main', 'fishimages', 
            'fish_negative_samples', 'combined_dataset_with_negatives', 'synthetic_data',
            'data', 'configs']

for d in datasets:
    if os.path.exists(d):
        try:
            shutil.move(d, f'datasets_archive/{d}')
            print(f"Moved: {d}")
        except:
            pass

# Move training folders
train_folders = ['runs', 'weights', 'train', 'test', 'utils']
for f in train_folders:
    if os.path.exists(f):
        try:
            shutil.move(f, f'archived/{f}')
        except:
            pass

# Move .pt weights to backend/models
for pt in glob.glob('*.pt'):
    try:
        shutil.copy2(pt, f'backend/models/{pt}')
        os.remove(pt)
    except:
        pass

# Remove empty/temp files
for f in ['cd', 'python']:
    if os.path.exists(f) and os.path.isfile(f):
        os.remove(f)

print("\n✓ DONE! Root is now clean")
print("\nKEPT IN ROOT:")
print("  backend/, frontend/, app/")
print("  scripts/, datasets_archive/, docs/, reports/")
print("  Essential config files")