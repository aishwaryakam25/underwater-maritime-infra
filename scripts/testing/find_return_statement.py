file_path = r"backend\sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("Searching for return statements in sonar endpoints...\n")

for i, line in enumerate(lines, 1):
    if 'return {' in line or 'return JSONResponse' in line:
        start = max(0, i-2)
        end = min(len(lines), i+15)
        print(f"Found return at line {i}:")
        print("="*60)
        for j in range(start, end):
            marker = ">>>" if j == i-1 else "   "
            print(f"{marker} {j+1:4d}: {lines[j].rstrip()}")
        print("\n")

input("Press Enter...")