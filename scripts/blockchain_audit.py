import hashlib
import json
import time
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import mm

class Block:
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

class InspectionBlockchain:
    def __init__(self):
        self.chain = [self.create_genesis_block()]

    def create_genesis_block(self):
        return Block(0, str(datetime.now()), {
            "type": "GENESIS",
            "message": "NautiCAI Inspection Blockchain Initialized",
            "created_by": "NautiCAI System"
        }, "0")

    def get_latest_block(self):
        return self.chain[-1]

    def add_inspection_record(self, vessel_name, vessel_imo, inspector, detections, location):
        data = {
            "type": "INSPECTION_RECORD",
            "vessel_name": vessel_name,
            "vessel_imo": vessel_imo,
            "inspector": inspector,
            "location": location,
            "inspection_date": str(datetime.now()),
            "total_defects": len(detections),
            "detections": detections,
            "model_version": "NautiCAI-YOLOv8m-seg-v1.0"
        }
        new_block = Block(
            index=len(self.chain),
            timestamp=str(datetime.now()),
            data=data,
            previous_hash=self.get_latest_block().hash
        )
        self.chain.append(new_block)
        print(f"✅ Block #{new_block.index} added | Hash: {new_block.hash[:20]}...")
        return new_block

    def verify_chain(self):
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            if current.hash != current.calculate_hash():
                return False, f"Block #{i} has been tampered!"
            if current.previous_hash != previous.hash:
                return False, f"Block #{i} broken chain link!"
        return True, "Chain is valid and untampered ✅"

    def generate_audit_report(self, output_path):
        is_valid, validation_msg = self.verify_chain()

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
        mono_style = ParagraphStyle('M', parent=styles['Normal'], fontSize=7,
            fontName='Courier', spaceAfter=2, textColor=colors.HexColor('#333333'))

        # Header
        elements.append(Paragraph("NautiCAI", title_style))
        elements.append(Paragraph("AI-Powered Underwater Infrastructure Inspection", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#003366')))
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph("BLOCKCHAIN TAMPER-PROOF INSPECTION AUDIT TRAIL", ParagraphStyle(
            'RT', parent=styles['Normal'], fontSize=14,
            textColor=colors.HexColor('#CC0000'), fontName='Helvetica-Bold', spaceAfter=6)))

        # Chain Status
        elements.append(Paragraph("1. BLOCKCHAIN INTEGRITY STATUS", section_style))
        status_color = colors.HexColor('#4CAF50') if is_valid else colors.HexColor('#F44336')
        status_data = [
            ['Total Blocks', 'Chain Status', 'Validation', 'Generated'],
            [str(len(self.chain)),
             'INTACT' if is_valid else 'COMPROMISED',
             validation_msg,
             datetime.now().strftime('%d %B %Y %H:%M')],
        ]
        st = Table(status_data, colWidths=[30*mm, 35*mm, 75*mm, 40*mm])
        st.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#003366')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('BACKGROUND', (1,1), (1,1), status_color),
            ('TEXTCOLOR', (1,1), (1,1), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 5),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        elements.append(st)
        elements.append(Spacer(1, 4*mm))

        # Block Records
        elements.append(Paragraph("2. INSPECTION RECORDS ON CHAIN", section_style))
        for block in self.chain:
            elements.append(Paragraph(f"Block #{block.index} — {block.data.get('type', 'UNKNOWN')}", ParagraphStyle(
                'BH', parent=styles['Normal'], fontSize=10,
                textColor=colors.HexColor('#003366'), fontName='Helvetica-Bold',
                spaceBefore=4, spaceAfter=2)))

            block_data = [
                ['Timestamp', block.timestamp],
                ['Hash', block.hash],
                ['Previous Hash', block.previous_hash],
            ]
            if block.data.get('type') == 'INSPECTION_RECORD':
                block_data += [
                    ['Vessel', f"{block.data['vessel_name']} ({block.data['vessel_imo']})"],
                    ['Inspector', block.data['inspector']],
                    ['Location', block.data['location']],
                    ['Defects Found', str(block.data['total_defects'])],
                    ['AI Model', block.data['model_version']],
                ]

            bt = Table(block_data, colWidths=[35*mm, 145*mm])
            bt.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#E8EEF4')),
                ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTNAME', (1,0), (1,-1), 'Courier'),
                ('FONTSIZE', (0,0), (-1,-1), 7),
                ('GRID', (0,0), (-1,-1), 0.3, colors.grey),
                ('PADDING', (0,0), (-1,-1), 3),
            ]))
            elements.append(bt)
            elements.append(Spacer(1, 3*mm))

        # Footer
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366')))
        elements.append(Spacer(1, 2*mm))
        elements.append(Paragraph(
            "This blockchain audit trail provides cryptographic proof that inspection records have not been altered. "
            "Each block's SHA-256 hash is computed from its contents and the previous block's hash, "
            "making tampering detectable. Compliant with MPA Singapore and ABS inspection record requirements.",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, textColor=colors.grey)))

        doc.build(elements)
        print(f"✅ Blockchain Audit Report generated: {output_path}")


# ===== TEST =====
blockchain = InspectionBlockchain()

blockchain.add_inspection_record(
    vessel_name="MV Pacific Explorer",
    vessel_imo="IMO 9876543",
    inspector="NautiCAI Automated System",
    location="Singapore Strait, 1.2°N 103.8°E",
    detections=[
        {"class": "Leakage", "confidence": 0.87, "severity": "Critical"},
        {"class": "Biofouling", "confidence": 0.82, "severity": "Moderate"},
        {"class": "Corrosion", "confidence": 0.76, "severity": "Moderate"},
    ]
)

blockchain.add_inspection_record(
    vessel_name="MV Singapore Star",
    vessel_imo="IMO 1234567",
    inspector="NautiCAI Automated System",
    location="Johor Strait, 1.4°N 103.9°E",
    detections=[
        {"class": "Pipeline", "confidence": 0.91, "severity": "Minor"},
        {"class": "Anode", "confidence": 0.78, "severity": "Moderate"},
    ]
)

is_valid, msg = blockchain.verify_chain()
print(f"\nChain Verification: {msg}")

blockchain.generate_audit_report(
    r"C:\Users\RAMNATH VENKAT\Documents\nauticai-underwater-anomaly\Blockchain_Audit_Report.pdf"
)