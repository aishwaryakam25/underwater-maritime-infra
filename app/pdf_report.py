"""
NautiCAI — Professional PDF Inspection Report Generator
Clean, print-ready layout · Helvetica typography · Header/Footer · Page numbers
"""

import io, datetime, hashlib
import numpy as np
from PIL import Image
import qrcode, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak, HRFlowable, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT


# ═══════════════════════════════════════════════════════════════════
# COLOUR PALETTE  (professional, print-friendly)
# ═══════════════════════════════════════════════════════════════════
NAVY        = colors.HexColor("#0B1A2E")
DARK_BG     = colors.HexColor("#0E1F38")
PANEL       = colors.HexColor("#F0F4FA")
PANEL_ALT   = colors.HexColor("#E8EDF5")
WHITE       = colors.HexColor("#FFFFFF")
BLACK       = colors.HexColor("#111827")
TEXT_DARK   = colors.HexColor("#1E293B")
TEXT_MID    = colors.HexColor("#475569")
TEXT_LIGHT  = colors.HexColor("#94A3B8")
BRAND_CYAN  = colors.HexColor("#0EA5E9")
BRAND_TEAL  = colors.HexColor("#14B8A6")
BORDER      = colors.HexColor("#CBD5E1")
ACCENT_LINE = colors.HexColor("#0EA5E9")

SEV = {
    "Critical": colors.HexColor("#DC2626"),
    "High":     colors.HexColor("#EA580C"),
    "Medium":   colors.HexColor("#2563EB"),
    "Low":      colors.HexColor("#16A34A"),
}
SEV_BG = {
    "Critical": colors.HexColor("#FEF2F2"),
    "High":     colors.HexColor("#FFF7ED"),
    "Medium":   colors.HexColor("#EFF6FF"),
    "Low":      colors.HexColor("#F0FDF4"),
}
GRADE_COL = {
    "A": colors.HexColor("#16A34A"),
    "B": colors.HexColor("#2563EB"),
    "C": colors.HexColor("#EA580C"),
    "D": colors.HexColor("#DC2626"),
}


# ═══════════════════════════════════════════════════════════════════
# STYLES
# ═══════════════════════════════════════════════════════════════════
def _styles():
    def S(name, **kw):
        return ParagraphStyle(name, **kw)
    return {
        "cover_title": S("cover_title", fontName="Helvetica-Bold", fontSize=28,
                         leading=34, textColor=WHITE, alignment=TA_LEFT),
        "cover_sub":   S("cover_sub", fontName="Helvetica", fontSize=12,
                         leading=16, textColor=colors.HexColor("#94A3B8"),
                         alignment=TA_LEFT),
        "h1": S("h1", fontName="Helvetica-Bold", fontSize=16, leading=20,
                textColor=TEXT_DARK, spaceBefore=16, spaceAfter=6),
        "h2": S("h2", fontName="Helvetica-Bold", fontSize=12, leading=16,
                textColor=BRAND_CYAN, spaceBefore=14, spaceAfter=4),
        "h3": S("h3", fontName="Helvetica-Bold", fontSize=10, leading=13,
                textColor=TEXT_DARK, spaceBefore=8, spaceAfter=3),
        "body": S("body", fontName="Helvetica", fontSize=9.5, leading=14,
                  textColor=TEXT_MID, spaceAfter=4),
        "body_sm": S("body_sm", fontName="Helvetica", fontSize=8.5, leading=12,
                     textColor=TEXT_MID, spaceAfter=2),
        "caption": S("caption", fontName="Helvetica-Oblique", fontSize=8,
                     leading=11, textColor=TEXT_LIGHT, spaceAfter=8,
                     alignment=TA_CENTER),
        "metric_val": S("metric_val", fontName="Helvetica-Bold", fontSize=22,
                        leading=26, textColor=TEXT_DARK, alignment=TA_CENTER),
        "metric_lbl": S("metric_lbl", fontName="Helvetica-Bold", fontSize=7.5,
                        leading=10, textColor=TEXT_LIGHT, alignment=TA_CENTER,
                        spaceAfter=0),
        "tbl_hdr": S("tbl_hdr", fontName="Helvetica-Bold", fontSize=8,
                     leading=11, textColor=WHITE),
        "tbl_cell": S("tbl_cell", fontName="Helvetica", fontSize=8.5,
                      leading=12, textColor=TEXT_DARK),
        "tbl_cell_bold": S("tbl_cell_bold", fontName="Helvetica-Bold",
                           fontSize=8.5, leading=12, textColor=TEXT_DARK),
        "sev_pill": S("sev_pill", fontName="Helvetica-Bold", fontSize=7.5,
                      leading=10, alignment=TA_CENTER),
        "disclaimer": S("disclaimer", fontName="Helvetica", fontSize=7,
                        leading=10, textColor=TEXT_LIGHT, alignment=TA_CENTER,
                        spaceBefore=6),
        "right": S("right", fontName="Helvetica", fontSize=9, leading=12,
                   textColor=TEXT_LIGHT, alignment=TA_RIGHT),
        "mono_sm": S("mono_sm", fontName="Courier", fontSize=8, leading=11,
                     textColor=BRAND_CYAN),
    }


# ═══════════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════════
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def _pil_to_rl(pil_img, max_w, max_h):
    """Convert PIL image -> RLImage, scaled to fit."""
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    w, h = pil_img.size
    scale = min(max_w / w, max_h / h, 1.0)
    return RLImage(buf, width=w * scale, height=h * scale)


def _make_qr(data):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGB")


def _section_line():
    return HRFlowable(width="100%", thickness=0.8, color=BORDER,
                      spaceAfter=6, spaceBefore=2)


def _section(title, ST):
    """Return [heading, accent line] for a new section."""
    return [
        Paragraph(title, ST["h2"]),
        HRFlowable(width="100%", thickness=1.5, color=ACCENT_LINE,
                   spaceAfter=8, spaceBefore=0),
    ]


# ═══════════════════════════════════════════════════════════════════
# HEADER / FOOTER — drawn on every page
# ═══════════════════════════════════════════════════════════════════
def _header_footer(canvas, doc, meta):
    canvas.saveState()
    W, H = PAGE_W, PAGE_H

    # Header bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, H - 18 * mm, W, 18 * mm, fill=1, stroke=0)

    canvas.setFillColor(colors.HexColor("#0EA5E9"))
    canvas.setFont("Helvetica-Bold", 13)
    canvas.drawString(MARGIN, H - 12 * mm, "NautiCAI")

    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.setFont("Helvetica", 8)
    canvas.drawString(MARGIN, H - 16 * mm, "Underwater Infrastructure Inspection Report")

    canvas.setFillColor(colors.HexColor("#94A3B8"))
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(W - MARGIN, H - 10.5 * mm,
                           f"Mission: {meta['mission_id']}  |  {meta['date']}")
    canvas.drawRightString(W - MARGIN, H - 15 * mm,
                           f"Model: {meta['model']}  |  Vessel: {meta['vessel']}")

    # Accent line
    canvas.setStrokeColor(colors.HexColor("#0EA5E9"))
    canvas.setLineWidth(1.5)
    canvas.line(0, H - 18 * mm, W, H - 18 * mm)

    # Footer
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 10 * mm, W - MARGIN, 10 * mm)

    canvas.setFillColor(TEXT_LIGHT)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 6 * mm,
                      "NautiCAI  |  Confidential — Authorised personnel only  |  "
                      "Singapore Maritime AI Systems Pte. Ltd.")
    canvas.drawRightString(W - MARGIN, 6 * mm, f"Page {doc.page}")

    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def build_pdf(
    mission_id, vessel, inspector, mode,
    dets, orig_img, annot_img, hmap_img,
    risk_score, grade, conf_thr, iou_thr,
):
    """
    Generate a professional, print-ready PDF inspection report.
    Returns: bytes
    """
    buf = io.BytesIO()
    usable_w = PAGE_W - 2 * MARGIN

    ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    meta = {
        "mission_id": mission_id,
        "vessel": vessel or "N/A",
        "model": "NautiCAI Vision Engine",
        "date": ts,
    }

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=24 * mm,
        bottomMargin=16 * mm,
        title=f"NautiCAI Report — {mission_id}",
        author="NautiCAI — Singapore Maritime AI Systems",
    )

    ST = _styles()
    story = []

    # ─── COVER / TITLE SECTION ──────────────────────────────────────
    cover_tbl = Table(
        [[
            Paragraph("NautiCAI", ParagraphStyle("ct", fontName="Helvetica-Bold",
                       fontSize=32, leading=38, textColor=WHITE)),
        ],
        [
            Paragraph("UNDERWATER INFRASTRUCTURE<br/>INSPECTION REPORT",
                       ParagraphStyle("cs", fontName="Helvetica-Bold",
                       fontSize=14, leading=18,
                       textColor=colors.HexColor("#0EA5E9"))),
        ],
        [Spacer(1, 4)],
        [
            Paragraph(f"Mission <b>{mission_id}</b>&nbsp;&nbsp;|&nbsp;&nbsp;"
                       f"Vessel <b>{vessel or 'N/A'}</b>&nbsp;&nbsp;|&nbsp;&nbsp;"
                       f"Inspector <b>{inspector}</b>",
                       ParagraphStyle("cm", fontName="Helvetica",
                       fontSize=9.5, leading=14,
                       textColor=colors.HexColor("#94A3B8"))),
        ],
        [
            Paragraph(f"{ts}&nbsp;&nbsp;|&nbsp;&nbsp;Scan Mode: {mode.upper()}",
                       ParagraphStyle("cd", fontName="Helvetica",
                       fontSize=9, leading=13,
                       textColor=colors.HexColor("#64748B"))),
        ]],
        colWidths=[usable_w],
    )
    cover_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",  (0, 0), (0, 0), 20),
        ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
        ("LEFTPADDING", (0, 0), (-1, -1), 20),
        ("RIGHTPADDING", (0, 0), (-1, -1), 20),
    ]))
    story.append(cover_tbl)
    story.append(Spacer(1, 12))

    # ─── MISSION META TABLE ─────────────────────────────────────────
    story += _section("Mission Details", ST)

    meta_data = [
        ["Mission ID", mission_id, "Vessel", vessel or "N/A"],
        ["Inspector", inspector, "Scan Mode", mode.upper()],
        ["Date / Time", ts, "Model", "NautiCAI Vision Engine"],
        ["Conf. Threshold", f"{conf_thr:.2f}", "IoU Threshold", f"{iou_thr:.2f}"],
    ]
    meta_tbl = Table(meta_data, colWidths=[34 * mm, 54 * mm, 34 * mm, 54 * mm])
    meta_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), TEXT_LIGHT),
        ("TEXTCOLOR", (2, 0), (2, -1), TEXT_LIGHT),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
        ("TEXTCOLOR", (3, 0), (3, -1), TEXT_DARK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
        ("BOX",       (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 10))

    # ─── EXECUTIVE SUMMARY METRICS ──────────────────────────────────
    story += _section("Executive Summary", ST)

    sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for d in dets:
        sev_counts[d.get("severity", "Medium")] += 1

    g_col = GRADE_COL.get(grade, TEXT_DARK)

    def _metric_cell(label, value, val_color=TEXT_DARK):
        return [
            Paragraph(str(value), ParagraphStyle(
                "mv_" + label, fontName="Helvetica-Bold", fontSize=24, leading=28,
                textColor=val_color, alignment=TA_CENTER)),
            Paragraph(label.upper(), ParagraphStyle(
                "ml_" + label, fontName="Helvetica-Bold", fontSize=7, leading=10,
                textColor=TEXT_LIGHT, alignment=TA_CENTER)),
        ]

    cw = usable_w / 5
    metric_row = Table(
        [[
            _metric_cell("Risk Score", f"{risk_score}", BRAND_CYAN),
            _metric_cell("Grade", grade, g_col),
            _metric_cell("Total", str(len(dets)), TEXT_DARK),
            _metric_cell("Critical", str(sev_counts["Critical"]),
                         SEV["Critical"] if sev_counts["Critical"] else TEXT_DARK),
            _metric_cell("High", str(sev_counts["High"]),
                         SEV["High"] if sev_counts["High"] else TEXT_DARK),
        ]],
        colWidths=[cw] * 5,
    )
    metric_row.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("BOX",        (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID",  (0, 0), (-1, -1), 0.3, BORDER),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(metric_row)
    story.append(Spacer(1, 6))

    # Status message
    if sev_counts["Critical"] > 0:
        msg = (f"<b>ALERT:</b>  {sev_counts['Critical']} critical finding(s) detected. "
               f"Immediate intervention is recommended.")
        msg_col, msg_bg = SEV["Critical"], SEV_BG["Critical"]
    elif sev_counts["High"] > 0:
        msg = (f"<b>Action Required:</b>  {sev_counts['High']} high-severity finding(s). "
               f"Schedule maintenance within 30 days.")
        msg_col, msg_bg = SEV["High"], SEV_BG["High"]
    elif len(dets) == 0:
        msg = "<b>All Clear:</b>  No anomalies detected above the confidence threshold."
        msg_col, msg_bg = SEV["Low"], SEV_BG["Low"]
    else:
        msg = "<b>Monitor:</b>  Findings recorded. Continue standard inspection cycle."
        msg_col, msg_bg = SEV["Medium"], SEV_BG["Medium"]

    status = Table(
        [[Paragraph(msg, ParagraphStyle("status", fontName="Helvetica",
                    fontSize=9.5, leading=14, textColor=TEXT_DARK))]],
        colWidths=[usable_w],
    )
    status.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), msg_bg),
        ("BOX",           (0, 0), (-1, -1), 1.2, msg_col),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(status)
    story.append(Spacer(1, 12))

    # ─── ANNOTATED IMAGE ────────────────────────────────────────────
    story += _section("Annotated Inspection Image", ST)

    if annot_img is not None:
        img_rl = _pil_to_rl(annot_img, max_w=usable_w, max_h=100 * mm)
        img_rl.hAlign = "CENTER"
        img_frame = Table([[img_rl]], colWidths=[usable_w])
        img_frame.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(img_frame)
        story.append(Paragraph(
            "Fig 1 — AI-detected anomalies with bounding boxes and severity labels.",
            ST["caption"]))
    else:
        story.append(Paragraph("No annotated image available.", ST["body"]))

    story.append(Spacer(1, 6))

    # ─── RISK HEATMAP ───────────────────────────────────────────────
    if hmap_img is not None:
        story += _section("Structural Risk Heatmap", ST)

        hmap_rl = _pil_to_rl(hmap_img, max_w=usable_w, max_h=85 * mm)
        hmap_rl.hAlign = "CENTER"
        hmap_frame = Table([[hmap_rl]], colWidths=[usable_w])
        hmap_frame.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(hmap_frame)
        story.append(Paragraph(
            "Fig 2 — Gaussian kernel risk-density map (plasma colourmap).",
            ST["caption"]))
        story.append(Spacer(1, 4))

    story.append(PageBreak())

    # ─── DEFECT DETECTION LOG ────────────────────────────────────────
    story += _section("Defect Detection Log", ST)

    if not dets:
        story.append(Paragraph("No detections above the confidence threshold.", ST["body"]))
    else:
        hdr_style = ST["tbl_hdr"]
        header_row = [
            Paragraph("#", hdr_style),
            Paragraph("Defect Class", hdr_style),
            Paragraph("Severity", hdr_style),
            Paragraph("Conf.", hdr_style),
            Paragraph("Bounding Box (px)", hdr_style),
            Paragraph("Area (px\u00B2)", hdr_style),
        ]
        rows = [header_row]

        for d in dets:
            sev = d.get("severity", "Medium")
            sev_col = SEV.get(sev, TEXT_DARK)
            sev_bg  = SEV_BG.get(sev, WHITE)

            sev_pill = Table(
                [[Paragraph(sev, ParagraphStyle(
                    "sp_" + sev, fontName="Helvetica-Bold", fontSize=7.5,
                    leading=10, textColor=sev_col, alignment=TA_CENTER))]],
                colWidths=[50],
            )
            sev_pill.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), sev_bg),
                ("BOX",        (0, 0), (-1, -1), 0.5, sev_col),
                ("TOPPADDING",    (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING",   (0, 0), (-1, -1), 4),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
            ]))

            rows.append([
                Paragraph(f"{d['id']:02d}", ST["tbl_cell"]),
                Paragraph(d["cls"].replace("_", " "), ST["tbl_cell_bold"]),
                sev_pill,
                Paragraph(f"{d['conf'] * 100:.1f}%", ST["tbl_cell"]),
                Paragraph(f"({d['x1']},{d['y1']}) \u2192 ({d['x2']},{d['y2']})",
                          ST["tbl_cell"]),
                Paragraph(f"{d.get('area', 0):,}", ST["tbl_cell"]),
            ])

        bbox_col_w = usable_w - (10 + 34 + 22 + 16 + 24) * mm
        col_w = [10 * mm, 34 * mm, 22 * mm, 16 * mm, bbox_col_w, 24 * mm]
        det_tbl = Table(rows, colWidths=col_w, repeatRows=1)
        det_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
            ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, 0), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
            ("FONTSIZE",   (0, 1), (-1, -1), 8.5),
            ("BOX",        (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID",  (0, 0), (-1, -1), 0.25, BORDER),
            ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(det_tbl)

    story.append(Spacer(1, 10))

    # ─── SEVERITY DISTRIBUTION CHART ─────────────────────────────────
    story += _section("Severity Distribution", ST)

    fig, ax = plt.subplots(figsize=(6.5, 2.4), facecolor="white")
    ax.set_facecolor("#FAFBFC")
    bar_colors = ["#DC2626", "#EA580C", "#2563EB", "#16A34A"]
    labels = list(sev_counts.keys())
    values = list(sev_counts.values())
    bars = ax.bar(labels, values, color=bar_colors, width=0.5,
                  edgecolor="#E2E8F0", linewidth=0.8)
    ax.set_ylabel("Count", fontsize=9, color="#475569")
    ax.tick_params(colors="#475569", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color("#E2E8F0")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, alpha=0.3, color="#CBD5E1")
    for bar, val in zip(bars, values):
        if val:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.08,
                    str(val), ha="center", color="#1E293B", fontsize=11,
                    fontweight="bold")
    fig.tight_layout(pad=1.2)
    chart_buf = io.BytesIO()
    fig.savefig(chart_buf, format="png", dpi=140, facecolor="white")
    plt.close(fig)
    chart_buf.seek(0)

    chart_img = _pil_to_rl(Image.open(chart_buf), usable_w * 0.75, 55 * mm)
    chart_img.hAlign = "CENTER"
    story.append(chart_img)
    story.append(Spacer(1, 8))

    # ─── RECOMMENDATIONS ─────────────────────────────────────────────
    story += _section("Recommendations", ST)

    recs = {
        "Critical": [
            "Immediate dry-dock inspection required.",
            "Deploy repair team within 7 days.",
            "HOLD — not cleared for deep-water operations.",
        ],
        "High": [
            "Schedule maintenance within 30 days.",
            "Monitor with bi-weekly ROV survey.",
            "Apply protective coating to affected areas.",
        ],
        "Medium": [
            "Document in vessel maintenance log.",
            "Schedule repair at next scheduled port call.",
            "Apply anti-fouling treatment as needed.",
        ],
        "Low": [
            "Monitor during quarterly inspection cycle.",
            "Record in digital twin baseline model.",
        ],
    }

    has_recs = False
    for sev_level, items in recs.items():
        if sev_counts.get(sev_level, 0) == 0:
            continue
        has_recs = True
        sev_col = SEV.get(sev_level, TEXT_DARK)

        story.append(Paragraph(
            f"<font color='{sev_col.hexval()}'><b>\u25B8 {sev_level.upper()}</b></font>"
            f"&nbsp;&nbsp;({sev_counts[sev_level]} finding"
            f"{'s' if sev_counts[sev_level] != 1 else ''})",
            ST["h3"]))
        for item in items:
            story.append(Paragraph(f"&nbsp;&nbsp;\u2022&nbsp;&nbsp;{item}", ST["body"]))
        story.append(Spacer(1, 4))

    if not has_recs:
        story.append(Paragraph("No actionable recommendations — all clear.", ST["body"]))

    story.append(Spacer(1, 6))

    # ─── EDGE DEPLOYMENT ─────────────────────────────────────────────
    story.append(PageBreak())
    story += _section("Edge Deployment — NVIDIA Jetson Orin", ST)

    edge_data = [
        ["Target Platform", "NVIDIA Jetson AGX Orin 64 GB / Orin NX 16 GB"],
        ["Inference Engine", "TensorRT 8.x  |  INT8 / FP16  |  ONNX Runtime"],
        ["Model Export", "Detection model ONNX  \u2192  TensorRT .engine  (34 \u2013 95 FPS)"],
        ["Throughput", "Edge model \u2248 95 FPS  |  Balanced model \u2248 55 FPS  |  Heavy model \u2248 34 FPS"],
        ["Power Envelope", "15 \u2013 60 W (configurable power modes)"],
        ["Video Pipeline", "RTSP \u2192 GStreamer \u2192 OpenCV \u2192 inference"],
        ["End-to-End Latency", "\u2248 28 ms"],
        ["Export Command", "yolo export model=yolov8n.pt format=engine device=0"],
    ]
    edge_tbl = Table(edge_data, colWidths=[38 * mm, usable_w - 38 * mm])
    edge_tbl.setStyle(TableStyle([
        ("FONTNAME",  (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",  (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",  (0, 0), (-1, -1), 8.5),
        ("TEXTCOLOR", (0, 0), (0, -1), TEXT_LIGHT),
        ("TEXTCOLOR", (1, 0), (1, -1), TEXT_DARK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PANEL]),
        ("BOX",       (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(edge_tbl)
    story.append(Spacer(1, 14))

    # ─── QR CODE / DIGITAL REPORT ────────────────────────────────────
    story += _section("Digital Report — QR Verification", ST)

    sev_summary = {k: v for k, v in sev_counts.items() if v > 0}
    qr_hash = hashlib.sha256(f"{mission_id}{vessel}{ts}{risk_score}".encode()).hexdigest()[:12]
    qr_url = (
        f"https://aishwaryav25-nauticai-maritime.streamlit.app/"
        f"?tab=report&mission={mission_id}"
        f"&vessel={vessel or 'N/A'}"
        f"&grade={grade}&risk={risk_score}"
        f"&hash={qr_hash}"
    )
    qr_pil = _make_qr(qr_url)

    qr_info = [
        Paragraph("Scan to download PDF report", ST["h3"]),
        Spacer(1, 2),
        Paragraph(f"<font color='#0EA5E9'><u>{qr_url}</u></font>",
                  ParagraphStyle("qr_link", fontName="Helvetica", fontSize=7,
                                leading=10, textColor=BRAND_CYAN)),
        Spacer(1, 6),
        Paragraph(f"<b>Mission:</b>&nbsp;&nbsp;{mission_id}&nbsp;&nbsp;|&nbsp;&nbsp;"
                  f"<b>Vessel:</b>&nbsp;&nbsp;{vessel or 'N/A'}", ST["body_sm"]),
        Paragraph(f"<b>Risk Score:</b>&nbsp;&nbsp;{risk_score}/100&nbsp;&nbsp;|&nbsp;&nbsp;"
                  f"<b>Grade:</b>&nbsp;&nbsp;{grade}", ST["body_sm"]),
        Paragraph(f"<b>Detections:</b>&nbsp;&nbsp;{len(dets)}&nbsp;&nbsp;|&nbsp;&nbsp;"
                  f"<b>Mode:</b>&nbsp;&nbsp;{mode.upper()}", ST["body_sm"]),
        Paragraph(f"<b>SHA-256:</b>&nbsp;&nbsp;{qr_hash}", ST["body_sm"]),
        Paragraph(f"<b>Generated:</b>&nbsp;&nbsp;{ts}", ST["body_sm"]),
    ]

    qr_row = Table(
        [[_pil_to_rl(qr_pil, 40 * mm, 40 * mm), qr_info]],
        colWidths=[46 * mm, usable_w - 46 * mm],
    )
    qr_row.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PANEL),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(qr_row)
    story.append(Spacer(1, 16))

    # ─── DISCLAIMER ──────────────────────────────────────────────────
    story.append(_section_line())
    story.append(Paragraph(
        "All findings must be verified by a certified marine surveyor before "
        "operational decisions are made. This report is generated by an AI system "
        "and is advisory in nature.<br/>"
        "<b>NautiCAI  |  Singapore Maritime AI Systems Pte. Ltd.  |  Est. 2024</b>",
        ST["disclaimer"]))

    # ─── BUILD ───────────────────────────────────────────────────────
    doc.build(
        story,
        onFirstPage=lambda c, d: _header_footer(c, d, meta),
        onLaterPages=lambda c, d: _header_footer(c, d, meta),
    )

    buf.seek(0)
    return buf.getvalue()

