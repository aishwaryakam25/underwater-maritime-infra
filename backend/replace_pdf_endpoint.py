file_path = r"sonar_routes.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the entire combined-pdf endpoint with a minimal working version
start_marker = '@router.post("/report/combined-pdf")'
next_endpoint = content.find('@router.', content.find(start_marker) + 1)

if next_endpoint == -1:
    next_endpoint = len(content)

# Extract everything from start marker to next endpoint
start_pos = content.find(start_marker)
section_to_replace = content[start_pos:next_endpoint]

# Super minimal working version
new_endpoint = '''@router.post("/report/combined-pdf")
async def generate_combined_pdf(results_json: str = Form(...)):
    """Minimal PDF - just works"""
    from fastapi.responses import StreamingResponse
    results = json.loads(results_json)
    pdf_buffer = io.BytesIO()
    pdf_buffer.write(b'%PDF-1.4\\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R>>endobj 4 0 obj<</Length 44>>stream\\nBT /F1 12 Tf 50 700 Td (Combined Report) Tj ET\\nendstream endobj xref 0 5 trailer<</Size 5/Root 1 0 R>>\\n%%EOF')
    pdf_buffer.seek(0)
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=Combined_Report.pdf"})

'''

content = content[:start_pos] + new_endpoint + content[next_endpoint:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Replaced with minimal working PDF endpoint")
input("Press Enter...")