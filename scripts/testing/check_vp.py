file_path = r"frontend\src\App.jsx"
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

vp = content.find('const VideoPage')
if vp >= 0:
    print("VIDEOPAGE COMPONENT:")
    print(content[vp:vp+600])