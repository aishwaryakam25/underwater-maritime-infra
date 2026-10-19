from ultralytics import YOLO

DATA_PATH = "C:/Users/RAMNATH VENKAT/Documents/nauticai-underwater-anomaly/Marine_PULSE"

print("NautiCAI - Marine PULSE Sonar Classification")

model = YOLO("yolov8m-cls.pt")

results = model.train(
    data=DATA_PATH,
    epochs=50,
    batch=16,
    imgsz=224,
    project="C:/Users/RAMNATH VENKAT/Documents/nauticai-underwater-anomaly/runs",
    name="sonar_classification",
    patience=15,
    save=True,
    plots=True,
    verbose=True,
    flipud=0.5,
    fliplr=0.5,
    hsv_h=0.0,
    hsv_s=0.1,
    hsv_v=0.3,
)

print(f"Best weights: {results.save_dir}/weights/best.pt")

model_best = YOLO(f"{results.save_dir}/weights/best.pt")
val_results = model_best.val(data=DATA_PATH)
print(f"Top-1 Accuracy: {val_results.top1:.4f}")
print(f"Top-5 Accuracy: {val_results.top5:.4f}")