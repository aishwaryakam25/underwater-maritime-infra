import io, os, datetime, hashlib, json, math
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
    Image as RLImage, PageBreak, HRFlowable,
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

# Company site (matches web app sidebar/footer)
NAUTICAI_WEB_URL = os.environ.get("NAUTICAI_WEB_URL", "https://www.nauticai-ai.com")

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
    """Convert PIL image -> RLImage, scaled to fit (ReportLab units on max_w/max_h)."""
    pil_img = pil_img.convert("RGB")
    w, h = pil_img.size
    if w <= 0 or h <= 0:
        raise ValueError("Invalid image dimensions for PDF embedding")
    # Very large frames create giant PNGs and can trigger ReportLab layout/memory failures.
    max_px_side = 2400
    longest = max(w, h)
    if longest > max_px_side:
        s = max_px_side / float(longest)
        nw = max(1, int(round(w * s)))
        nh = max(1, int(round(h * s)))
        try:
            rs = Image.Resampling.LANCZOS
        except AttributeError:
            rs = Image.LANCZOS
        pil_img = pil_img.resize((nw, nh), rs)
        w, h = pil_img.size
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    scale = min(float(max_w) / float(w), float(max_h) / float(h), 1.0)
    rw = max(1.0, float(w) * scale)
    rh = max(1.0, float(h) * scale)
    return RLImage(buf, width=rw, height=rh)


def _batch_bbox_cell_txt(d):
    x1, y1, x2, y2 = d.get("x1"), d.get("y1"), d.get("x2"), d.get("y2")
    if None in (x1, y1, x2, y2):
        return "—"
    try:
        return (
            f"({int(float(x1))},{int(float(y1))}) \u2192 ({int(float(x2))},{int(float(y2))})"
        )
    except (TypeError, ValueError):
        return "—"


def _make_qr(data, box_size=10):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
                        box_size=box_size, border=3)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGB")


def _prov_cell_val(v):
    if v is None:
        return "—"
    if isinstance(v, bool):
        return "Yes" if v else "No"
    return str(v)


def _xml_esc(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


# Omitted from customer PDF (table + QR). Same logic must stay in sync with inspection_provenance fields.
_PROVENANCE_MODEL_ARTEFACT_KEYS = frozenset({
    "model_key",
    "model_weights_display_name",
    "model_weights_filename",
    "model_weights_relative_path",
    "weights_sha256",
    "weights_size_bytes",
})


def _customer_pdf_provenance(provenance: dict) -> dict:
    """Remove model artefact fingerprinting; recompute digest so QR matches the printed snapshot."""
    base = {
        k: v
        for k, v in provenance.items()
        if k != "provenance_digest_sha256" and k not in _PROVENANCE_MODEL_ARTEFACT_KEYS
    }
    body = {k: base[k] for k in sorted(base.keys())}
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    out = dict(base)
    out["provenance_digest_sha256"] = digest
    return out


def inspection_provenance_flowables(ST, usable_w, provenance: dict):
    """Survey-style audit block: human-readable rows + QR with full JSON payload."""
    if not provenance:
        return []

    provenance = _customer_pdf_provenance(provenance)

    intro = Paragraph(
        "Cryptographically sealed snapshot of the inference configuration used for this report "
        "(thresholds, preprocessing, API build). Scan the QR to retrieve the "
        "machine-readable JSON; verify <b>provenance_digest_sha256</b> by recomputing SHA-256 "
        "over all other keys sorted alphabetically, JSON-encoded with compact separators.",
        ST["body_sm"],
    )

    rows_kv = [
        ("Generated (UTC)", provenance.get("generated_at_utc")),
        ("API version", provenance.get("api_version")),
        ("Schema", str(provenance.get("schema_version", ""))),
        ("Mission ID", provenance.get("mission_id")),
        ("Scan mode", provenance.get("scan_mode")),
        ("Confidence threshold", provenance.get("conf_threshold")),
        ("IoU threshold", provenance.get("iou_threshold")),
        ("CLAHE", provenance.get("use_clahe")),
        ("CLAHE clip", provenance.get("clahe_clip")),
        ("Green-channel boost", provenance.get("use_green_channel_boost")),
        ("Edge estimator", provenance.get("use_edge_estimator")),
        ("Turbidity in", provenance.get("turbidity_in")),
        ("Correct turbidity", provenance.get("correct_turbidity")),
        ("Marine snow", provenance.get("marine_snow")),
        ("Official-19-only outputs", provenance.get("official_19_only_outputs")),
        ("Severity filter", provenance.get("severity_filter")),
        ("Video sample stride (frames)", provenance.get("video_sample_stride_frames")),
        ("Provenance digest SHA-256", provenance.get("provenance_digest_sha256")),
    ]

    hdr = ParagraphStyle(
        "prov_h",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=WHITE,
        alignment=TA_LEFT,
    )
    cell_l = ParagraphStyle(
        "prov_cl",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=TEXT_LIGHT,
    )
    cell_r = ParagraphStyle(
        "prov_cr",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=TEXT_DARK,
    )
    mono_r = ParagraphStyle(
        "prov_mono",
        fontName="Courier",
        fontSize=7,
        leading=10,
        textColor=TEXT_DARK,
    )

    tbl_rows = [[Paragraph("Field", hdr), Paragraph("Value", hdr)]]
    for label, val in rows_kv:
        if label == "Severity filter" and val is None:
            continue
        if label == "Video sample stride (frames)" and val is None:
            continue
        wrap_style = mono_r if label == "Provenance digest SHA-256" else cell_r
        val_s = _prov_cell_val(val)
        tbl_rows.append([
            Paragraph(_xml_esc(label), cell_l),
            Paragraph(_xml_esc(val_s), wrap_style),
        ])

    val_w = usable_w - 82 * mm
    prov_tbl = Table(tbl_rows, colWidths=[40 * mm, val_w])
    prov_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))

    qr_payload = json.dumps(provenance, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    bs = 5 if len(qr_payload) > 900 else 6
    qr_pil = _make_qr(qr_payload, box_size=bs)

    # Nested Table (not KeepTogether): KeepTogether inside Table cells makes ReportLab compute
    # row heights incorrectly (~1e7 pt) and raises LayoutError on PDF build.
    qr_w = 42 * mm
    qr_col = Table(
        [
            [Paragraph("<b>Audit QR (JSON)</b>", ST["h3"])],
            [
                Paragraph(
                    "Contains the full provenance record including digest. Store alongside the PDF for "
                    "third-party verification.",
                    ST["body_sm"],
                )
            ],
            [_pil_to_rl(qr_pil, 38 * mm, 38 * mm)],
        ],
        colWidths=[qr_w],
    )
    qr_col.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (0, 0), 4),
                ("BOTTOMPADDING", (0, 1), (0, 1), 8),
                ("BOTTOMPADDING", (0, 2), (0, 2), 2),
            ]
        )
    )

    combined = Table(
        [[prov_tbl, qr_col]],
        colWidths=[usable_w - qr_w, qr_w],
    )
    combined.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))

    out = []
    out += _section("Inspection provenance (survey audit)", ST)
    out.append(intro)
    out.append(Spacer(1, 8))
    out.append(combined)
    out.append(Spacer(1, 12))
    return out


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

    page_txt = f"Page {doc.page}"
    pw = canvas.stringWidth(page_txt, "Helvetica", 7)
    uw = canvas.stringWidth(NAUTICAI_WEB_URL, "Helvetica", 7)
    gap = 4 * mm
    url_x = W - MARGIN - pw - gap - uw
    canvas.setFillColor(BRAND_CYAN)
    canvas.drawString(url_x, 6 * mm, NAUTICAI_WEB_URL)
    canvas.linkURL(
        NAUTICAI_WEB_URL,
        (url_x, 6 * mm - 1, url_x + uw, 6 * mm + 8),
        relative=0,
    )

    canvas.setFillColor(TEXT_LIGHT)
    canvas.drawRightString(W - MARGIN, 6 * mm, page_txt)

    canvas.restoreState()


UI_CYAN = colors.HexColor("#22D3EE")
DASH_BG = colors.HexColor("#0B1220")
PANEL_IMG_BG = colors.HexColor("#0F172A")


def _panel_cell(pil_img, label, cell_w, cell_h):
    """One labelled tile — matches web dashboard captions (ORIGINAL / ENHANCED / ANNOTATED / HEATMAP)."""
    lbl = Paragraph(
        f"<b>{label}</b>",
        ParagraphStyle(
            "pn_lbl_" + label[:8],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
    )
    if pil_img is None:
        body = Paragraph(
            "<i>No image</i>",
            ParagraphStyle(
                "pn_miss",
                fontName="Helvetica",
                fontSize=9,
                leading=12,
                textColor=TEXT_LIGHT,
                alignment=TA_CENTER,
            ),
        )
    else:
        body = _pil_to_rl(pil_img, max_w=cell_w - 8, max_h=cell_h - 16)
        body.hAlign = "CENTER"
    inner = Table([[lbl], [body]], colWidths=[cell_w])
    inner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 1), (-1, 1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
                ("BACKGROUND", (0, 1), (-1, 1), PANEL_IMG_BG),
            ]
        )
    )
    return inner


FOUL_LEGEND_YELLOW = colors.HexColor("#FFEB3B")


DEFAULT_HULL_FOULING_ROWS = [
    {
        "location": "Bow",
        "narrative": (
            "The condition of plating of the bulbous bow area as visual inspection is fouled by "
            "Slime with 5mm of thickness."
        ),
        "pct": "80",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Port Side",
        "narrative": (
            "The condition of side shell / vertical side at portside area as visual inspection "
            "from forward to aft ward is fouled by Slime with 10mm of thickness."
        ),
        "pct": "70",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Starboard Side",
        "narrative": (
            "The condition of side shell / vertical side at STB side area as visual inspection "
            "from forward to aft ward is fouled by Slime with 10mm of thickness."
        ),
        "pct": "70",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Flat Bottom",
        "narrative": (
            "The condition of flat bottom hull as visual inspection from bottom forward to "
            "aft Ward is fouled by Slime with 5mm of thickness."
        ),
        "pct": "50",
        "severity": "B",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Dry docking marks",
        "narrative": (
            "The condition of dry docking marks flat bottom hull as visual inspection from "
            "bottom forward to aft ward is fouled by Slime and barnacles with 3mm of thickness."
        ),
        "pct": "90",
        "severity": "B",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Bilge keels",
        "narrative": (
            "The condition of bilge keel at portside and starboard side area as visual inspection "
            "from fore tip to aft tip and flat bar is fouled by Slime with 5mm of thickness."
        ),
        "pct": "50",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Stern",
        "narrative": (
            "The condition of stern area as visual inspection is fouled by Slime with 5mm of thickness."
        ),
        "pct": "80",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Sea Chest Gratings",
        "narrative": (
            "The condition of the sea chest gratings is fouled by barnacles and Slime with "
            "4-6mm of thickness."
        ),
        "pct": "80",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Rudder/S",
        "narrative": (
            "The condition of shell plating of rudder blade as visual inspection from top to "
            "bottom is fouled by Slime with 5mm of thickness."
        ),
        "pct": "80",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Rudder pintle frame",
        "narrative": (
            "The condition of rudder pintle frame as visual inspection from top to bottom is "
            "fouled by Slime and barnacles with 5-10mm of thickness."
        ),
        "pct": "70",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
    {
        "location": "Rope Guard",
        "narrative": (
            "The condition of rope gaurd as visual inspection is fouled by Slime and barnacles "
            "with 2-4mm of thickness."
        ),
        "pct": "70",
        "severity": "C",
        "clean_yes": True,
        "remarks": "Fishing net removed",
        "remarks_highlight": True,
    },
    {
        "location": "Propeller/S",
        "narrative": (
            "The propeller blades, as visual inspection all blades is fouled by Slime with "
            "6mm of thickness."
        ),
        "pct": "70",
        "severity": "C",
        "clean_yes": True,
        "remarks": "",
        "remarks_highlight": False,
    },
]


def _hull_fouling_executive_summary_flowables(ST, usable_w, fouling_rows=None, include_annex_note=True):
    """
    Extra hull report page: fouling type legend + executive summary grid + severity legend.
    """
    rows = fouling_rows if fouling_rows is not None else DEFAULT_HULL_FOULING_ROWS

    title_style = ParagraphStyle(
        "hf_title",
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=TEXT_DARK,
    )
    leg_cell = ParagraphStyle(
        "hf_leg",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=TEXT_DARK,
        alignment=TA_CENTER,
    )
    leg_plain = ParagraphStyle(
        "hf_legp",
        parent=leg_cell,
        fontName="Helvetica-Bold",
    )
    leg_yellow = ParagraphStyle(
        "hf_legy",
        parent=leg_cell,
        backColor=FOUL_LEGEND_YELLOW,
    )

    cw = usable_w / 7.0
    legend_cells = [
        Paragraph("0-Clean", leg_plain),
        Paragraph("1-Barnacles", leg_yellow),
        Paragraph("2-Algae", leg_plain),
        Paragraph("3-Slime", leg_yellow),
        Paragraph("4-Tubeworm", leg_plain),
        Paragraph("5-Mussels", leg_plain),
        Paragraph("6-Grass", leg_plain),
    ]
    ep = Paragraph("", leg_plain)
    leg_row2 = [Paragraph("7-Calcareous/Other", leg_plain), ep, ep, ep, ep, ep, ep]
    leg_tbl = Table([legend_cells, leg_row2], colWidths=[cw] * 7)
    leg_tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BACKGROUND", (1, 0), (1, 0), FOUL_LEGEND_YELLOW),
                ("BACKGROUND", (3, 0), (3, 0), FOUL_LEGEND_YELLOW),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("SPAN", (0, 1), (6, 1)),
            ]
        )
    )

    hdr = ST["tbl_hdr"]
    cell_l = ParagraphStyle(
        "hf_cl",
        fontName="Helvetica",
        fontSize=6.5,
        leading=8.5,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
    )
    cell_c = ParagraphStyle(
        "hf_cc",
        parent=cell_l,
        alignment=TA_CENTER,
    )
    cell_b = ParagraphStyle(
        "hf_cb",
        parent=cell_l,
        fontName="Helvetica-Bold",
    )

    loc_w = 20 * mm
    pct_w = 13 * mm
    sev_w = 13 * mm
    cy_w = 11 * mm
    cn_w = 11 * mm
    rem_w = 22 * mm
    nar_w = usable_w - loc_w - pct_w - sev_w - cy_w - cn_w - rem_w

    head_top = [
        Paragraph("Location", hdr),
        Paragraph("Fouling conditions Executive", hdr),
        Paragraph("% Area<br/>Covered", hdr),
        Paragraph("Severity", hdr),
        Paragraph("Cleaning — Yes", hdr),
        Paragraph("Cleaning — No", hdr),
        Paragraph("Remarks", hdr),
    ]
    data_rows = [head_top]
    hl_commands = []

    for i, r in enumerate(rows, start=1):
        yes_mark = "X" if r.get("clean_yes") else ""
        no_mark = "" if r.get("clean_yes") else "X"
        rem = r.get("remarks") or ""
        rem_p = Paragraph(rem, cell_l)
        data_rows.append(
            [
                Paragraph(f"<b>{r['location']}</b>", cell_b),
                Paragraph(r["narrative"], cell_l),
                Paragraph(str(r["pct"]), cell_c),
                Paragraph(str(r["severity"]), cell_c),
                Paragraph(yes_mark, cell_c),
                Paragraph(no_mark, cell_c),
                rem_p,
            ]
        )
        if r.get("remarks_highlight"):
            hl_commands.append(("BACKGROUND", (6, i), (6, i), FOUL_LEGEND_YELLOW))

    foul_tbl = Table(data_rows, colWidths=[loc_w, nar_w, pct_w, sev_w, cy_w, cn_w, rem_w], repeatRows=1)
    ts = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ALIGN", (2, 1), (4, -1), "CENTER"),
    ]
    ts.extend(hl_commands)
    foul_tbl.setStyle(TableStyle(ts))

    foot_lbl = ParagraphStyle(
        "hf_ft",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=TEXT_DARK,
        alignment=TA_LEFT,
    )
    foot_hi = ParagraphStyle(
        "hf_fth",
        parent=foot_lbl,
        fontName="Helvetica-Bold",
        backColor=FOUL_LEGEND_YELLOW,
        alignment=TA_CENTER,
    )
    footer_tbl = Table(
        [
            [
                Paragraph("Severity:", foot_lbl),
                Paragraph("(A) Light", foot_lbl),
                Paragraph("(B) Moderate", foot_hi),
                Paragraph("(C) Heavy", foot_hi),
                Paragraph("(D) Clean", foot_lbl),
            ]
        ],
        colWidths=[22 * mm, 28 * mm, 32 * mm, 28 * mm, 28 * mm],
    )
    footer_tbl.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ]
        )
    )

    out = [
        Paragraph("Fouling conditions executive summary:", title_style),
        Spacer(1, 4),
        leg_tbl,
        Spacer(1, 10),
        foul_tbl,
        Spacer(1, 10),
        footer_tbl,
    ]
    if include_annex_note:
        out.append(
            Paragraph(
                "<i>NautiCAI hull annex — fouling taxonomy reference for survey reporting.</i>",
                ST["caption"],
            )
        )
    return out


def _four_panel_grid(orig_img, enhanced_img, annot_img, hmap_img, usable_w, cell_h_mm=52):
    """2×2 layout like the live NAUTICAI dashboard."""
    gap = 2.5 * mm
    half = (usable_w - gap) / 2
    ch = cell_h_mm * mm
    r1 = [
        _panel_cell(orig_img, "ORIGINAL", half, ch),
        _panel_cell(enhanced_img, "VISIBILITY (ENHANCED)", half, ch),
    ]
    r2 = [
        _panel_cell(annot_img, "ANNOTATED", half, ch),
        _panel_cell(hmap_img, "HEATMAP", half, ch),
    ]
    grid = Table([r1, r2], colWidths=[half, half])
    grid.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return grid


def _dashboard_results_banner(dets, risk_score, grade, mission_id, usable_w, scan_mode=""):
    """Dark strip with headline metrics (web UI style)."""
    n = len(dets)
    g_col = GRADE_COL.get(grade, WHITE)
    head_style = ParagraphStyle(
        "db_head",
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        "db_sub",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=10,
        textColor=UI_CYAN,
        alignment=TA_CENTER,
    )
    lbl_style = ParagraphStyle(
        "db_k",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=TEXT_LIGHT,
        alignment=TA_CENTER,
    )
    val_style = ParagraphStyle(
        "db_v",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=WHITE,
        alignment=TA_CENTER,
    )
    grade_style = ParagraphStyle(
        "db_g",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=g_col,
        alignment=TA_CENTER,
    )
    note_style = ParagraphStyle(
        "db_note",
        fontName="Helvetica",
        fontSize=7,
        leading=10,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_CENTER,
    )
    cw = usable_w / 4
    metrics = Table(
        [
            [
                Paragraph("DETECTIONS", lbl_style),
                Paragraph("INSPECTION SCORE", lbl_style),
                Paragraph("GRADE", lbl_style),
                Paragraph("MISSION ID", lbl_style),
            ],
            [
                Paragraph(str(n), val_style),
                Paragraph(f"{risk_score}%", val_style),
                Paragraph(str(grade), grade_style),
                Paragraph(
                    mission_id,
                    ParagraphStyle(
                        "db_mid",
                        fontName="Courier-Bold",
                        fontSize=10,
                        leading=13,
                        textColor=UI_CYAN,
                        alignment=TA_CENTER,
                    ),
                ),
            ],
        ],
        colWidths=[cw, cw, cw, cw],
    )
    metrics.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LINEBELOW", (0, 0), (-1, 0), 0.25, colors.HexColor("#334155")),
            ]
        )
    )
    outer = Table(
        [
            [Paragraph("INSPECTION RESULTS", sub_style)],
            [Paragraph(f"{n} Anomalies Found", head_style)],
            [metrics],
            [
                Paragraph(
                    "Inspection score = health-style index (higher with fewer / lighter defects); "
                    "not &quot;% danger&quot;. Aggregates severity weights with diminishing impact "
                    "so dense video detections do not force the score to zero."
                    + (
                        " <b>Video:</b> counts include every sampled frame; the image panel below "
                        "is the <i>first</i> sampled frame only."
                        if str(scan_mode).lower().strip() == "video"
                        else ""
                    ),
                    note_style,
                )
            ],
        ],
        colWidths=[usable_w],
    )
    outer.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), DASH_BG),
                ("BOX", (0, 0), (-1, -1), 1, UI_CYAN),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    return outer


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def build_pdf(
    mission_id, vessel, inspector, mode,
    dets, orig_img, enhanced_img, annot_img, hmap_img,
    risk_score, grade, conf_thr, iou_thr,
    model_name=None,
    hull_fouling_rows=None,
    video_meta=None,
    provenance=None,
):
    """
    Generate a professional, print-ready PDF inspection report.
    Returns: bytes

    hull_fouling_rows: optional list of dicts for scan_mode ``hull`` only; each dict may contain
    ``location``, ``narrative``, ``pct``, ``severity``, ``clean_yes`` (bool), ``remarks``,
    ``remarks_highlight`` (bool). If omitted, a standard fouling executive annex is used.
    video_meta: optional dict for ``video`` reports with keys like ``duration_sec``, ``fps``,
    ``total_frames``, ``sample_stride``, ``frames_processed``.
    provenance: optional audit dict from ``collect_inspection_provenance`` (table + JSON QR).
    """
    buf = io.BytesIO()
    usable_w = PAGE_W - 2 * MARGIN

    ts = datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    model_disp = model_name or "NautiCAI Vision Engine"
    meta = {
        "mission_id": mission_id,
        "vessel": vessel or "N/A",
        "model": model_disp,
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
        ["Date / Time", ts, "Model", model_disp],
        ["Conf. Threshold", f"{conf_thr:.2f}", "IoU Threshold", f"{iou_thr:.2f}"],
    ]
    if video_meta:
        dur = video_meta.get("duration_sec")
        fps_m = video_meta.get("fps")
        meta_data.append(
            [
                "Video duration",
                f"{dur} s" if dur is not None else "—",
                "Video FPS",
                str(fps_m) if fps_m is not None else "—",
            ]
        )
        meta_data.append(
            [
                "Sample stride (frames)",
                str(video_meta.get("sample_stride", "—")),
                "Frames processed",
                str(video_meta.get("frames_processed", "—")),
            ]
        )
        meta_data.append(
            [
                "Est. total frames",
                str(video_meta.get("total_frames", "—")),
                "Detections (report)",
                str(video_meta.get("total_detections", len(dets))),
            ]
        )
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

    sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for d in dets:
        sev = d.get("severity", "Medium")
        if sev not in sev_counts:
            sev = "Medium"
        sev_counts[sev] += 1

    # ─── DASHBOARD SNAPSHOT (matches live UI headline + 4 tiles) ─────
    story += _section("Dashboard snapshot", ST)
    story.append(_dashboard_results_banner(dets, risk_score, grade, mission_id, usable_w, mode))
    story.append(Spacer(1, 8))

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
    story.append(Spacer(1, 10))

    story += _section("Visual record — four-panel view", ST)
    enh_display = enhanced_img if enhanced_img is not None else orig_img
    story.append(_four_panel_grid(orig_img, enh_display, annot_img, hmap_img, usable_w))
    four_panel_caption = (
        "Video report: images are from the <b>first sampled frame</b> only (same enhancement "
        "and annotation pipeline as the web UI). Detection counts and the log below cover "
        "<b>all</b> sampled frames."
        if str(mode).lower().strip() == "video"
        else (
            "Same layout as the web dashboard: original upload, visibility-enhanced frame, "
            "annotated detections, and risk heatmap."
        )
    )
    story.append(Paragraph(four_panel_caption, ST["caption"]))
    story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ─── HULL ANNEX: FOULING EXECUTIVE SUMMARY ───────────────────────
    if str(mode).lower().strip() == "hull":
        story.extend(
            _hull_fouling_executive_summary_flowables(ST, usable_w, hull_fouling_rows)
        )
        story.append(PageBreak())

    # ─── DEFECT DETECTION LOG ────────────────────────────────────────
    story += _section("Defect Detection Log", ST)

    try:
        pdf_cap = int(os.environ.get("NAUTICAI_PDF_DEFECT_CAP", "250"))
    except (TypeError, ValueError):
        pdf_cap = 250
    dets_for_log = list(dets)
    log_note_para = None
    if pdf_cap > 0 and len(dets_for_log) > pdf_cap:
        dets_for_log = sorted(
            dets_for_log,
            key=lambda x: float(x.get("conf", 0) or 0),
            reverse=True,
        )[:pdf_cap]
        log_note_para = Paragraph(
            f"<i>Table lists the {pdf_cap} highest-confidence detections out of {len(dets)} total "
            f"(row cap keeps PDF generation fast on long videos). Summary metrics above use all detections.</i>",
            ST["body"],
        )

    if not dets:
        story.append(Paragraph("No detections above the confidence threshold.", ST["body"]))
    else:
        if log_note_para:
            story.append(log_note_para)
            story.append(Spacer(1, 6))
        hdr_style = ST["tbl_hdr"]
        show_frame_col = any(d.get("frame") is not None for d in dets_for_log)
        header_row = [
            Paragraph("#", hdr_style),
            Paragraph("Defect Class", hdr_style),
            Paragraph("Severity", hdr_style),
            Paragraph("Conf.", hdr_style),
            Paragraph("Bounding Box (px)", hdr_style),
            Paragraph("Area (px\u00B2)", hdr_style),
        ]
        if show_frame_col:
            header_row.insert(1, Paragraph("Frame", hdr_style))
        rows = [header_row]

        for d in dets_for_log:
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

            fn = d.get("frame")
            frame_cell = (
                Paragraph("—" if fn is None else str(int(fn)), ST["tbl_cell"])
                if show_frame_col
                else None
            )
            cls_raw = str(d.get("cls", "?")).replace("_", " ")
            conf_f = float(d.get("conf", 0) or 0)
            x1, y1, x2, y2 = d.get("x1"), d.get("y1"), d.get("x2"), d.get("y2")
            bbox_txt = f"({x1},{y1}) \u2192 ({x2},{y2})" if None not in (x1, y1, x2, y2) else "—"

            row_cells = [
                Paragraph(str(int(d.get("id", 0))), ST["tbl_cell"]),
                Paragraph(cls_raw, ST["tbl_cell_bold"]),
                sev_pill,
                Paragraph(f"{conf_f * 100:.1f}%", ST["tbl_cell"]),
                Paragraph(bbox_txt, ST["tbl_cell"]),
                Paragraph(f"{d.get('area', 0):,}", ST["tbl_cell"]),
            ]
            if show_frame_col:
                row_cells.insert(1, frame_cell)

            rows.append(row_cells)

        fixed_mm = 10 + 34 + 22 + 16 + 24
        if show_frame_col:
            fixed_mm += 14
        bbox_col_w = usable_w - fixed_mm * mm
        col_w = [10 * mm, 34 * mm, 22 * mm, 16 * mm, bbox_col_w, 24 * mm]
        if show_frame_col:
            col_w = [10 * mm, 14 * mm, 34 * mm, 22 * mm, 16 * mm, bbox_col_w, 24 * mm]
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

    # ─── INSPECTION PROVENANCE (survey audit) ────────────────────────
    story.extend(inspection_provenance_flowables(ST, usable_w, provenance or {}))

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


def _batch_aggregate_severity(batch_results):
    sev_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
    for r in batch_results:
        for d in r["dets"]:
            sev_counts[d.get("severity", "Medium")] += 1
    return sev_counts


def _batch_risk_level_label(sev_counts, total_detections):
    """Display risk tier + ReportLab colour (HIGH / CRITICAL use alert red like NCR samples)."""
    if total_detections == 0:
        return "LOW", SEV["Low"]
    alert_red = SEV["Critical"]
    if sev_counts.get("Critical", 0) > 0:
        return "CRITICAL", alert_red
    if sev_counts.get("High", 0) > 0:
        return "HIGH", alert_red
    if sev_counts.get("Medium", 0) > 0:
        return "MEDIUM", SEV["Medium"]
    return "LOW", SEV["Low"]


def _batch_unique_classes(batch_results):
    seen = set()
    order = []
    for r in batch_results:
        for d in r["dets"]:
            c = str(d.get("cls", "")).strip()
            if c and c not in seen:
                seen.add(c)
                order.append(c.replace("_", " "))
    return ", ".join(order) if order else ""


def _inspection_summary_ncr_table(
    ST,
    usable_w,
    inspection_id: str,
    date_disp: str,
    risk_level: str,
    risk_color,
    inference_ms,
    total_detections: int,
    classes_found: str,
):
    """Two-column × five-row summary grid (Inspection ID / Date / Risk / …)."""
    lbl_style = ParagraphStyle(
        "is_lbl",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=TEXT_MID,
    )
    val_style = ParagraphStyle(
        "is_val",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=TEXT_DARK,
    )
    risk_val_style = ParagraphStyle(
        "is_risk_lvl",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=risk_color,
    )
    em = "\u2014"
    if inference_ms is not None:
        inf_str = f"{float(inference_ms):.3f} ms"
    else:
        inf_str = em
    cls_str = classes_found if classes_found.strip() else em

    data = [
        [
            Paragraph("Inspection ID", lbl_style),
            Paragraph(inspection_id, val_style),
            Paragraph("Date", lbl_style),
            Paragraph(date_disp, val_style),
        ],
        [
            Paragraph("Risk Level", lbl_style),
            Paragraph(risk_level, risk_val_style),
            Paragraph("Inference Time", lbl_style),
            Paragraph(inf_str, val_style),
        ],
        [
            Paragraph("Total Detections", lbl_style),
            Paragraph(str(total_detections), val_style),
            Paragraph("Classes Found", lbl_style),
            Paragraph(cls_str, val_style),
        ],
        [
            Paragraph("Precision", lbl_style),
            Paragraph(em, val_style),
            Paragraph("Recall", lbl_style),
            Paragraph(em, val_style),
        ],
        [
            Paragraph("mAP@0.5", lbl_style),
            Paragraph(em, val_style),
            Paragraph("mAP@0.5:0.95", lbl_style),
            Paragraph(em, val_style),
        ],
    ]
    lw = usable_w * 0.22
    vw = usable_w * 0.28
    tbl = Table(data, colWidths=[lw, vw, lw, vw])
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), PANEL_ALT),
                ("BACKGROUND", (2, 0), (2, -1), PANEL_ALT),
                ("BACKGROUND", (1, 0), (1, -1), WHITE),
                ("BACKGROUND", (3, 0), (3, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.75, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return tbl


def build_batch_pdf(
    batch_results,
    vessel_name,
    inspector,
    pdf_password=None,
    inference_ms=None,
    provenance=None,
    mission_id=None,
    cover_ts=None,
    report_style="diver_hull",
    diver_meta=None,
):
    """
    Generate a batch PDF report for multiple images.
    batch_results: List of dicts with keys:
        filename, orig_img, enhanced_img, annotated_img, heatmap_img, dets, risk, grade
    inference_ms: optional wall time for full batch inference (ms).
    provenance: optional audit dict (same as ``build_pdf``).
    mission_id / cover_ts: optional; default matches legacy BATCH-{hash(ts+vessel)} behaviour.
    report_style: ``diver_hull`` (hull cleaning / PP diver-style pack) or ``nauticai`` (dashboard batch).
    diver_meta: optional dict for ``diver_hull`` (imo, place, activity, job_number, vessel_type, ...).
    """
    rs = (report_style or "diver_hull").strip().lower().replace("-", "_")
    if rs in ("diver", "diver_hull", "hull_diver", "panama_style"):
        from diver_style_hull_pdf import build_diver_style_batch_pdf

        return build_diver_style_batch_pdf(
            batch_results=batch_results,
            vessel_name=vessel_name,
            inspector=inspector,
            pdf_password=pdf_password,
            mission_id=mission_id,
            cover_ts=cover_ts,
            diver_meta=diver_meta or {},
        )

    buf = io.BytesIO()
    usable_w = PAGE_W - 2 * MARGIN
    ts = cover_ts or datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    mission_id = mission_id or f"BATCH-{hashlib.sha256((ts + vessel_name).encode()).hexdigest()[:8]}"
    meta = {
        "mission_id": mission_id,
        "vessel": vessel_name or "N/A",
        "model": "NautiCAI Vision Engine",
        "date": ts,
    }
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=24 * mm,
        bottomMargin=16 * mm,
        title=f"NautiCAI Batch Report — {mission_id}",
        author="NautiCAI — Singapore Maritime AI Systems",
    )
    ST = _styles()
    story = []
    cover_tbl = Table(
        [
            [
                Paragraph(
                    "NautiCAI",
                    ParagraphStyle(
                        "ct",
                        fontName="Helvetica-Bold",
                        fontSize=32,
                        leading=38,
                        textColor=WHITE,
                    ),
                ),
            ],
            [
                Paragraph(
                    "BATCH INSPECTION REPORT",
                    ParagraphStyle(
                        "cs",
                        fontName="Helvetica-Bold",
                        fontSize=14,
                        leading=18,
                        textColor=colors.HexColor("#0EA5E9"),
                    ),
                ),
            ],
            [Spacer(1, 4)],
            [
                Paragraph(
                    f"Mission <b>{mission_id}</b>&nbsp;&nbsp;|&nbsp;&nbsp;"
                    f"Vessel <b>{vessel_name or 'N/A'}</b>&nbsp;&nbsp;|&nbsp;&nbsp;"
                    f"Inspector <b>{inspector}</b>",
                    ParagraphStyle(
                        "cm",
                        fontName="Helvetica",
                        fontSize=9.5,
                        leading=14,
                        textColor=colors.HexColor("#94A3B8"),
                    ),
                ),
            ],
            [
                Paragraph(
                    f"{ts}&nbsp;&nbsp;|&nbsp;&nbsp;Total Images: {len(batch_results)}",
                    ParagraphStyle(
                        "cd",
                        fontName="Helvetica",
                        fontSize=9,
                        leading=13,
                        textColor=colors.HexColor("#64748B"),
                    ),
                ),
            ],
        ],
        colWidths=[usable_w],
    )
    cover_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (0, 0), 20),
                ("BOTTOMPADDING", (0, 0), (-1, -2), 4),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 18),
                ("LEFTPADDING", (0, 0), (-1, -1), 20),
                ("RIGHTPADDING", (0, 0), (-1, -1), 20),
            ]
        )
    )
    story.append(cover_tbl)
    story.append(Spacer(1, 10))

    total_detections = sum(len(r["dets"]) for r in batch_results)
    sev_counts = _batch_aggregate_severity(batch_results)
    risk_lvl, risk_col = _batch_risk_level_label(sev_counts, total_detections)
    classes_line = _batch_unique_classes(batch_results)
    day_stamp = datetime.datetime.now()
    date_disp = day_stamp.strftime("%d %b %Y")
    ncr_suffix = hashlib.sha256(f"{mission_id}{ts}{vessel_name}".encode()).hexdigest()[:8].upper()
    inspection_id_fmt = f"NCR-{day_stamp:%Y%m%d}-{ncr_suffix}"

    grades = [r["grade"] for r in batch_results]
    risks = [r["risk"] for r in batch_results]
    summary_tbl = Table(
        [
            ["Total Images", str(len(batch_results)), "Total Detections", str(total_detections)],
            [
                "Critical",
                str(sev_counts["Critical"]),
                "High",
                str(sev_counts["High"]),
            ],
            [
                "Medium",
                str(sev_counts["Medium"]),
                "Low",
                str(sev_counts["Low"]),
            ],
            ["Grades", ", ".join(grades), "Risk Scores", ", ".join(str(x) for x in risks)],
        ],
        colWidths=[38 * mm, 38 * mm, 38 * mm, 38 * mm],
    )
    summary_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PANEL),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    insp_tbl = _inspection_summary_ncr_table(
        ST,
        usable_w,
        inspection_id_fmt,
        date_disp,
        risk_lvl,
        risk_col,
        inference_ms,
        total_detections,
        classes_line,
    )
    first_page_summaries = [
        Paragraph("Inspection summary", ST["h2"]),
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=ACCENT_LINE,
            spaceAfter=8,
            spaceBefore=0,
        ),
        insp_tbl,
        Spacer(1, 12),
    ]
    first_page_summaries += _section("Batch Summary", ST)
    first_page_summaries.append(summary_tbl)
    first_page_summaries.append(Spacer(1, 10))
    for el in first_page_summaries:
        story.append(el)

    for idx, r in enumerate(batch_results):
        story.append(PageBreak())
        img_id = f"IMG-{idx + 1}-{hashlib.sha256(r['filename'].encode()).hexdigest()[:4].upper()}"
        story += _section(f"Image {idx + 1} — {r['filename']}", ST)
        story.append(
            _dashboard_results_banner(r["dets"], r["risk"], r["grade"], img_id, usable_w, "")
        )
        story.append(Spacer(1, 8))
        enh = r.get("enhanced_img") if r.get("enhanced_img") is not None else r.get("orig_img")
        story.append(
            _four_panel_grid(
                r.get("orig_img"),
                enh,
                r.get("annotated_img"),
                r.get("heatmap_img"),
                usable_w,
                cell_h_mm=48,
            )
        )
        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                f"Grade: {r['grade']} | Inspection score: {r['risk']}% | "
                f"Detections: {len(r['dets'])}",
                ST["body_sm"],
            )
        )
        if r["dets"]:
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
            for d in r["dets"]:
                sev = d.get("severity", "Medium")
                sev_col = SEV.get(sev, TEXT_DARK)
                sev_bg = SEV_BG.get(sev, WHITE)
                sev_style_key = hashlib.sha256(str(sev).encode()).hexdigest()[:12]
                try:
                    conf_v = float(d.get("conf", 0) or 0)
                    if not math.isfinite(conf_v):
                        conf_v = 0.0
                    conf_txt = f"{conf_v * 100:.1f}%"
                except (TypeError, ValueError):
                    conf_txt = "—"
                try:
                    det_id = int(d.get("id", 0))
                except (TypeError, ValueError):
                    det_id = 0
                cls_txt = str(d.get("cls", "?")).replace("_", " ")
                bbox_txt = _batch_bbox_cell_txt(d)
                try:
                    area_v = int(d.get("area", 0) or 0)
                except (TypeError, ValueError):
                    area_v = 0
                sev_pill = Table(
                    [
                        [
                            Paragraph(
                                str(sev),
                                ParagraphStyle(
                                    "sp_" + sev_style_key,
                                    fontName="Helvetica-Bold",
                                    fontSize=7.5,
                                    leading=10,
                                    textColor=sev_col,
                                    alignment=TA_CENTER,
                                ),
                            )
                        ]
                    ],
                    colWidths=[50],
                )
                sev_pill.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), sev_bg),
                            ("BOX", (0, 0), (-1, -1), 0.5, sev_col),
                            ("TOPPADDING", (0, 0), (-1, -1), 2),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ("LEFTPADDING", (0, 0), (-1, -1), 4),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ]
                    )
                )
                rows.append(
                    [
                        Paragraph(f"{det_id:02d}", ST["tbl_cell"]),
                        Paragraph(cls_txt, ST["tbl_cell_bold"]),
                        sev_pill,
                        Paragraph(conf_txt, ST["tbl_cell"]),
                        Paragraph(bbox_txt, ST["tbl_cell"]),
                        Paragraph(f"{area_v:,}", ST["tbl_cell"]),
                    ]
                )
            bbox_col_w = usable_w - (10 + 34 + 22 + 16 + 24) * mm
            col_w = [10 * mm, 34 * mm, 22 * mm, 16 * mm, bbox_col_w, 24 * mm]
            det_tbl = Table(rows, colWidths=col_w, repeatRows=1)
            det_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PANEL]),
                        ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                        ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            story.append(det_tbl)
        story.append(Spacer(1, 8))

    story.append(PageBreak())
    story += _section("Batch Inspection Summary", ST)
    story.append(Paragraph(f"Total Images: {len(batch_results)}", ST["body_sm"]))
    story.append(Paragraph(f"Total Detections: {total_detections}", ST["body_sm"]))
    story.append(Paragraph(f"Severity Distribution: {sev_counts}", ST["body_sm"]))
    story.append(Paragraph(f"Grades: {', '.join(grades)}", ST["body_sm"]))
    story.append(Paragraph(f"Risk Scores: {', '.join(str(x) for x in risks)}", ST["body_sm"]))
    story.extend(inspection_provenance_flowables(ST, usable_w, provenance or {}))
    doc.build(
        story,
        onFirstPage=lambda c, d: _header_footer(c, d, meta),
        onLaterPages=lambda c, d: _header_footer(c, d, meta),
    )
    buf.seek(0)
    out = buf.getvalue()
    if pdf_password and str(pdf_password).strip():
        try:
            from io import BytesIO
            from pypdf import PdfReader, PdfWriter

            r = PdfReader(BytesIO(out))
            w = PdfWriter()
            for page in r.pages:
                w.add_page(page)
            w.encrypt(str(pdf_password).strip())
            bo = BytesIO()
            w.write(bo)
            return bo.getvalue()
        except Exception:
            return out
    return out

