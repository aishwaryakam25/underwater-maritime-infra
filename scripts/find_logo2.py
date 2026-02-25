import requests, re

r = requests.get("https://www.nauticai-ai.com/", timeout=10)
html = r.text

# Find all squarespace image URLs
imgs = re.findall(r'["\x27](https?://images\.squarespace-cdn\.com[^"\x27\s>]+)', html, re.I)
# Also check static URLs  
static = re.findall(r'["\x27](https?://static1\.squarespace[^"\x27\s>]+)', html, re.I)

print("=== Squarespace CDN images ===")
for u in sorted(set(imgs)):
    print(u)

print("\n=== Static images ===")
for u in sorted(set(static)):
    print(u)

# Look for any image near the word NautiCAI or logo in the HTML
logo_ctx = re.findall(r'(?:logo|NautiCAI|brand|header-title).{0,500}', html, re.I | re.S)
print("\n=== Logo context snippets ===")
for ctx in logo_ctx[:5]:
    # find img/src within context
    srcs = re.findall(r'(?:src|href)=["\x27]([^"\x27]+)', ctx)
    for s in srcs:
        print(s)
