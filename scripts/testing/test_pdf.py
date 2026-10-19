import requests
import json

test_results = {
    "sonar": {"total_images": 1, "results": [{"filename": "test.jpg", "total_detections": 2}]},
    "anomaly": {"total_images": 1, "results": [{"filename": "test2.jpg", "total_detections": 3, "grade": "B", "risk_score": 45}]},
    "combined_summary": {"total_images": 2, "total_detections": 5}
}

r = requests.post(
    "http://localhost:8000/api/sonar/report/combined-pdf",
    data={
        "results_json": json.dumps(test_results),
        "vessel_name": "Test",
        "inspector": "Test"
    }
)

print(f"Status: {r.status_code}")
if r.status_code != 200:
    print(f"Error: {r.text[:500]}")
else:
    print("PDF generated successfully!")
    with open("test_combined.pdf", "wb") as f:
        f.write(r.content)
    print("Saved as test_combined.pdf")

input("Press Enter...")