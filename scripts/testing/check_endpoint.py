import requests

try:
    r = requests.post(
        "http://localhost:8000/api/sonar/analyze-combined",
        data={"confidence_threshold": "0.25"}
    )
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

input("Press Enter...")