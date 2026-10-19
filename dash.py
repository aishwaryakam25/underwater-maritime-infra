import re

file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove Dashboard from tabs array
content = re.sub(r'\{\s*id:\s*"dash",.*?"Dashboard"\s*\},?', '', content)

# Remove route
content = re.sub(r'\{tab\s*===\s*"dash".*?/>\}', '', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Dashboard removed!")