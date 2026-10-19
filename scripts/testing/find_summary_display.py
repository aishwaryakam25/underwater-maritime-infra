file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Searching for batch summary or total detections display...\n")

for i, line in enumerate(lines, 1):
    if 'total_detections' in line.lower() or 'totaldets' in line.lower() or 'session detections' in line.lower():
        start = max(0, i-3)
        end = min(len(lines), i+5)
        print(f"Found at line {i}:")
        print("="*60)
        for j in range(start, end):
            marker = ">>>" if j == i-1 else "   "
            print(f"{marker} {j+1:4d}: {lines[j].rstrip()}")
        print("\n")

input("Press Enter...")