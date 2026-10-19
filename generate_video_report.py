"""
Generate Batch PDF Report for Video Analysis
Processes all extracted frames and creates comprehensive report
"""
import sys
import os
from pathlib import Path
from datetime import datetime

# Add backend to path
backend_path = r'C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\backend'
sys.path.insert(0, backend_path)

try:
    from detection import run_detection, annotate_image, build_heatmap
    from severity import compute_risk, score_to_grade
    from PIL import Image
    import glob
    
    # Import PDF libraries
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    print("✓ All imports successful")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nPlease install missing packages:")
    print("pip install reportlab pillow --break-system-packages")
    sys.exit(1)

# Configuration
IMAGE_FOLDER = r'C:\Users\RAMNATH VENKAT\Desktop\pipelineimages'
OUTPUT_PDF = r'C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\reports\Video_Analysis_Batch_Report.pdf'

print(f"\n{'='*60}")
print("NautiCAI Video Analysis Batch Report Generator")
print(f"{'='*60}\n")

# Find all images
image_files = []
for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
    image_files.extend(glob.glob(os.path.join(IMAGE_FOLDER, ext)))

image_files.sort()

if not image_files:
    print(f"❌ No images found in {IMAGE_FOLDER}")
    sys.exit(1)

print(f"📁 Found {len(image_files)} image files")
print(f"📄 Output PDF: {OUTPUT_PDF}\n")

# Process each image
all_results = []
total_detections = 0

for idx, img_path in enumerate(image_files, 1):
    print(f"Processing {idx}/{len(image_files)}: {os.path.basename(img_path)}...", end=' ')
    
    try:
        # Load image
        img = Image.open(img_path)
        
        # Run detection
        detections = run_detection(img, conf_thr=0.25, iou_thr=0.45, mode="general")
        
        # Calculate risk
        risk_score = compute_risk(detections)
        grade = score_to_grade(risk_score)
        
        # Store results
        all_results.append({
            'filename': os.path.basename(img_path),
            'path': img_path,
            'detections': detections,
            'risk_score': risk_score,
            'grade': grade
        })
        
        total_detections += len(detections)
        print(f"✓ {len(detections)} detections, Grade: {grade}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        continue

print(f"\n{'='*60}")
print(f"Processing Complete!")
print(f"Total Images: {len(all_results)}")
print(f"Total Detections: {total_detections}")
print(f"{'='*60}\n")

# Generate PDF Report
print("📝 Generating PDF report...")

try:
    doc = SimpleDocTemplate(OUTPUT_PDF, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=18)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0A4D68'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#0A4D68'),
        spaceAfter=12,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    # Title Page
    elements.append(Spacer(1, 1.5*inch))
    title = Paragraph("NautiCAI", title_style)
    elements.append(title)
    
    subtitle = Paragraph("Video Analysis Batch Report", 
                        ParagraphStyle('Subtitle', parent=styles['Normal'], 
                                      fontSize=14, alignment=TA_CENTER,
                                      textColor=colors.HexColor('#088F8F')))
    elements.append(subtitle)
    elements.append(Spacer(1, 0.5*inch))
    
    # Summary info
    summary_data = [
        ["Mission Date:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        ["Total Images:", str(len(all_results))],
        ["Total Detections:", str(total_detections)],
        ["Source:", "Video Frame Extraction"],
    ]
    
    summary_table = Table(summary_data, colWidths=[2*inch, 4*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(summary_table)
    elements.append(PageBreak())
    
    # Summary Table
    summary_title = Paragraph("Batch Summary", heading_style)
    elements.append(summary_title)
    elements.append(Spacer(1, 0.2*inch))
    
    summary_rows = [["#", "Filename", "Detections", "Grade", "Risk Score"]]
    for idx, result in enumerate(all_results, 1):
        summary_rows.append([
            str(idx),
            result['filename'][:40] + "..." if len(result['filename']) > 40 else result['filename'],
            str(len(result['detections'])),
            result['grade'],
            f"{result['risk_score']:.0f}"
        ])
    
    summary_table = Table(summary_rows, colWidths=[0.5*inch, 3*inch, 1*inch, 0.7*inch, 1*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0A4D68')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    
    # Build PDF
    doc.build(elements)
    
    print(f"\n✅ PDF Report Generated Successfully!")
    print(f"📄 Location: {OUTPUT_PDF}")
    print(f"\n{'='*60}")
    
except Exception as e:
    print(f"❌ PDF generation failed: {e}")
    import traceback
    traceback.print_exc()