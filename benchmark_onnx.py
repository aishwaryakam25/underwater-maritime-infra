import time
from ultralytics import YOLO

model = YOLO('weights/best_merged_original.onnx', task='segment')

test_image = r'C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\data\dataset1_pipelines\test\images\1-108-_jpg.rf.c7aab830e19100ba214421fa01f4f391.jpg'

print("Warming up...")
model.predict(source=test_image, imgsz=640, save=False, verbose=False)

print("Benchmarking (30 runs)...")
times = []
for i in range(30):
    start = time.time()
    model.predict(source=test_image, imgsz=640, save=False, verbose=False)
    end = time.time()
    times.append(end - start)

avg_ms = (sum(times) / len(times)) * 1000
fps = 1000 / avg_ms

print(f"\n===== BENCHMARK RESULTS =====")
print(f"Average latency : {avg_ms:.1f} ms per batch")
print(f"Estimated FPS   : {fps:.1f}")
print(f"Device          : CPU (Intel i5-1135G7)")
print(f"Model           : best_merged_original.onnx")
print(f"Format          : ONNX opset 22")