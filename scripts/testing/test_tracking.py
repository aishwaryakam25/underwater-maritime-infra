import requests

video_path = r"C:\Users\RAMNATH VENKAT\Downloads\vidssave.com Underwater ROV Pipe Inspection  with Laser Scaler 1080P.mp4"
url = "http://127.0.0.1:8000/api/sonar/live-tracking"

print("TESTING LIVE TRACKING")
print("Uploading video...")

try:
    with open(video_path, 'rb') as f:
        response = requests.post(url, files={'file': f})
        
        if response.status_code == 200:
            result = response.json()
            print("SUCCESS!")
            print(f"Inspection ID: {result['inspection_id']}")
            print(f"Frames: {result['summary']['total_frames']}")
            print(f"Analyzed: {result['summary']['analyzed_frames']}")
        else:
            print(f"Error: {response.status_code}")
            
except Exception as e:
    print(f"Error: {e}")