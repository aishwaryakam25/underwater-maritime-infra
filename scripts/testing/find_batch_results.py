file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Searching for batch results render section...\n")

for i, line in enumerate(lines, 1):
    if 'batchResults' in line and 'map' in line:
        start = max(0, i-5)
        end = min(len(lines), i+8)
        print(f"Found at line {i}:")
        print("="*60)
        for j in range(start, end):
            marker = ">>>" if j == i-1 else "   "
            print(f"{marker} {j+1:4d}: {lines[j].rstrip()}")
        print("\n")

input("Press Enter...")