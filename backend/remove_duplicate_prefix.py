file_path = r"innovation_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove prefix from router definition
old = 'router = APIRouter(prefix="/api/innovation", tags=["Innovation"])'
new = 'router = APIRouter(tags=["Innovation"])'

content = content.replace(old, new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Removed duplicate prefix from innovation_routes.py")
input("Press Enter...")