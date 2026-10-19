file_path = r"App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("TABS array structure:\n")
print("="*60)

for i in range(13, min(40, len(lines))):
    print(f"{i+1:4d}: {lines[i].rstrip()}")
    if '];' in lines[i]:
        break

input("\nPress Enter...")