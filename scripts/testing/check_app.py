file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find the Video Analysis section
import re
video_section = re.search(r'(Analyze Video.{800})', content, re.DOTALL)

if video_section:
    print("BUTTONS SECTION IN APP.JSX:")
    print("="*70)
    print(video_section.group(1))
    print("="*70)
else:
    print("Searching for video-related code...")
    if 'VIDEO UPLOAD' in content:
        idx = content.find('VIDEO UPLOAD')
        print(content[idx:idx+1000])