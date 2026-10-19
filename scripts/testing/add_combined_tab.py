file_path = r"frontend\src\App.jsx"

print("Adding CombinedScan tab to navigation...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

if "import CombinedScan from './CombinedScan';" not in content:
    weld_import = "import WeldInspector from './WeldInspector';"
    if weld_import in content:
        content = content.replace(
            weld_import,
            weld_import + "\nimport CombinedScan from './CombinedScan';"
        )
        print("✓ Added CombinedScan import")

if '"combined"' not in content or 'Combined Scan' not in content:
    sonar_tab = 'onClick={() => setTab("sonar")}>{SONAR_ICON} Sonar Analysis</button>'
    if sonar_tab in content:
        new_tab = '\n            <button className={tab === "combined" ? "tab-btn active" : "tab-btn"} onClick={() => setTab("combined")}>🚀 Combined Scan</button>'
        content = content.replace(sonar_tab, sonar_tab + new_tab)
        print("✓ Added Combined Scan tab button")

if '{tab==="sonar"&&<SonarAnalysis' in content and '{tab==="combined"' not in content:
    sonar_route = '{tab==="sonar"&&<SonarAnalysis'
    combined_route = '\n            {tab==="combined"&&<CombinedScan API={API} />}'
    pos = content.find(sonar_route)
    if pos != -1:
        end_line = content.find('\n', pos) + 1
        content = content[:end_line] + combined_route + content[end_line:]
        print("✓ Added Combined Scan route")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Refresh browser to see Combined Scan tab!")
input("Press Enter...")