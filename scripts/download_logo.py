import requests

# Download the OG image (NautiCAI logo - dark navy square with text)
url = "http://static1.squarespace.com/static/68c686e016f6655da8dcfceb/t/68c69cbc5fc8910d74cb7e87/1757846716235/ChatGPT+Image+Sep+14%2C+2025%2C+06_44_56+PM.png?format=1500w"
r = requests.get(url, timeout=15)
print(f"Status: {r.status_code}, Size: {len(r.content)} bytes")
with open("frontend/public/nauticai-og.png", "wb") as f:
    f.write(r.content)
print("Saved to frontend/public/nauticai-og.png")

# Also try to download the 06_47_11 image and 06_56_57 image which might be the actual logo
for name, img_url in [
    ("img1.png", "https://images.squarespace-cdn.com/content/v1/68c686e016f6655da8dcfceb/99dd0e72-132b-45ac-9a20-24c7cebe2131/ChatGPT+Image+Sep+14%2C+2025%2C+06_47_11+PM.png"),
    ("img2.png", "https://images.squarespace-cdn.com/content/v1/68c686e016f6655da8dcfceb/c768c972-09a0-4d96-849b-dabdb7863c48/ChatGPT+Image+Sep+14%2C+2025%2C+06_56_57+PM.png"),
]:
    try:
        r2 = requests.get(img_url, timeout=15)
        with open(f"frontend/public/{name}", "wb") as f:
            f.write(r2.content)
        print(f"Saved {name}: {len(r2.content)} bytes")
    except Exception as e:
        print(f"Failed {name}: {e}")
