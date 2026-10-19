file_path = r"backend\main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = "app.include_router(sonar_router)"
new = 'app.include_router(sonar_router, prefix="/api/sonar")'

if old in content and 'sonar_router, prefix="/api/sonar"' not in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Added /api/sonar prefix to router")
else:
    print("⚠ Already has prefix or pattern not found")

input("Press Enter...")