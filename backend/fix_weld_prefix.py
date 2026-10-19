file_path = r"main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = "app.include_router(innovation_router)"
new = 'app.include_router(innovation_router, prefix="/api/innovation")'

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Added /api/innovation prefix to router")
else:
    print("❌ Pattern not found")

input("Press Enter...")