import re

file_path = r"frontend\src\App.jsx"

print("Reading App.jsx...")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old_pattern = r' showEnhance enhanceAll=\{enhanceAll\} runBothAll=\{runBothAll\}'
content = re.sub(old_pattern, '', content)

print("Writing changes...")
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Buttons removed.")
input("Press Enter to close...")