file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Insert InsightsPanel before the image selector comment
marker = "          {/* Image selector for results */}"

if marker in content:
    insights_code = """
          {/* AI Analysis Insights */}
          {batchResults && batchResults.insights && (
            <InsightsPanel insights={batchResults.insights} />
          )}

"""
    content = content.replace(marker, insights_code + marker)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ Added InsightsPanel to render")
    print("Frontend will auto-reload - refresh browser to see it!")
else:
    print("❌ Marker not found")

input("Press Enter...")