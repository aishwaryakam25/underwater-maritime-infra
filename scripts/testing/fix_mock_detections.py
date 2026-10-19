file_path = r"backend\sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the mock return and add detections
old_sonar = '"results": [{"filename": f.filename, "total_detections": 2, "critical_count": 0, "high_count": 1} for f in sonar_files]'

new_sonar = '"results": [{"filename": f.filename, "total_detections": 2, "critical_count": 0, "high_count": 1, "detections": [{"id": 1, "class_name": "Pipeline", "confidence": 0.85, "severity": "high"}, {"id": 2, "class_name": "Sediment", "confidence": 0.62, "severity": "low"}]} for f in sonar_files]'

old_anomaly = '"results": [{"filename": f.filename, "total_detections": 3, "risk_score": 45, "grade": "B", "critical_count": 0} for f in anomaly_files]'

new_anomaly = '"results": [{"filename": f.filename, "total_detections": 3, "risk_score": 45, "grade": "B", "critical_count": 0, "detections": [{"id": 1, "class_name": "Marine Growth", "confidence": 0.78, "severity": "High"}, {"id": 2, "class_name": "Scaling", "confidence": 0.65, "severity": "Medium"}, {"id": 3, "class_name": "Dent", "confidence": 0.52, "severity": "Low"}]} for f in anomaly_files]'

if old_sonar in content:
    content = content.replace(old_sonar, new_sonar)
    print("✓ Added sonar detections")

if old_anomaly in content:
    content = content.replace(old_anomaly, new_anomaly)
    print("✓ Added anomaly detections")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Backend will reload with defect details.")
input("Press Enter...")