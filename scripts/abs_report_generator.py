from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import mm
from datetime import datetime

def generate_abs_report(vessel_name, vessel_imo, inspector, detections, output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title Style
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Normal'],
        fontSize=18,
        textColor=colors.HexColor('#003366'),
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#003366'),
        spaceAfter=2,
        fontName='Helvetica'
    )
    section_style = ParagraphStyle(
        'Section',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#003366'),
        spaceBefore=10,
        spaceAfter=4,
        fontName='Helvetica-Bold'
    )
    normal_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        spaceAfter=3,
        fontName='Helvetica'
    )

    # Header
    elements.append(Paragraph("NautiCAI", title_style))
    elements.append(Paragraph("AI-Powered Underwater Infrastructure Inspection", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366')))
    elements.append(Spacer(1, 5*mm))

    # Report Title
    elements.append(Paragraph("ABS / DNV CLASS SOCIETY INSPECTION REPORT", ParagraphStyle(
        'ReportTitle',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#CC0000'),
        fontName='Helvetica-Bold',
        spaceAfter=6
    )))

    # Vessel Info Table
    elements.append(Paragraph("1. VESSEL INFORMATION", section_style))
    vessel_data = [
        ['Vessel Name', vessel_name, 'Report Date', datetime.now().strftime('%d %B %Y')],
        ['IMO Number', vessel_imo, 'Inspector', inspector],
        ['Inspection Type', 'Underwater Hull & Pipeline', 'Classification', 'ABS / DNV'],
        ['AI Model', 'NautiCAI YOLOv8m-seg v1.0', 'Confidence Threshold', '0.50'],
    ]
    vessel_table = Table(vessel_data, colWidths=[40*mm, 55*mm, 40*mm, 45*mm])
    vessel_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#003366')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('TEXTCOLOR', (2,0), (2,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(vessel_table)
    elements.append(Spacer(1, 5*mm))

    # Defect Summary
    elements.append(Paragraph("2. DEFECT DETECTION SUMMARY", section_style))

    total = len(detections)
    critical = sum(1 for d in detections if d['severity'] == 'Critical')
    moderate = sum(1 for d in detections if d['severity'] == 'Moderate')
    minor = sum(1 for d in detections if d['severity'] == 'Minor')

    summary_data = [
        ['Total Defects Detected', 'Critical', 'Moderate', 'Minor'],
        [str(total), str(critical), str(moderate), str(minor)],
    ]
    summary_table = Table(summary_data, colWidths=[47*mm, 47*mm, 47*mm, 47*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BACKGROUND', (1,1), (1,1), colors.HexColor('#FF4444')),
        ('BACKGROUND', (2,1), (2,1), colors.HexColor('#FFA500')),
        ('BACKGROUND', (3,1), (3,1), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (1,1), (3,1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 11),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 5*mm))

    # Detailed Defect Table
    elements.append(Paragraph("3. DETAILED DEFECT LOG", section_style))
    defect_data = [['#', 'Defect Class', 'Location', 'Confidence', 'Severity', 'Action Required']]
    for i, d in enumerate(detections):
        defect_data.append([
            str(i+1),
            d['class'],
            d['location'],
            f"{d['confidence']:.0%}",
            d['severity'],
            d['action']
        ])

    defect_table = Table(defect_data, colWidths=[10*mm, 35*mm, 35*mm, 22*mm, 22*mm, 56*mm])
    defect_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 4),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0F4FF')]),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(defect_table)
    elements.append(Spacer(1, 5*mm))

    # Compliance Status
    elements.append(Paragraph("4. ABS / DNV COMPLIANCE STATUS", section_style))
    status = "CONDITIONAL PASS" if critical == 0 else "REQUIRES IMMEDIATE ATTENTION"
    status_color = colors.HexColor('#FFA500') if critical == 0 else colors.HexColor('#CC0000')
    elements.append(Paragraph(f"Overall Status: <font color='red'><b>{status}</b></font>", normal_style))
    elements.append(Spacer(1, 3*mm))

    compliance_data = [
        ['ABS Rule', 'Requirement', 'Status'],
        ['Part 7, Section 3', 'Hull structural integrity', '✓ Compliant' if critical == 0 else '✗ Review Required'],
        ['Part 6, Section 1', 'Pipeline leak-free operation', '✓ Compliant' if not any(d['class']=='Leakage' for d in detections) else '✗ Leakage Detected'],
        ['Part 5, Section 2', 'Corrosion within limits', '✓ Compliant' if moderate < 3 else '✗ Exceeds Threshold'],
        ['IMO Resolution A.744', 'Enhanced Survey Programme', '✓ Survey Complete'],
    ]
    compliance_table = Table(compliance_data, colWidths=[50*mm, 80*mm, 60*mm])
    compliance_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0F4FF')]),
    ]))
    elements.append(compliance_table)
    elements.append(Spacer(1, 5*mm))

    # Footer
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "This report was auto-generated by NautiCAI AI Inspection System. "
        "All detections are based on YOLOv8m-seg model inference. "
        "This report is confidential and intended for classification society use only.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.grey)
    ))

    doc.build(elements)
    print(f"✅ ABS/DNV Report generated: {output_path}")


# ===== TEST DATA =====
sample_detections = [
    {'class': 'Leakage', 'location': 'Frame 45, Port Side', 'confidence': 0.87, 'severity': 'Critical', 'action': 'Immediate repair required'},
    {'class': 'Corrosion', 'location': 'Frame 12, Starboard', 'confidence': 0.76, 'severity': 'Moderate', 'action': 'Monitor and schedule repair'},
    {'class': 'Pipeline', 'location': 'Section B, Mid-ship', 'confidence': 0.91, 'severity': 'Minor', 'action': 'Routine maintenance'},
    {'class': 'Biofouling', 'location': 'Hull Bottom, Aft', 'confidence': 0.82, 'severity': 'Moderate', 'action': 'Hull cleaning recommended'},
    {'class': 'Pipe Coupling', 'location': 'Frame 78, Centre', 'confidence': 0.69, 'severity': 'Minor', 'action': 'Inspect at next dry dock'},
]

generate_abs_report(
    vessel_name="MV Pacific Explorer",
    vessel_imo="IMO 9876543",
    inspector="NautiCAI Automated System",
    detections=sample_detections,
    output_path=r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\ABS_DNV_Report.pdf"
)