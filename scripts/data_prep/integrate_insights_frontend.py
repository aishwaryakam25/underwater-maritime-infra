"""
SONAR INSIGHTS FRONTEND INTEGRATION
====================================

STEP 1: Add InsightsPanel Component
------------------------------------

Download InsightsPanel.jsx and place it at:
C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\frontend\src\InsightsPanel.jsx

Using CMD:
cd "C:\Users\RAMNATH VENKAT\Downloads"
copy InsightsPanel.jsx "C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\frontend\src\"


STEP 2: Integrate into SonarAnalysis.jsx
-----------------------------------------

We need to:
1. Import the InsightsPanel component
2. Display it when results have insights

Run this automated script:
"""

file_path = r"frontend\src\SonarAnalysis.jsx"

print("Updating SonarAnalysis.jsx...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import at top
if "import InsightsPanel from './InsightsPanel';" not in content:
    # Find the first import and add after it
    import_pos = content.find("import React")
    if import_pos != -1:
        end_of_line = content.find("\n", import_pos)
        content = content[:end_of_line+1] + "import InsightsPanel from './InsightsPanel';\n" + content[end_of_line+1:]
        print("✓ Added InsightsPanel import")

# Find where to add the insights panel display
# Look for the results display section and add insights before it
# Search for "DETECTION OVERLAY" or similar section header

# Add insights display after batch results load
# Find: {batchResults && (
# Add InsightsPanel before the results map

search_text = "{batchResults && ("
if search_text in content:
    # Add insights panel right after {batchResults && (
    insert_code = "\n          {batchResults.insights && <InsightsPanel insights={batchResults.insights} />}\n"
    
    pos = content.find(search_text)
    if pos != -1:
        # Find the end of that line
        end_line = content.find("\n", pos)
        content = content[:end_line+1] + insert_code + content[end_line+1:]
        print("✓ Added InsightsPanel to render")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Frontend will auto-reload.")
print("Refresh browser and run Sonar Analysis to see insights!")
input("\nPress Enter...")
