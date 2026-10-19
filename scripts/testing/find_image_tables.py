file_path = r"app\pdf_report.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Searching for image table structures...\n")

# Find lines around image table creation
in_image_section = False
for i, line in enumerate(lines, 1):
    if 'img_frame = Table' in line or 'hmap_frame = Table' in line or '_pil_to_rl' in line:
        # Show context: 5 lines before and 10 lines after
        start = max(0, i-6)
        end = min(len(lines), i+10)
        print(f"\n{'='*60}")
        print(f"Found at line {i}:")
        print('='*60)
        for j in range(start, end):
            marker = ">>>" if j == i-1 else "   "
            print(f"{marker} {j+1:4d}: {lines[j].rstrip()}")

input("\nPress Enter to close...")