file_path = r"app\pdf_report.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Very specific, safe replacement - only the colWidths line
old = "], colWidths=[38*mm, 38*mm, 38*mm, 38*mm])"
new = "], colWidths=[44*mm, 44*mm, 44*mm, 44*mm])"

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Fixed table column widths")
else:
    print("Pattern not found - no changes made")

input("Press Enter...")