file_path = r"frontend\src\SonarAnalysis.jsx"

print("Integrating Combined Analysis Mode into SonarAnalysis.jsx...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: Add import for CombinedAnalysisMode
if "import CombinedAnalysisMode from './CombinedAnalysisMode';" not in content:
    # Find InsightsPanel import and add after it
    insights_import = "import InsightsPanel from './InsightsPanel';"
    if insights_import in content:
        content = content.replace(
            insights_import,
            insights_import + "\nimport CombinedAnalysisMode from './CombinedAnalysisMode';"
        )
        print("✓ Added CombinedAnalysisMode import")
    else:
        # Fallback: add after React import
        content = content.replace(
            "import React",
            "import React, { useState } from 'react';\nimport CombinedAnalysisMode from './CombinedAnalysisMode'"
        )
        print("✓ Added imports (fallback method)")

# Step 2: Add mode state
# Find the first useState in the component
if "[analysisMode, setAnalysisMode] = useState('sonar')" not in content:
    # Add after the first existing useState
    first_usestate = content.find("useState(")
    if first_usestate != -1:
        end_of_line = content.find("\n", first_usestate)
        mode_state = "\n  const [analysisMode, setAnalysisMode] = useState('sonar'); // 'sonar' or 'combined'\n"
        content = content[:end_of_line+1] + mode_state + content[end_of_line+1:]
        print("✓ Added analysisMode state")

# Step 3: Add mode toggle button before the upload section
# Find the section header
section_marker = '<p className="section-desc">Side-Scan Sonar'
if section_marker in content and "analysisMode ===" not in content:
    toggle_ui = '''
      {/* Mode Toggle */}
      <div className="card mb-20">
        <div style={{ display: 'flex', gap: 8 }}>
          <button 
            className={analysisMode === 'sonar' ? 'btn btn-primary' : 'btn btn-ghost'}
            onClick={() => setAnalysisMode('sonar')}
          >
            🔊 Sonar Only
          </button>
          <button 
            className={analysisMode === 'combined' ? 'btn btn-primary' : 'btn btn-ghost'}
            onClick={() => setAnalysisMode('combined')}
          >
            🚀 Combined Analysis
          </button>
        </div>
        <div style={{ fontSize: 11, opacity: 0.5, marginTop: 8 }}>
          {analysisMode === 'sonar' ? 'Analyzing sonar images only (SubPipe + Marine-PULSE)' : 'Dual-model analysis: Sonar + Underwater Anomaly Detection'}
        </div>
      </div>

      {analysisMode === 'combined' ? (
        <CombinedAnalysisMode API={API} />
      ) : (
        <>
'''
    
    # Find where to insert (after section-desc paragraph)
    insert_pos = content.find(section_marker)
    if insert_pos != -1:
        # Find the end of the </p> tag
        end_p = content.find('</p>', insert_pos) + 4
        # Find the next line
        next_line = content.find('\n', end_p) + 1
        content = content[:next_line] + toggle_ui + content[next_line:]
        print("✓ Added mode toggle UI")

# Step 4: Add closing fragment for the conditional render
# Find near the end of the return statement, before the last closing div
if "analysisMode === 'combined'" in content and "</>)}" not in content:
    # Find the last </div> before the final closing of SonarAnalysis
    # This is tricky - let's just add it before the export statement
    export_pos = content.rfind("export default")
    if export_pos != -1:
        # Add the closing fragment just before
        content = content[:export_pos] + "        </>\n      )}\n    </div>\n  );\n}\n\n" + content[export_pos:]
        print("✓ Added conditional render closing")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Frontend integration complete.")
print("Refresh browser to see the mode toggle!")
input("Press Enter...")
