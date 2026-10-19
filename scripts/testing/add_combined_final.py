file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Add import
if "import CombinedScan from './CombinedScan';" not in content:
    content = content.replace(
        "import SonarAnalysis from './SonarAnalysis';",
        "import SonarAnalysis from './SonarAnalysis';\nimport CombinedScan from './CombinedScan';"
    )
    print("✓ Import added")

# Step 2: Add to TABS array (after sonar, before roadmap)
old_tabs = '  { id: "sonar", icon: "S", label: "Sonar Analysis" },\n  { id: "road", icon: "🗺️", label: "Roadmap" },'
new_tabs = '  { id: "sonar", icon: "S", label: "Sonar Analysis" },\n  { id: "combined", icon: "🚀", label: "Combined" },\n  { id: "road", icon: "🗺️", label: "Roadmap" },'

if old_tabs in content:
    content = content.replace(old_tabs, new_tabs)
    print("✓ Tab added to TABS array")

# Step 3: Add route (after sonar route)
if '{tab==="combined"&&<CombinedScan' not in content:
    sonar_route = '{tab==="sonar"&&<SonarAnalysis'
    pos = content.find(sonar_route)
    if pos != -1:
        end_line = content.find('\n', pos)
        combined_route = '\n            {tab==="combined"&&<CombinedScan />}'
        content = content[:end_line] + combined_route + content[end_line:]
        print("✓ Route added")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Refresh browser - Combined tab will appear!")
input("Press Enter...")