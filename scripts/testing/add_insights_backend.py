"""
Add insights generation to sonar PDF endpoint
This script updates sonar_routes.py to include analysis insights
"""

# Instructions:
# 1. Copy sonar_insights.py to backend/ folder
# 2. Run this script to update sonar_routes.py
# 3. Backend will auto-reload

import re

file_path = r"backend\sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add import at the top (after other imports)
if "from sonar_insights import generate_insights" not in content:
    # Find the last import line
    import_section = content.split('\n\n')[0]
    new_import = import_section + "\nfrom sonar_insights import generate_insights\n"
    content = content.replace(import_section, new_import, 1)
    print("✓ Added insights import")

# Add insights to the return dict in generate_sonar_pdf
# Find the return statement and add insights field
old_return_pattern = r'(return StreamingResponse\(\s+io\.BytesIO\(pdf_bytes\))'

# Before we return the PDF, we need to add insights to the response
# But wait - we're returning a PDF, not JSON. We need to add insights to the
# analyze_batch endpoint instead, which returns JSON with the results.

# Let's find the analyze_batch endpoint return statement
search_pattern = r'"summary":\s*summary_stats'
if re.search(search_pattern, content):
    # Add insights after summary
    old = '"summary": summary_stats'
    new = '"summary": summary_stats,\n        "insights": generate_insights(results)'
    content = re.sub(old, new, content)
    print("✓ Added insights to analyze_batch response")
else:
    print("⚠ analyze_batch pattern not found - check manually")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! Backend will auto-reload.")
print("Next: Update frontend to display insights")
