with open('frontend/src/App.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

old = '{tab==="road"&&<RoadmapPage />}'
new = '{tab==="road"&&<RoadmapPage />}\n            {tab==="weld"&&<WeldInspector />}'

if old in content:
    content = content.replace(old, new)
    with open('frontend/src/App.jsx', 'w', encoding='utf-8') as f:
        f.write(content)
    print("SUCCESS! Weld tab added!")
else:
    print("Pattern not found - searching...")
    idx = content.find('RoadmapPage')
    print(f"RoadmapPage found at index: {idx}")
    print(content[idx:idx+100])
