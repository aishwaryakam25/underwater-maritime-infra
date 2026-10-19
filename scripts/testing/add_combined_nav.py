file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Add import
if "import CombinedScan from './CombinedScan';" not in content:
    content = content.replace(
        "import WeldInspector from './WeldInspector';",
        "import WeldInspector from './WeldInspector';\nimport CombinedScan from './CombinedScan';"
    )
    print("✓ Import added")

# Step 2: Add tab button (find Sonar tab and add after it)
if 'tab === "combined"' not in content:
    sonar_btn = '<button className={tab === "sonar" ? "tab-btn active" : "tab-btn"} onClick={() => setTab("sonar")}>{SONAR_ICON} Sonar Analysis</button>'
    combined_btn = '\n            <button className={tab === "combined" ? "tab-btn active" : "tab-btn"} onClick={() => setTab("combined")}>🚀 Combined</button>'
    content = content.replace(sonar_btn, sonar_btn + combined_btn)
    print("✓ Tab button added")

# Step 3: Add route (find sonar route and add after)
if '{tab==="combined"&&<CombinedScan' not in content:
    sonar_route = '{tab==="sonar"&&<SonarAnalysis'
    pos = content.find(sonar_route)
    if pos != -1:
        end_line = content.find('\n', pos)
        combined_route = '\n            {tab==="combined"&&<CombinedScan API={API} />}'
        content = content[:end_line] + combined_route + content[end_line:]
        print("✓ Route added")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Refresh browser to see Combined tab.")
input("Press Enter...")