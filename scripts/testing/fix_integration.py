file_path = r"frontend\src\SonarAnalysis.jsx"

print("Updating SonarAnalysis.jsx...")

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import at top
if "import InsightsPanel from './InsightsPanel';" not in content:
    import_pos = content.find("import React")
    if import_pos != -1:
        end_of_line = content.find("\n", import_pos)
        content = content[:end_of_line+1] + "import InsightsPanel from './InsightsPanel';\n" + content[end_of_line+1:]
        print("✓ Added InsightsPanel import")

# Add insights panel to render
search_text = "{batchResults && ("
if search_text in content:
    insert_code = "\n          {batchResults.insights && <InsightsPanel insights={batchResults.insights} />}\n"
    pos = content.find(search_text)
    if pos != -1:
        end_line = content.find("\n", pos)
        content = content[:end_line+1] + insert_code + content[end_line+1:]
        print("✓ Added InsightsPanel to render")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Refresh browser to see insights panel.")
input("Press Enter...")