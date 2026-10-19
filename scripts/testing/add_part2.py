import re

file_path = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\frontend\src\SonarAnalysis.jsx"

print("Adding Live Tracking functionality...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add function
if 'handleLiveTracking' not in content:
    func = '''
  const handleLiveTracking = async () => {
    if (!videoFile) { alert('Upload video first'); return; }
    setIsLiveTracking(true);
    const formData = new FormData();
    formData.append('file', videoFile);
    try {
      const res = await fetch('http://localhost:8000/api/sonar/live-tracking', {method: 'POST', body: formData});
      const data = await res.json();
      setLiveTrackingResult(data);
      alert('Live tracking complete!');
    } catch (err) { setError('Failed'); }
    finally { setIsLiveTracking(false); }
  };

'''
    content = content.replace('  return (', func + '  return (')
    print("Function added")

# Add button
if 'Live Tracking' not in content:
    button = '<button className="btn" onClick={handleLiveTracking} disabled={isLiveTracking} style={{background:"#10B981",marginLeft:"1rem"}}>🎥 {isLiveTracking ? "Processing..." : "Live Tracking"}</button>'
    content = content.replace('Analyze Video</button>', 'Analyze Video</button>\n          ' + button)
    print("Button added")

# Save
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE! Restart frontend!")