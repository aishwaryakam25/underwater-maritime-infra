from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import mm
from datetime import datetime

def calculate_biofouling_impact(
    vessel_name,
    vessel_imo,
    vessel_type,
    dwt_tonnes,
    route_km,
    fuel_type,
    biofouling_coverage_percent,
    biofouling_severity,  # 'Light', 'Medium', 'Heavy'
    output_path
):
    # ===== CALCULATIONS =====
    # Biofouling drag penalty lookup (based on IMO research)
    drag_penalty = {
        'Light': 0.10,   # 10% fuel penalty
        'Medium': 0.25,  # 25% fuel penalty
        'Heavy': 0.40,   # 40% fuel penalty
    }

    # Base fuel consumption (tonnes per 1000km) by vessel type
    base_fuel = {
        'Bulk Carrier': 25,
        'Container Ship': 35,
        'Tanker': 30,
        'Offshore Vessel': 15,
        'General Cargo': 20,
    }

    # CO2 emission factor per tonne of fuel
    co2_factor = {
        'HFO': 3.114,    # Heavy Fuel Oil
        'MGO': 3.206,    # Marine Gas Oil
        'LNG': 2.750,    # Liquefied Natural Gas
    }

    penalty = drag_penalty.get(biofouling_severity, 0.25)
    coverage_factor = biofouling_coverage_percent / 100
    effective_penalty = penalty * coverage_factor

    base_consumption = base_fuel.get(vessel_type, 25) * (route_km / 1000)
    extra_fuel = base_consumption * effective_penalty
    total_fuel = base_consumption + extra_fuel

    co2_per_tonne = co2_factor.get(fuel_type, 3.114)
    base_co2 = base_consumption * co2_per_tonne
    extra_co2 = extra_fuel * co2_per_tonne
    total_co2 = total_fuel * co2_per_tonne

    # Fuel cost (USD per tonne)
    fuel_cost_per_tonne = 650
    extra_cost = extra_fuel * fuel_cost_per_tonne

    # CII Score estimation (simplified)
    # CII = CO2 / (DWT x Distance)
    cii_clean = (base_co2) / (dwt_tonnes * route_km / 1000)
    cii_fouled = (total_co2) / (dwt_tonnes * route_km / 1000)

    def cii_rating(cii):
        if cii < 0.8: return 'A'
        elif cii < 0.95: return 'B'
        elif cii < 1.05: return 'C'
        elif cii < 1.15: return 'D'
        else: return 'E'

    rating_clean = cii_rating(cii_clean * 10)
    rating_fouled = cii_rating(cii_fouled * 10)

    # ===== PDF GENERATION =====
    doc = SimpleDocTemplate(output_path, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('T', parent=styles['Normal'], fontSize=18,
        textColor=colors.HexColor('#003366'), fontName='Helvetica-Bold', spaceAfter=4)
    subtitle_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=11,
        textColor=colors.HexColor('#003366'), fontName='Helvetica', spaceAfter=2)
    section_style = ParagraphStyle('Sec', parent=styles['Normal'], fontSize=12,
        textColor=colors.HexColor('#003366'), fontName='Helvetica-Bold',
        spaceBefore=8, spaceAfter=4)
    normal_style = ParagraphStyle('N', parent=styles['Normal'], fontSize=9,
        fontName='Helvetica', spaceAfter=3)

    # Header
    elements.append(Paragraph("NautiCAI", title_style))
    elements.append(Paragraph("AI-Powered Underwater Infrastructure Inspection", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366')))
    elements.append(Spacer(1, 4*mm))
    elements.append(Paragraph("BIOFOULING IMPACT & IMO CII COMPLIANCE REPORT", ParagraphStyle(
        'RT', parent=styles['Normal'], fontSize=14,
        textColor=colors.HexColor('#CC0000'), fontName='Helvetica-Bold', spaceAfter=6)))

    # Vessel Info
    elements.append(Paragraph("1. VESSEL & VOYAGE INFORMATION", section_style))
    vessel_data = [
        ['Vessel Name', vessel_name, 'Report Date', datetime.now().strftime('%d %B %Y')],
        ['IMO Number', vessel_imo, 'Vessel Type', vessel_type],
        ['DWT (tonnes)', f'{dwt_tonnes:,}', 'Fuel Type', fuel_type],
        ['Route Distance', f'{route_km:,} km', 'Biofouling Coverage', f'{biofouling_coverage_percent}%'],
    ]
    t = Table(vessel_data, colWidths=[40*mm, 55*mm, 40*mm, 45*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#003366')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (0,-1), colors.white),
        ('TEXTCOLOR', (2,0), (2,-1), colors.white),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 4*mm))

    # Fuel Impact
    elements.append(Paragraph("2. FUEL CONSUMPTION IMPACT", section_style))
    fuel_data = [
        ['Metric', 'Clean Hull (Baseline)', 'Fouled Hull (Current)', 'Extra Due to Fouling'],
        ['Fuel Consumption (tonnes)', f'{base_consumption:.1f}', f'{total_fuel:.1f}', f'+{extra_fuel:.1f}'],
        ['Fuel Cost (USD)', f'${base_consumption*fuel_cost_per_tonne:,.0f}', f'${total_fuel*fuel_cost_per_tonne:,.0f}', f'+${extra_cost:,.0f}'],
        ['CO2 Emissions (tonnes)', f'{base_co2:.1f}', f'{total_co2:.1f}', f'+{extra_co2:.1f}'],
        ['Drag Penalty', '0%', f'{effective_penalty*100:.1f}%', f'+{effective_penalty*100:.1f}%'],
    ]
    ft = Table(fuel_data, colWidths=[50*mm, 42*mm, 42*mm, 46*mm])
    ft.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 5),
        ('BACKGROUND', (3,1), (3,-1), colors.HexColor('#FFF0F0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F0F4FF')]),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(ft)
    elements.append(Spacer(1, 4*mm))

    # CII Score
    elements.append(Paragraph("3. IMO CARBON INTENSITY INDICATOR (CII) SCORE", section_style))

    rating_colors = {'A': '#4CAF50', 'B': '#8BC34A', 'C': '#FFC107', 'D': '#FF9800', 'E': '#F44336'}
    cii_data = [
        ['CII Metric', 'Clean Hull', 'Current (Fouled)'],
        ['CII Value', f'{cii_clean*10:.4f}', f'{cii_fouled*10:.4f}'],
        ['CII Rating', rating_clean, rating_fouled],
        ['MPA Singapore Status',
         'Compliant' if rating_clean in ['A','B','C'] else 'Non-Compliant',
         'Compliant' if rating_fouled in ['A','B','C'] else 'Non-Compliant'],
    ]
    ct = Table(cii_data, colWidths=[60*mm, 55*mm, 65*mm])
    ct.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 6),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('BACKGROUND', (1,2), (1,2), colors.HexColor(rating_colors.get(rating_clean, '#FFC107'))),
        ('BACKGROUND', (2,2), (2,2), colors.HexColor(rating_colors.get(rating_fouled, '#F44336'))),
        ('TEXTCOLOR', (1,2), (2,2), colors.white),
        ('FONTNAME', (1,2), (2,2), 'Helvetica-Bold'),
        ('FONTSIZE', (1,2), (2,2), 14),
    ]))
    elements.append(ct)
    elements.append(Spacer(1, 4*mm))

    # Recommendation
    elements.append(Paragraph("4. RECOMMENDATION", section_style))
    elements.append(Paragraph(
        f"Based on NautiCAI AI hull inspection, biofouling coverage of <b>{biofouling_coverage_percent}%</b> "
        f"({biofouling_severity} severity) is causing an estimated fuel penalty of "
        f"<b>{effective_penalty*100:.1f}%</b>, resulting in additional fuel cost of "
        f"<b>USD ${extra_cost:,.0f}</b> per voyage and <b>{extra_co2:.1f} tonnes</b> of excess CO2 emissions.",
        normal_style))
    elements.append(Spacer(1, 3*mm))

    rec = "IMMEDIATE HULL CLEANING RECOMMENDED" if biofouling_severity == 'Heavy' else \
          "HULL CLEANING RECOMMENDED WITHIN 30 DAYS" if biofouling_severity == 'Medium' else \
          "SCHEDULE HULL CLEANING AT NEXT PORT CALL"

    elements.append(Paragraph(f"<b>Action: {rec}</b>", ParagraphStyle(
        'Rec', parent=styles['Normal'], fontSize=11,
        textColor=colors.HexColor('#CC0000'), fontName='Helvetica-Bold')))

    elements.append(Spacer(1, 4*mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        "This report was auto-generated by NautiCAI AI Inspection System. "
        "CII calculations follow IMO MEPC.337(76) guidelines. "
        "Compliant with Singapore MPA Green Shipping Initiative.",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.grey)))

    doc.build(elements)
    print(f"✅ Biofouling CO2 Report generated: {output_path}")


# ===== TEST =====
calculate_biofouling_impact(
    vessel_name="MV Pacific Explorer",
    vessel_imo="IMO 9876543",
    vessel_type="Container Ship",
    dwt_tonnes=50000,
    route_km=15000,
    fuel_type="HFO",
    biofouling_coverage_percent=65,
    biofouling_severity="Heavy",
    output_path=r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\Biofouling_CO2_Report.pdf"
)