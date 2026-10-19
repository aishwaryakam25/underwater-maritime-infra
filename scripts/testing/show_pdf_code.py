file_path = r"app\pdf_report.py"

print("Reading pdf_report.py...")
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"\nTotal lines: {len(lines)}")
print("\nSearching for image-related code...\n")

for i, line in enumerate(lines, 1):
    lower = line.lower()
    if any(word in lower for word in ['image', 'draw', 'width', 'height', '200', '180', '165', '220']):
        print(f"Line {i}: {line.rstrip()}")

input("\nPress Enter to close...")