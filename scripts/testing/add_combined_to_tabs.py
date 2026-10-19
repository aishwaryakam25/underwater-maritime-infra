file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add to TABS array
old = '  { id: "sonar", icon: "S", label: "Sonar Analysis" },\n  { id: "road", icon: "🗺️", label: "Roadmap" },'
new = '  { id: "sonar", icon: "S", label: "Sonar Analysis" },\n  { id: "combined", icon: "🚀", label: "Combined" },\n  { id: "road", icon: "🗺️", label: "Roadmap" },'

if 'id: "combined"' not in content:
    content = content.replace(old, new)
    print("✓ Added Combined tab")
else:
    print("Already exists")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

input("Press Enter...")