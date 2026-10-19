file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Searching for button variations...")

searches = [
    'Analyze Video',
    'Analyze',
    'Video',
    'button className',
    'onClick=',
]

for search in searches:
    count = content.count(search)
    print(f"{search}: {count} occurrences")

# Show all button-like code
import re
buttons = re.findall(r'<button[^>]*>[^<]*</button>', content)
print(f"\nFound {len(buttons)} button elements")
print("\nFirst 5 buttons:")
for i, btn in enumerate(buttons[:5], 1):
    print(f"{i}. {btn}")