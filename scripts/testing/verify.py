file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("CHECKING FILE CONTENTS...")

# Find buttons section
idx = content.find('Analyze Video')
if idx > 0:
    print("\nButtons section:")
    print(content[idx:idx+800])
else:
    print("Could not find Analyze Video")

print("\n\nChecklist:")
print(f"Live Tracking: {'Found' if 'Live Tracking' in content else 'Missing'}")
print(f"WhatsApp: {'Still there' if 'WhatsApp' in content else 'Removed'}")