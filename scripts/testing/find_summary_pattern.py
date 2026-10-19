file_path = r"backend\sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Searching for return statements with 'summary'...\n")

for i, line in enumerate(lines, 1):
    if '"summary"' in line and 'return' not in line:
        start = max(0, i-3)
        end = min(len(lines), i+3)
        print(f"Found at line {i}:")
        print("="*60)
        for j in range(start, end):
            marker = ">>>" if j == i-1 else "   "
            print(f"{marker} {j+1:4d}: {lines[j].rstrip()}")
        print()

input("Press Enter to close...")