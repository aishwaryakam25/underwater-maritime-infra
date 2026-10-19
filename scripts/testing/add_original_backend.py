file_path = r"backend\main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace
old = '"enhanced_b64": _pil_to_b64(enhanced),\n    }'
new = '"enhanced_b64": _pil_to_b64(enhanced),\n        "original_b64": _pil_to_b64(pil_img),\n    }'

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Added original_b64 to backend")
else:
    print("❌ Pattern not found")

input("Press Enter...")