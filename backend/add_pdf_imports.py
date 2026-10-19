file_path = r"sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the first import and add datetime and io
first_import_idx = 0
for i, line in enumerate(lines):
    if line.strip().startswith('import ') or line.strip().startswith('from '):
        first_import_idx = i
        break

# Add imports after the first one
if 'import datetime' not in ''.join(lines[:20]):
    lines.insert(first_import_idx + 1, 'import datetime\n')
    print("✓ Added datetime import")

if 'import io' not in ''.join(lines[:20]):
    lines.insert(first_import_idx + 1, 'import io\n')
    print("✓ Added io import")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\nDone! Backend will reload.")
input("Press Enter...")