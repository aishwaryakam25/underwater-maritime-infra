file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace
old = '<ImgPanel label="ORIGINAL" color="#64748b" src={preview} placeholder="No image" />'
new = '<ImgPanel label="ORIGINAL" color="#64748b" src={detResult?.original_b64?`data:image/jpeg;base64,${detResult.original_b64}`:preview} placeholder="No image" />'

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Added original image to Dashboard")
else:
    print("❌ Pattern not found")

input("Press Enter...")