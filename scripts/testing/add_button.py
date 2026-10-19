import re

file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Adding Live Tracking button...")

# Add button right after Analyze Video
button = '\n          <button className="btn btn-primary" onClick={handleLiveTracking} disabled={isLiveTracking} style={{background:"#10B981",marginLeft:"1rem"}}>🎥 {isLiveTracking ? "Processing..." : "Live Tracking"}</button>'

if 'Live Tracking' not in content:
    content = content.replace('Analyze Video</button>', 'Analyze Video</button>' + button)
    print("Button added")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("DONE!")
else:
    print("Already exists")