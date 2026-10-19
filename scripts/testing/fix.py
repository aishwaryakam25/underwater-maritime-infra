file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Fixing buttons...")

# Add Live Tracking button after Analyze Video
if 'Live Tracking' not in content:
    button = '\n          <button className="btn btn-primary" onClick={handleLiveTracking} disabled={isLiveTracking} style={{background:"#10B981",marginLeft:"1rem"}}>🎥 Live Tracking</button>'
    content = content.replace('Analyze Video</button>', 'Analyze Video</button>' + button)
    print("Button added")

# Remove WhatsApp
import re
content = re.sub(r'<button[^>]*>[\s\S]*?WhatsApp[\s\S]*?</button>', '', content, flags=re.DOTALL)
print("WhatsApp removed")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE! Run: cd frontend && npm start")