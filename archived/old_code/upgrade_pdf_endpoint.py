file_path = r"backend\sonar_routes.py"

print("Upgrading combined PDF to show full analysis data...")

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the minimal PDF endpoint and replace with enhanced version
found = False
start_line = -1

for i, line in enumerate(lines):
    if '@router.post("/report/combined-pdf")' in line:
        found = True
        start_line = i
        break

if not found:
    print("❌ Endpoint not found")
    input("Press Enter...")
    exit()

# Find the end of this function (next @router or end of file)
end_line = len(lines)
for i in range(start_line + 1, len(lines)):
    if lines[i].strip().startswith('@router.'):
        end_line = i
        break

# Enhanced endpoint code
enhanced = '''@router.post("/report/combined-pdf")
async def generate_combined_pdf(
    results_json: str = Form(...),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
):
    """Enhanced combined PDF with full analysis data"""
    from fastapi.responses import StreamingResponse
    
    if not REPORTLAB_AVAILABLE:
        return StreamingResponse(io.BytesIO(b'%PDF-1.4\\nBasic PDF'), media_type="application/pdf")
    
    results = json.loads(results_json)
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, leftMargin=18*mm, rightMargin=18*mm, topMargin=24*mm, bottomMargin=16*mm)
    ST = _pdf_styles()
    story = []
    usable_w = PAGE_W - 36*mm
    
    # Title
    story.append(Paragraph("NautiCAI Combined Analysis Report", ParagraphStyle('MainTitle', fontName='Helvetica-Bold', fontSize=22, textColor=colors.HexColor('#22d3ee'), spaceAfter=6*mm)))
    
    # Metadata
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    story.append(Paragraph(f"<b>Vessel:</b> {vessel_name}  |  <b>Inspector:</b> {inspector}  |  <b>Date:</b> {ts}", ST['body']))
    story.append(Spacer(1, 8*mm))
    
    # Summary
    summary = results.get('combined_summary', {})
    sum_data = [['Total Images', str(summary.get('total_images', 0)), 'Total Detections', str(summary.get('total_detections', 0))],
                ['Sonar Images', str(results.get('sonar', {}).get('total_images', 0)), 'Anomaly Images', str(results.get('anomaly', {}).get('total_images', 0))]]
    sum_tbl = Table(sum_data, colWidths=[44*mm]*4)
    sum_tbl.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d2a4a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    story.append(sum_tbl)
    story.append(Spacer(1, 10*mm))
    
    # Sonar Results
    story.append(Paragraph("🔊 Sonar Detection Results", ST['h2']))
    story.append(Spacer(1, 4*mm))
    for idx, r in enumerate(results.get('sonar', {}).get('results', []), 1):
        story.append(Paragraph(f"<b>Image {idx}:</b> {r.get('filename', 'Unknown')}", ST['body']))
        story.append(Paragraph(f"Total: {r.get('total_detections', 0)} | Critical: {r.get('critical_count', 0)} | High: {r.get('high_count', 0)}", ST['body_sm']))
        for det in r.get('detections', [])[:5]:
            story.append(Paragraph(f"  • {det.get('class_name', 'Unknown')} - {det.get('severity', 'N/A')} - {det.get('confidence', 0)*100:.1f}%", ST['body_sm']))
        story.append(Spacer(1, 5*mm))
    
    story.append(PageBreak())
    
    # Anomaly Results
    story.append(Paragraph("🔍 Underwater Anomaly Results", ST['h2']))
    story.append(Spacer(1, 4*mm))
    for idx, r in enumerate(results.get('anomaly', {}).get('results', []), 1):
        story.append(Paragraph(f"<b>Image {idx}:</b> {r.get('filename', 'Unknown')}", ST['body']))
        story.append(Paragraph(f"Total: {r.get('total_detections', 0)} | Grade: {r.get('grade', 'N/A')} | Risk: {r.get('risk_score', 0)}%", ST['body_sm']))
        for det in r.get('detections', [])[:5]:
            cn = det.get('class_name') or det.get('cls', 'Unknown')
            conf = det.get('confidence') or det.get('conf', 0)
            story.append(Paragraph(f"  • {cn} - {det.get('severity', 'N/A')} - {conf*100:.1f}%", ST['body_sm']))
        story.append(Spacer(1, 5*mm))
    
    # Footer
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("NautiCAI | Singapore Maritime AI Systems | Confidential", ParagraphStyle('Footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)))
    
    doc.build(story)
    pdf_buffer.seek(0)
    
    filename = f"NautiCAI_Combined_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

'''

# Replace the minimal version
new_lines = lines[:start_line] + [enhanced] + lines[end_line:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✓ Upgraded PDF endpoint to show full analysis data")
print("Backend will auto-reload. Refresh browser and download PDF again!")
input("Press Enter...")
