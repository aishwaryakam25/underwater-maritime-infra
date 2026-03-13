import requests

url = "http://localhost:8000/api/detect"

# Use an absolute path to an existing PNG image from the workspace
file_path = r"C:/Users/RAMNATH VENKAT/Documents/nauticai-underwater-anomaly/frontend/public/nauticai-logo.png"

with open(file_path, "rb") as f:
    files = {"file": (file_path, f, "image/jpeg")}
    response = requests.post(url, files=files)
    print("Status Code:", response.status_code)
    print("Response:", response.text)
