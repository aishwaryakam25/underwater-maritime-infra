"""
Add insights to sonar batch analyze endpoint
"""

file_path = r"backend\sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# The exact pattern from line 619-624
old = '''    return {
        "total_images": len(results),
        "total_detections": sum(r.total_detections for r in results),
        "total_critical": sum(r.critical_count for r in results),
        "results": results,
    }'''

new = '''    return {
        "total_images": len(results),
        "total_detections": sum(r.total_detections for r in results),
        "total_critical": sum(r.critical_count for r in results),
        "results": results,
        "insights": generate_insights(results),
    }'''

if old in content:
    content = content.replace(old, new)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Added insights to sonar batch endpoint")
else:
    print("❌ Pattern not found - checking alternate spacing...")
    # Try with different spacing
    import re
    pattern = r'return \{\s+"total_images": len\(results\),\s+"total_detections".*?"results": results,\s+\}'
    if re.search(pattern, content, re.DOTALL):
        print("Found with regex - attempting fix...")
        # Add insights field before closing brace
        content = re.sub(
            r'("results": results,)\s+\}',
            r'\1\n        "insights": generate_insights(results),\n    }',
            content
        )
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ Added insights (regex method)")
    else:
        print("❌ Could not find pattern")

input("Press Enter...")
