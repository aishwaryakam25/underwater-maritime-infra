"""
Generate Comprehensive Video Analysis Batch Report
Creates detailed PDF with all frames, images, and detection tables
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import uuid

# Add backend to path
backend_path = r'C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\backend'
sys.path.insert(0, backend_path)

try:
    from detection import run_detection, annotate_image, build_heatmap, get_model_name
    from severity import compute_risk, score_to_grade, SEVERITY_MAP
    from enhancement import enhance_image
    from PIL import Image
    import glob
    
    # Import PDF libraries
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage, KeepTogether
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    
    print("✓ All imports successful")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTrying to continue without enhancement module...")
    try:
        from detection import run_detection, annotate_image, build_heatmap, get_model_name
        from severity import compute_risk, score_to_grade, SEVERITY_MAP
        from PIL import Image, ImageEnhance
        import glob
        
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage, KeepTogether
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        
        # Fallback enhancement function
        def enhance_image(img):
            """Simple enhancement using PIL"""
            enhancer = ImageEnhance.Contrast(img)
            enhanced = enhancer.enhance(1.3)
            enhancer = ImageEnhance.Brightness(enhanced)
            return enhancer.enhance(1.1)
        
        print("✓ Using fallback enhancement")
    except ImportError as e2:
        print(f"❌ Critical import error: {e2}")
        print("\nPlease install: pip install reportlab pillow")
        sys.exit(1)

# Configuration
IMAGE_FOLDER = r'C:\Users\RAMNATH VENKAT\Desktop\pipelineimages'
OUTPUT_PDF = r'C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\reports\Video_Analysis_Report.pdf'
TEMP_DIR = r'C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\temp_report_images'

# Create temp directory for processed images
os.makedirs(TEMP_DIR, exist_ok=True)

print(f"\n{'='*70}")
print("NautiCAI Video Analysis Comprehensive Report Generator")
print(f"{'='*70}\n")

# Find all images (remove duplicates)
image_files = []
seen_names = set()
for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
    for file in glob.glob(os.path.join(IMAGE_FOLDER, ext)):
        basename = os.path.basename(file)
        # Remove duplicates by checking unique part of filename
        unique_id = basename.split('.rf.')[1] if '.rf.' in basename else basename
        if unique_id not in seen_names:
            image_files.append(file)
            seen_names.add(unique_id)

image_files.sort()

if not image_files:
    print(f"❌ No images found in {IMAGE_FOLDER}")
    sys.exit(1)

print(f"📁 Found {len(image_files)} unique image files")
print(f"📄 Output PDF: {OUTPUT_PDF}\n")

# Generate mission ID
mission_id = f"VIDEO-{uuid.uuid4().hex[:8]}"
mission_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Process each image
all_results = []
total_detections = 0
severity_distribution = {'Critical': 0, 'High': 0, 'Medium': 0, 'Low': 0}

for idx, img_path in enumerate(image_files, 1):
    print(f"Processing {idx}/{len(image_files)}: {os.path.basename(img_path)[:50]}...", end=' ')
    
    try:
        # Load image
        img = Image.open(img_path)
        
        # Run detection
        detections = run_detection(img, conf_thr=0.25, iou_thr=0.45, mode="general")
        
        # Calculate risk
        risk_score = compute_risk(detections)
        grade = score_to_grade(risk_score)
        
        # Count severities
        for det in detections:
            sev = det.get('severity', 'Unknown')
            if sev in severity_distribution:
                severity_distribution[sev] += 1
        
        # Generate processed images
        enhanced_img = enhance_image(img)
        annotated_img = annotate_image(img.copy(), detections)
        heatmap_img = build_heatmap(img, detections)
        
        # Save processed images to temp directory
        base_name = f"frame_{idx:03d}"
        original_path = os.path.join(TEMP_DIR, f"{base_name}_original.jpg")
        enhanced_path = os.path.join(TEMP_DIR, f"{base_name}_enhanced.jpg")
        annotated_path = os.path.join(TEMP_DIR, f"{base_name}_annotated.jpg")
        heatmap_path = os.path.join(TEMP_DIR, f"{base_name}_heatmap.jpg")
        
        img.save(original_path, 'JPEG', quality=85)
        enhanced_img.save(enhanced_path, 'JPEG', quality=85)
        annotated_img.save(annotated_path, 'JPEG', quality=85)
        heatmap_img.save(heatmap_path, 'JPEG', quality=85)
        
        # Store results
        all_results.append({
            'filename': os.path.basename(img_path),
            'original_path': original_path,
            'enhanced_path': enhanced_path,
            'annotated_path': annotated_path,
            'heatmap_path': heatmap_path,
            'detections': detections,
            'risk_score': risk_score,
            'grade': grade
        })
        
        total_detections += len(detections)
        print(f"✓ {len(detections)} detections, Grade: {grade}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        continue

print(f"\n{'='*70}")
print(f"Processing Complete!")
print(f"Total Frames: {len(all_results)}")
print(f"Total Detections: {total_detections}")
print(f"Severity: Critical={severity_distribution['Critical']}, High={severity_distribution['High']}, Medium={severity_distribution['Medium']}, Low={severity_distribution['Low']}")
print(f"{'='*70}\n")

# Generate PDF Report
print("📝 Generating comprehensive PDF report...")

try:
    doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#0A4D68'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#666666'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#088F8F'),
        spaceAfter=12,
        spaceBefore=15,
        fontName='Helvetica-Bold'
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading3'],
        fontSize=11,
        textColor=colors.HexColor('#088F8F'),
        spaceAfter=8,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    # ============= COVER PAGE =============
    elements.append(Spacer(1, 0.8*inch))
    
    title = Paragraph("NautiCAI", title_style)
    elements.append(title)
    
    subtitle = Paragraph("Underwater Infrastructure Inspection Report", subtitle_style)
    elements.append(subtitle)
    
    # Mission info
    mission_info = f"Mission: {mission_id} | {mission_date}<br/>Model: {get_model_name()} | Vessel: Unknown"
    mission_para = Paragraph(mission_info, 
                            ParagraphStyle('Mission', parent=styles['Normal'], 
                                          fontSize=9, alignment=TA_CENTER,
                                          textColor=colors.HexColor('#666666')))
    elements.append(mission_para)
    elements.append(Spacer(1, 0.5*inch))
    
    # Add watermark
    watermark = Paragraph(
        "NautiCAI | Confidential — Authorised personnel only | Singapore Maritime AI Systems Pte. Ltd.",
        ParagraphStyle('Watermark', parent=styles['Normal'], 
                      fontSize=7, alignment=TA_CENTER, textColor=colors.grey)
    )
    elements.append(watermark)
    
    elements.append(Spacer(1, 0.5*inch))
    
    # ============= BATCH INSPECTION SUMMARY =============
    batch_title = Paragraph("VIDEO ANALYSIS REPORT", heading_style)
    elements.append(batch_title)
    
    batch_info_text = f"Mission {mission_id} | Vessel Unknown | Inspector NautiCAI AutoScan v1.0<br/>{mission_date} | Total Frames: {len(all_results)}"
    batch_info = Paragraph(batch_info_text,
                          ParagraphStyle('BatchInfo', parent=styles['Normal'],
                                        fontSize=9, alignment=TA_CENTER,
                                        textColor=colors.HexColor('#666666')))
    elements.append(batch_info)
    elements.append(Spacer(1, 0.3*inch))
    
    # Batch Summary Section
    summary_title = Paragraph("Batch Summary", section_title_style)
    elements.append(summary_title)
    
    # Summary stats
    grades_list = [r['grade'] for r in all_results]
    risk_scores = [int(r['risk_score']) for r in all_results]
    
    summary_text = f"Total Detections <b>{total_detections}</b><br/>"
    summary_text += f"High <b>{severity_distribution['High']}</b> Medium <b>{severity_distribution['Medium']}</b> Low <b>{severity_distribution['Low']}</b><br/>"
    summary_text += f"<b>{', '.join(grades_list)}</b> Risk Scores <b>{', '.join(map(str, risk_scores))}</b>"
    
    summary_para = Paragraph(summary_text,
                            ParagraphStyle('Summary', parent=styles['Normal'],
                                          fontSize=10, textColor=colors.HexColor('#333333')))
    elements.append(summary_para)
    
    elements.append(PageBreak())
    
    # ============= DETAILED RESULTS FOR EACH FRAME =============
    
    for idx, result in enumerate(all_results, 1):
        # Page header with mission info (repeated on each page)
        header = Paragraph("NautiCAI<br/><font size=8>Underwater Infrastructure Inspection Report</font>",
                          ParagraphStyle('Header', parent=styles['Normal'],
                                        fontSize=12, fontName='Helvetica-Bold',
                                        textColor=colors.HexColor('#0A4D68')))
        elements.append(header)
        
        mission_header = Paragraph(f"Mission: {mission_id} | {mission_date}<br/>Model: {get_model_name()} | Vessel: Unknown",
                                  ParagraphStyle('MissionHeader', parent=styles['Normal'],
                                                fontSize=8, alignment=TA_RIGHT,
                                                textColor=colors.HexColor('#666666')))
        elements.append(mission_header)
        elements.append(Spacer(1, 0.2*inch))
        
        # Image title
        image_title = Paragraph(f"Image {idx} — {result['filename']}", 
                               ParagraphStyle('ImageTitle', parent=styles['Heading2'],
                                            fontSize=14, textColor=colors.HexColor('#088F8F'),
                                            fontName='Helvetica-Bold', spaceAfter=12))
        elements.append(image_title)
        
        # Original Image
        elements.append(Paragraph("Original Image", section_title_style))
        try:
            orig_img = RLImage(result['original_path'], width=4*inch, height=3*inch)
            elements.append(orig_img)
        except:
            elements.append(Paragraph("[Image not available]", styles['Normal']))
        elements.append(Spacer(1, 0.15*inch))
        
        # Enhanced Image
        elements.append(Paragraph("Enhanced Image", section_title_style))
        try:
            enh_img = RLImage(result['enhanced_path'], width=4*inch, height=3*inch)
            elements.append(enh_img)
        except:
            elements.append(Paragraph("[Image not available]", styles['Normal']))
        elements.append(Spacer(1, 0.15*inch))
        
        # Annotated Image
        elements.append(Paragraph("Annotated Image", section_title_style))
        try:
            ann_img = RLImage(result['annotated_path'], width=4*inch, height=3*inch)
            elements.append(ann_img)
        except:
            elements.append(Paragraph("[Image not available]", styles['Normal']))
        elements.append(Spacer(1, 0.15*inch))
        
        # Heatmap
        elements.append(Paragraph("Heatmap", section_title_style))
        try:
            heat_img = RLImage(result['heatmap_path'], width=4*inch, height=3*inch)
            elements.append(heat_img)
        except:
            elements.append(Paragraph("[Image not available]", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        # Detection summary
        grade_color = {
            'A': colors.green,
            'B': colors.HexColor('#88C540'),
            'C': colors.orange,
            'D': colors.red,
            'F': colors.darkred
        }.get(result['grade'], colors.grey)
        
        summary_line = f"Grade: <font color='#{grade_color.hexval()[2:]}'><b>{result['grade']}</b></font> | Risk Score: <b>{int(result['risk_score'])}</b> | Total Detections: <b>{len(result['detections'])}</b>"
        elements.append(Paragraph(summary_line, 
                                 ParagraphStyle('DetSummary', parent=styles['Normal'],
                                               fontSize=10, fontName='Helvetica-Bold')))
        elements.append(Spacer(1, 0.1*inch))
        
        # Detections table
        if result['detections']:
            det_headers = ["#", "Defect Class", "Severity", "Conf.", "Bounding Box (px)", "Area (px²)"]
            det_rows = [det_headers]
            
            for det_idx, det in enumerate(result['detections'], 1):
                sev = det.get('severity', 'Unknown')
                sev_color = {
                    'Critical': colors.HexColor('#FFEBEE'),
                    'High': colors.HexColor('#FFF3E0'),
                    'Medium': colors.HexColor('#E3F2FD'),
                    'Low': colors.HexColor('#E8F5E9'),
                }.get(sev, colors.white)
                
                det_rows.append([
                    str(det_idx).zfill(2),
                    det.get('cls', 'Unknown'),
                    sev,
                    f"{det.get('conf', 0)*100:.1f}%",
                    f"({det.get('x1', 0)},{det.get('y1', 0)}) → ({det.get('x2', 0)},{det.get('y2', 0)})",
                    f"{det.get('area', 0):,}"
                ])
            
            det_table = Table(det_rows, colWidths=[0.4*inch, 1.3*inch, 0.9*inch, 0.7*inch, 2*inch, 0.9*inch])
            det_table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A4D68')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                
                # Data rows
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                
                # Severity column backgrounds
                ('BACKGROUND', (2, 1), (2, len(det_rows)-1), colors.white),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            elements.append(det_table)
        else:
            elements.append(Paragraph("<i>No detections found</i>", styles['Normal']))
        
        elements.append(Spacer(1, 0.1*inch))
        
        # Footer for each page
        footer = Paragraph(
            "NautiCAI | Confidential — Authorised personnel only | Singapore Maritime AI Systems Pte. Ltd.",
            ParagraphStyle('Footer', parent=styles['Normal'],
                          fontSize=7, alignment=TA_CENTER, textColor=colors.grey)
        )
        elements.append(footer)
        
        # Page break after each frame (except last)
        if idx < len(all_results):
            elements.append(PageBreak())
    
    # ============= FINAL SUMMARY PAGE =============
    elements.append(PageBreak())
    
    final_title = Paragraph("Batch Inspection Summary", heading_style)
    elements.append(final_title)
    elements.append(Spacer(1, 0.2*inch))
    
    final_summary = [
        [f"Total Images: {len(all_results)}"],
        [f"Total Detections: {total_detections}"],
        [f"Severity Distribution: {severity_distribution}"],
        [f"Grades: {', '.join(grades_list)}"],
        [f"Risk Scores: {', '.join(map(str, risk_scores))}"]
    ]
    
    for line in final_summary:
        elements.append(Paragraph(line[0], styles['Normal']))
        elements.append(Spacer(1, 0.1*inch))
    
    # Build PDF
    doc.build(elements)
    
    print(f"\n✅ PDF Report Generated Successfully!")
    print(f"📄 Location: {OUTPUT_PDF}")
    print(f"📄 Pages: ~{len(all_results) + 3} pages (cover + {len(all_results)} frames + summary)")
    print(f"\n{'='*70}")
    print(f"\n✓ You can now open: {OUTPUT_PDF}")
    
except Exception as e:
    print(f"❌ PDF generation failed: {e}")
    import traceback
    traceback.print_exc()

print("\nDone!")
