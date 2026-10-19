file_path = r"backend\main.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Searching for enhanced_b64 lines...\n")

for i, line in enumerate(lines, 1):
    if 'enhanced_b64' in line:
        # Show 5 lines before and after
        start = max(0, i-6)
        end = min(len(lines), i+5)
        print(f"Found at line {i}:")
        print("="*60)
        for j in range(start, end):
            marker = ">>>" if j == i-1 else "   "
            print(f"{marker} {j+1:4d}: {lines[j].rstrip()}")
        print()

input("Press Enter...")