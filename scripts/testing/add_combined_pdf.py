file_path = r"backend\sonar_routes.py"

endpoint_code = '''

@router.post("/report/combined-pdf")
async def generate_combined_pdf(
    results_json: str = Form(...),
    vessel_name: str = Form("Unknown"),
    inspector: str = Form("NautiCAI AutoScan v1.0"),
):
    """Generate PDF for combined analysis"""
    import json
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    
    results = json.loads(results_json)
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=20, textColor=colors.HexColor('#22d3ee'))
    story.append(Paragraph("NautiCAI Combined Analysis Report", title_style))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(f"Vessel: {vessel_name} | Inspector: {inspector}", styles['Normal']))
    story.append(Paragraph(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 8*mm))
    
    summary = results.get('combined_summary', {})
    summary_data = [['Total Images', str(summary.get('total_images', 0)), 'Total Detections', str(summary.get('total_detections', 0))]]
    summary_table = Table(summary_data, colWidths=[44*mm]*4)
    summary_table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0d2a4a')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.grey), ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    story.append(summary_table)
    story.append(Spacer(1, 10*mm))
    
    story.append(Paragraph("Sonar Results", styles['Heading2']))
    for idx, r in enumerate(results.get('sonar', {}).get('results', []), 1):
        story.append(Paragraph(f"Image {idx}: {r.get('filename', '')} - {r.get('total_detections', 0)} detections", styles['Normal']))
        story.append(Spacer(1, 3*mm))
    
    story.append(PageBreak())
    story.append(Paragraph("Anomaly Results", styles['Heading2']))
    for idx, r in enumerate(results.get('anomaly', {}).get('results', []), 1):
        story.append(Paragraph(f"Image {idx}: {r.get('filename', '')} - {r.get('total_detections', 0)} detections - Grade: {r.get('grade', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 3*mm))
    
    doc.build(story)
    pdf_buffer.seek(0)
    
    filename = f"NautiCAI_Combined_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(pdf_buffer, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})
'''

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

if "/report/combined-pdf" not in content:
    content = content.rstrip() + '\n' + endpoint_code + '\n'
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Added combined PDF endpoint")
else:
    print("Already exists")

input("Press Enter...")
