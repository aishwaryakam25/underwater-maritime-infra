import re

file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Finding VideoPage component...")

# Find VideoPage function
vp_idx = content.find('const VideoPage')
if vp_idx < 0:
    vp_idx = content.find('function VideoPage')

if vp_idx >= 0:
    # Find first useState after VideoPage
    first_state = content.find('useState', vp_idx)
    if first_state > 0:
        line_end = content.find(';', first_state)
        state_add = '\n  const [isLiveTracking, setIsLiveTracking] = useState(false);\n  const [liveTrackingResult, setLiveTrackingResult] = useState(null);'
        content = content[:line_end+1] + state_add + content[line_end+1:]
        print("State added")
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("DONE!")