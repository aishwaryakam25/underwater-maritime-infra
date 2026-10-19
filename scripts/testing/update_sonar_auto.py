import re

file_path = r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\frontend\src\SonarAnalysis.jsx"

print("Updating SonarAnalysis.jsx...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Backup
with open(file_path + '.backup', 'w', encoding='utf-8') as f:
    f.write(content)
print("Backup created")

# Add state
if 'isLiveTracking' not in content:
    content = content.replace('const [pdfLoading, setPdfLoading] = useState(false);',
        'const [pdfLoading, setPdfLoading] = useState(false);\n  const [isLiveTracking, setIsLiveTracking] = useState(false);\n  const [liveTrackingResult, setLiveTrackingResult] = useState(null);')
    print("State added")

# Remove WhatsApp
content = re.sub(r'<button[^>]*>[\s\S]*?WhatsApp[\s\S]*?</button>', '', content)
print("WhatsApp removed")

# Save
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("DONE!")