file_path = r"backend\main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

old = 'app.include_router(sonar_router, prefix="/api/sonar")'
new = 'app.include_router(sonar_router)'

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Removed duplicate sonar prefix")
else:
    print("Not found")

input("Press Enter...")