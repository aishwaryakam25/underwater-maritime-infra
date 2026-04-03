from ultralytics import YOLO
import os

models = [
    'weights/best_merged_original.pt',
    'weights/best_archive.pt',
    'weights/best_subpipemini.pt',
    'weights/best_subpipemini2.pt',
    'weights/best_subsea1_4class.pt',
    'data/train_subpipe_full5/weights/best.pt',
    'runs/detect/nauticai_v1/weights/best.pt',
    'runs/detect/runs/train/baseline_merged_light/weights/best.pt',
]

for path in models:
    if os.path.exists(path):
        print(f'Exporting {path}...')
        model = YOLO(path)
        model.export(format='onnx', imgsz=640, simplify=True, dynamic=False)
        print(f'✅ Done: {path}')
    else:
        print(f'⚠️ SKIPPED (not found): {path}')

print('ALL EXPORTS DONE!')