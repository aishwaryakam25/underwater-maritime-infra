file_path = r"App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add Combined tab to the TABS array after sonar
old = '  { id: "sonar", icon: "S", label: "Sonar Analysis" },\n  { id: "road", icon: "🗺️", label: "Roadmap" },'

new = '  { id: "sonar", icon: "S", label: "Sonar Analysis" },\n  { id: "combined", icon: "🚀", label: "Combined" },\n  { id: "road", icon: "🗺️", label: "Roadmap" },'

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Added Combined tab to TABS array")
else:
    print("❌ Pattern not found")

input("Press Enter...")