import re

file_path = r"app\pdf_report.py"

print("Reading pdf_report.py...")
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Search for the image positioning section
if "img_x" in content and "img_y" in content:
    print("✓ Found image positioning code")
    print("\nSearching for exact pattern...")
    
    # Show the user what was found
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'img_x' in line or 'img_y' in line or 'drawImage' in line:
            print(f"Line {i}: {line[:100]}")
else:
    print("❌ Pattern not found")

input("\nPress Enter to close...")