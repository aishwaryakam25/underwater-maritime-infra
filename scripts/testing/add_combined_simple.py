file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Simple approach: just add import and component at the very end
if "import CombinedAnalysisMode" not in content:
    # Add import after InsightsPanel
    content = content.replace(
        "import InsightsPanel from './InsightsPanel';",
        "import InsightsPanel from './InsightsPanel';\nimport CombinedAnalysisMode from './CombinedAnalysisMode';"
    )
    print("✓ Added import")

# Find the export statement and add combined mode BEFORE it
if "CombinedAnalysisMode API={API}" not in content:
    export_line = "export default SonarAnalysis;"
    combined_section = '''
      {/* Combined Analysis Mode - Below main sonar UI */}
      <div style={{ marginTop: 40, paddingTop: 40, borderTop: '2px solid rgba(34,211,238,0.2)' }}>
        <CombinedAnalysisMode API={API} />
      </div>
    </div>
  );
}

'''
    content = content.replace(export_line, combined_section + export_line)
    print("✓ Added combined mode section")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Refresh browser - combined mode appears below sonar analysis.")
input("Press Enter...")