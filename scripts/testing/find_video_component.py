import os

# Search for files containing "Analyze Video" or video-related code
search_dir = r"frontend\src"
search_terms = ['Analyze Video', 'VIDEO UPLOAD', 'Drop video file']

print("Searching for Video Analysis component...")

for root, dirs, files in os.walk(search_dir):
    for file in files:
        if file.endswith('.jsx') or file.endswith('.js'):
            filepath = os.path.join(root, file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                for term in search_terms:
                    if term in content:
                        print(f"\n✓ Found '{term}' in: {file}")
                        break
            except:
                pass