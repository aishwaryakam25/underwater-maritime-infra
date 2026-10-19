file_path = r"frontend\src\SonarAnalysis.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Checking SonarAnalysis.jsx...")
print("\n1. Live Tracking State:")
print("   Found" if 'isLiveTracking' in content else "   NOT FOUND ❌")

print("\n2. Live Tracking Function:")
print("   Found" if 'handleLiveTracking' in content else "   NOT FOUND ❌")

print("\n3. Live Tracking Button:")
print("   Found" if 'Live Tracking</button>' in content or 'Live Tracking"' in content else "   NOT FOUND ❌")

print("\n4. WhatsApp Button:")
print("   REMOVED ✓" if 'WhatsApp' not in content else "   STILL THERE ❌")

# Find the buttons section
import re
buttons = re.search(r'Analyze Video</button>(.{200})', content, re.DOTALL)
if buttons:
    print("\n5. Buttons section preview:")
    print(buttons.group(0)[:300])