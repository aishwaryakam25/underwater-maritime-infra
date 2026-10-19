import re

file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Updating App.jsx...")

# Backup
with open(file_path + '.backup', 'w', encoding='utf-8') as f:
    f.write(content)

# Add state
if 'isLiveTracking' not in content:
    content = content.replace('const [videoFile, setVideoFile] = useState(null);',
        'const [videoFile, setVideoFile] = useState(null);\n  const [isLiveTracking, setIsLiveTracking] = useState(false);\n  const [liveTrackingResult, setLiveTrackingResult] = useState(null);')
    print("State added")

# Add function
if 'handleLiveTracking' not in content:
    func = '\n  const handleLiveTracking = async () => { if (!videoFile) return; setIsLiveTracking(true); const fd = new FormData(); fd.append("file", videoFile); try { const res = await fetch("http://localhost:8000/api/sonar/live-tracking", {method:"POST", body:fd}); const data = await res.json(); setLiveTrackingResult(data); alert("Done!"); } catch (e) { alert("Error"); } finally { setIsLiveTracking(false); } };\n'
    content = content.replace('  return (', func + '  return (')
    print("Function added")

# Add button
if 'Live Tracking' not in content:
    btn = '<button className="btn btn-primary" onClick={handleLiveTracking} disabled={isLiveTracking} style={{background:"#10B981",marginLeft:8}}>🎥 Live Tracking</button>'
    content = content.replace('Analyze Video</button>', 'Analyze Video</button>' + btn)
    print("Button added")

# Remove WhatsApp
content = re.sub(r'<button[^>]*sendVideoPDFToWa[^>]*>[^<]*</button>', '', content)
print("WhatsApp removed")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDONE! Restart: cd frontend && npm start")