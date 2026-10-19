import requests

# Create a small test image
from PIL import Image
import io

img = Image.new('RGB', (100, 100), (128, 128, 128))
buf = io.BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)
buf2 = io.BytesIO()
img.save(buf2, format='JPEG')
buf2.seek(0)

r = requests.post(
    "http://localhost:8000/api/sonar/analyze-combined",
    files=[
        ("sonar_files", ("test_sonar.jpg", buf, "image/jpeg")),
        ("anomaly_files", ("test_anomaly.jpg", buf2, "image/jpeg")),
    ],
    data={"confidence_threshold": "0.25"}
)

print(f"Status: {r.status_code}")
print(f"Response: {r.text[:1000]}")
input("Press Enter...")