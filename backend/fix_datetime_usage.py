file_path = r"sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace datetime.datetime.now() with datetime.now()
# Since the import is "from datetime import datetime"
content = content.replace('datetime.datetime.now()', 'datetime.now()')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed datetime usage in PDF endpoint")
input("Press Enter...")