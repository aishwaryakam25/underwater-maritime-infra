content = open('backend/detection.py').read()
content = content.replace('font = cv2.FONT_HERSHEY_SIMPLEX', 'font = cv2.FONT_HERSHEY_SIMPLEX\n    tag_s = 0.35')
open('backend/detection.py', 'w').write(content)
print('Fixed!')