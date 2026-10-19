import requests

video_path = r"C:\Users\RAMNATH VENKAT\Downloads\Underwater_Laser_Scaler_1080P.mp4"
url = "http://127.0.0.1:8000/api/sonar/live-tracking"

print("="*70)
print("TESTING LIVE VIDEO TRACKING")
print("="*70)

try:
    with open(video_path, 'rb') as video_file:
        files = {'file': video_file}
        
        print(f"\nUploading: {video_path}")
        print("Processing...\n")
        
        response = requests.post(url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            
            print("SUCCESS!")
            print(f"Inspection ID: {result['inspection_id']}")
            
            summary = result['summary']
            print(f"\nTotal frames: {summary['total_frames']}")
            print(f"Analyzed: {summary['analyzed_frames']}")
            print(f"Tracked: {summary['tracked_frames']}")
            print(f"FPS: {summary['fps']}")
            print(f"Duration: {summary['duration_sec']:.1f}s")
            
        else:
            print(f"Error {response.status_code}")
            print(response.text)
            
except FileNotFoundError:
    print(f"Video not found: {video_path}")
except Exception as e:
    print(f"Error: {e}")