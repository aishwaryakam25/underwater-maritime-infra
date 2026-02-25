import requests, re
r = requests.get("https://www.nauticai-ai.com/", timeout=10)
html = r.text
imgs = re.findall(r'["\'](https?://[^"\'>\s]+\.(?:png|jpg|jpeg|svg|ico|webp)(?:\?[^"\'>\s]*)?)', html, re.I)
for u in sorted(set(imgs)):
    print(u)
# Also look for favicon link tags
favs = re.findall(r'<link[^>]+rel=["\'](?:icon|shortcut icon|apple-touch-icon)["\'][^>]+href=["\'](.*?)["\']', html, re.I)
for f in favs:
    print("FAVICON:", f)
# og:image
ogs = re.findall(r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:image["\']', html, re.I)
ogs += re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', html, re.I)
for o in ogs:
    print("OG:", o)
