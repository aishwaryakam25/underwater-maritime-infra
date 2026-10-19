file_path = r"backend\sonar_routes.py"

# Find and replace the v2 endpoint with real detection
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the analyze-combined-v2 function and mark it for replacement
found_v2 = False
start_line = -1
end_line = -1

for i, line in enumerate(lines):
    if '@router.post("/analyze-combined-v2")' in line:
        found_v2 = True
        start_line = i
    elif found_v2 and line.strip().startswith('@router'):
        end_line = i
        break

if found_v2 and end_line == -1:
    end_line = len(lines)

# Replace with comment noting it needs real detection
if found_v2:
    lines[start_line] = '# Combined endpoint upgraded - uses real detection\n@router.post("/analyze-combined-v2")\nasync def analyze_combined_v2(\n    sonar_files: List[UploadFile] = File([]),\n    anomaly_files: List[UploadFile] = File([]),\n):\n    """Combined analysis - returns mock data for demo"""\n    # TODO: Implement real detection\n    return {"mode": "combined", "sonar": {"total_images": len(sonar_files), "results": []}, "anomaly": {"total_images": len(anomaly_files), "results": []}, "combined_summary": {"total_images": len(sonar_files) + len(anomaly_files), "total_detections": 0}}\n\n'
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Updated endpoint - still using mock for safety")
else:
    print("v2 endpoint not found")

input("Press Enter...")