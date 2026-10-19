file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import
if "import CombinedScan from './CombinedScan';" not in content:
    content = content.replace(
        "import SonarAnalysis from './SonarAnalysis';",
        "import SonarAnalysis from './SonarAnalysis';\nimport CombinedScan from './CombinedScan';"
    )
    print("✓ Import added")

# Add route after sonar
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

print("\nDone!")
input("Press Enter...")