file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Searching App.jsx...")

# Search for various patterns
searches = [
    ('VideoPage', 'Component name'),
    ('Video Analysis', 'Tab title'),
    ('const [videoFile', 'Video state'),
    ('Analyze Video', 'Button text'),
]

for term, desc in searches:
    idx = content.find(term)
    if idx >= 0:
        print(f"\n'{term}' ({desc}) at position {idx}")
        print("Context:")
        print(content[max(0, idx-100):idx+200])
        print("-"*70)