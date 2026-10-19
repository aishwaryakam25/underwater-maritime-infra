import re

file_path = r"frontend\src\App.jsx"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

print("Fixing VideoPage props...")

# Find where VideoPage is rendered and add the missing props
old_videopage = '<VideoPage videoFile={videoFile} videoRef={videoRef} setVideoFile={setVideoFile} onDragOver={onDragOver} onDragLeave={onDragLeave} analyzeVideo={analyzeVideo} genVideoPDF={genVideoPDF} sendVideoPDFToWa'

# Add isLiveTracking, handleLiveTracking, liveTrackingResult props
new_videopage = '<VideoPage videoFile={videoFile} videoRef={videoRef} setVideoFile={setVideoFile} onDragOver={onDragOver} onDragLeave={onDragLeave} analyzeVideo={analyzeVideo} genVideoPDF={genVideoPDF} sendVideoPDFToWa isLiveTracking={isLiveTracking} handleLiveTracking={handleLiveTracking} liveTrackingResult={liveTrackingResult}'

if old_videopage in content:
    content = content.replace(old_videopage, new_videopage)
    print("✓ Props added to VideoPage")
else:
    print("❌ Could not find exact VideoPage props pattern")
    # Try alternative
    pattern = r'(<VideoPage[^>]*videoFile=\{videoFile\}[^>]*)'
    if re.search(pattern, content):
        # Add props before closing >
        content = re.sub(pattern, r'\1 isLiveTracking={isLiveTracking} handleLiveTracking={handleLiveTracking} liveTrackingResult={liveTrackingResult}', content)
        print("✓ Props added via alternative method")

# Now update VideoPage function to accept these props
# Find VideoPage function definition
vp_func_pattern = r'(const VideoPage = \(\{[^}]*\}\) =>)'
if re.search(vp_func_pattern, content):
    # Add the new props to destructuring
    content = re.sub(
        r'const VideoPage = \(\{([^}]*)\}\)',
        r'const VideoPage = ({\1, isLiveTracking, handleLiveTracking, liveTrackingResult})',
        content
    )
    print("✓ VideoPage function updated to accept props")

# Save
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ FIXED! VideoPage will now receive isLiveTracking as prop")
print("Restart: cd frontend && npm start")