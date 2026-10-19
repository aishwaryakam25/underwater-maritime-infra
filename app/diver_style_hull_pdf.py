"""
Hull cleaning & propeller polishing diver-style report (multi-page pack layout).

Structured like a conventional hull-cleaning job PDF: cover, index, vessel block,
scope / executive summary, fouling executive grid, photographic sections by hull
zone, then closing certificates. Branding uses Nautica AI / NautiCAI defaults.
"""
from __future__ import annotations

import hashlib
import io
import math
import os
import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import pdf_report as pr

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
BOTTOM_PAD = 26 * mm  # room for diver footer block


def _ordinal_day(d: int) -> str:
    if 11 <= d <= 13:
        return f"{d}th"
    return f"{d}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(d % 10, 'th')}"


def _cover_date_line(cover_ts: str) -> str:
    try:
        dt = datetime.datetime.strptime(cover_ts[:19], "%Y-%m-%d  %H:%M:%S")
    except ValueError:
        dt = datetime.datetime.now()
    return f"{dt.strftime('%B')} {_ordinal_day(dt.day)}, {dt.year}."


def _form_ref_line(cover_ts: str) -> str:
    try:
        dt = datetime.datetime.strptime(cover_ts[:19], "%Y-%m-%d  %H:%M:%S")
    except ValueError:
        dt = datetime.datetime.now()
    return f"NAI-OPE-F009-Rev.1-{dt.strftime('%B-%Y')}"


def _default_job_number(mission_id: Optional[str], cover_ts: str) -> str:
    yr = cover_ts[:4] if len(cover_ts) >= 4 else str(datetime.datetime.now().year)
    suf = (mission_id or "X")[-6:].upper().replace("-", "")
    if len(suf) < 3:
        suf = "001"
    return f"NAI-{yr}-{suf}"


def _split_into_buckets(items: Sequence[Any], n_buckets: int) -> List[List[Any]]:
    n = len(items)
    if n_buckets <= 0:
        return []
    if n == 0:
        return [[] for _ in range(n_buckets)]
    base, extra = divmod(n, n_buckets)
    out: List[List[Any]] = []
    pos = 0
    for i in range(n_buckets):
        sz = base + (1 if i < extra else 0)
        out.append(list(items[pos : pos + sz]))
        pos += sz
    return out


def _chapter_page_estimate(bucket: List[Any]) -> int:
    if not bucket:
        return 0
    n_pairs = len(bucket)
    pairs_per_page = 2
    return max(1, math.ceil(n_pairs / pairs_per_page))


def _toc_dots(label: str, page_num: int, width_chars: int = 72) -> str:
    """Monospace TOC line with dot leaders (approximate)."""
    page_s = str(page_num)
    core = f"{label} {page_s}"
    if len(core) >= width_chars:
        return f"{label[: width_chars - len(page_s) - 2]}.. {page_s}"
    dots_n = width_chars - len(label) - len(page_s)
    dots_n = max(3, dots_n)
    return label + ("." * dots_n) + page_s


def _diver_footer_canvas(meta: Dict[str, Any]):
    def _draw(canvas, doc):
        canvas.saveState()
        W, H = PAGE_W, PAGE_H
        foot_top = 18 * mm
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(pr.TEXT_DARK)
        canvas.drawString(MARGIN, foot_top, f"Vessel: {meta['vessel']}")
        canvas.drawString(MARGIN, foot_top - 3.6 * mm, f"Date: {meta['date_line']}")
        canvas.drawString(MARGIN, foot_top - 7.2 * mm, f"Job N°: {meta['job']}")
        canvas.drawString(MARGIN, foot_top - 10.8 * mm, meta["form_ref"])
        url_disp = meta["website"]
        url_href = meta.get("website_url") or (
            f"https://{url_disp}" if url_disp and "://" not in url_disp else url_disp
        )
        canvas.setFillColor(colors.HexColor("#1D4ED8"))
        tw = canvas.stringWidth(url_disp, "Helvetica", 8)
        canvas.drawString(MARGIN, foot_top - 14.4 * mm, url_disp)
        canvas.linkURL(
            url_href,
            (MARGIN, foot_top - 15.6 * mm, MARGIN + tw + 2, foot_top - 13.2 * mm),
            relative=0,
        )
        canvas.setFillColor(pr.TEXT_DARK)
        tp = meta.get("total_pages") or doc.page
        canvas.drawRightString(W - MARGIN, foot_top - 7 * mm, f"-- {doc.page} of {tp} --")
        canvas.restoreState()

    return _draw


def _plain_styles():
    body = ParagraphStyle(
        "dv_body",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=pr.TEXT_DARK,
        alignment=TA_LEFT,
    )
    body_sm = ParagraphStyle("dv_bsm", parent=body, fontSize=8.5, leading=11)
    h1 = ParagraphStyle(
        "dv_h1",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=pr.BLACK,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    h2 = ParagraphStyle(
        "dv_h2",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=pr.BLACK,
        alignment=TA_LEFT,
        spaceBefore=8,
        spaceAfter=4,
    )
    cov = ParagraphStyle(
        "dv_cov",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=13,
        textColor=pr.BLACK,
        alignment=TA_CENTER,
    )
    cov_lbl = ParagraphStyle(
        "dv_cov_lbl",
        fontName="Helvetica",
        fontSize=10,
        leading=12,
        textColor=pr.BLACK,
        alignment=TA_CENTER,
    )
    toc = ParagraphStyle(
        "dv_toc",
        fontName="Courier",
        fontSize=8.5,
        leading=11,
        textColor=pr.TEXT_DARK,
        alignment=TA_LEFT,
    )
    return {"body": body, "body_sm": body_sm, "h1": h1, "h2": h2, "cov": cov, "cov_lbl": cov_lbl, "toc": toc}


def _cover_story(meta: Dict[str, Any], usable_w: float, ST) -> List:
    ops_email = meta.get("ops_email") or os.environ.get("NAUTICAI_OPS_EMAIL", "ops@nauticai-ai.com")
    tel = meta.get("tel") or os.environ.get("NAUTICAI_TEL", "+65 0000 0000")
    addr = meta.get("address") or "Singapore"
    lines = [
        Paragraph(meta["form_ref"], ST["cov_lbl"]),
        Spacer(1, 10),
        Paragraph("Vessel Name", ST["cov_lbl"]),
        Paragraph(f"<b>{pr._xml_esc(meta['vessel'])}</b>", ST["cov"]),
        Spacer(1, 6),
        Paragraph("IMO:", ST["cov_lbl"]),
        Paragraph(f"<b>{pr._xml_esc(meta.get('imo') or 'N/A')}</b>", ST["cov"]),
        Spacer(1, 6),
        Paragraph("ACTIVITY", ST["cov_lbl"]),
        Paragraph(f"<b>{pr._xml_esc(meta['activity'])}</b>", ST["cov"]),
        Spacer(1, 6),
        Paragraph("DATE:", ST["cov_lbl"]),
        Paragraph(f"<b>{pr._xml_esc(meta['date_line'])}</b>", ST["cov"]),
        Spacer(1, 6),
        Paragraph("PLACE:", ST["cov_lbl"]),
        Paragraph(f"<b>{pr._xml_esc(meta['place'])}</b>", ST["cov"]),
        Spacer(1, 6),
        Paragraph("JOB NUMBER:", ST["cov_lbl"]),
        Paragraph(f"<b>{pr._xml_esc(meta['job'])}</b>", ST["cov"]),
        Spacer(1, 14),
        Paragraph(f"E-mail {pr._xml_esc(ops_email)}", ST["cov_lbl"]),
        Paragraph("<b>NAUTICA AI.</b>", ST["cov"]),
        Paragraph(pr._xml_esc(addr) + ".", ST["cov_lbl"]),
        Paragraph(f"Tel: {pr._xml_esc(tel)}", ST["cov_lbl"]),
        Paragraph(pr._xml_esc(meta["website"]), ST["cov_lbl"]),
    ]
    return lines


# (TOC label, section heading on photo pages, before caption, after caption)
PHOTO_CHAPTERS: Tuple[Tuple[str, str, str, str], ...] = (
    ("Bow section.", "Bow section.", "View of Bow section - Before cleaning.", "View of Bow section - After cleaning."),
    (
        "Vertical sides.",
        "Vertical Port side.",
        "View of vertical sides – Before cleaning.",
        "View of vertical sides – After cleaning.",
    ),
    (
        "Vertical sides.",
        "Vertical STB side.",
        "View of vertical sides – Before cleaning.",
        "View of vertical sides – After cleaning.",
    ),
    (
        "Bilge keels.",
        "Bilge keels – STB side.",
        "View of Bilge keels – Before cleaning.",
        "View of Bilge keels – After cleaning.",
    ),
    (
        "Bilge keels.",
        "Bilge keels Port side.",
        "View of Bilge keels – Before cleaning.",
        "View of Bilge keels – After cleaning.",
    ),
    ("Flat bottom.", "Flat bottom.", "View of flat bottom-Before cleaning.", "View of flat bottom – After cleaning."),
    ("Stern section.", "Stern section.", "View of stern section – Before cleaning.", "View of stern section – After cleaning"),
    (
        "Sea chest gratings.",
        "Sea chest gratings.",
        "View of sea chest gratings – Before cleaning.",
        "View of sea chest gratings – After cleaning.",
    ),
    ("Rudder.", "Rudder.", "View of Rudder - Before cleaning.", "View of Rudder - After cleaning."),
    (
        "Rope guard.",
        "Rope guard.",
        "View of Rope guard - Fishing net presence.",
        "View of Rope guard - Clear.",
    ),
    (
        "Propeller.",
        "Propeller polish.",
        "View of propeller blade – Before polish.",
        "View of propeller blade – After polish.",
    ),
)


def _photo_pair_block(
    r: Dict[str, Any],
    cap_before: str,
    cap_after: str,
    outer_w: float,
    img_h: float,
    ST,
) -> Table:
    """One before/after pair; ``outer_w`` is total width for both columns."""
    pad = 6 * mm
    cell_w = max(26 * mm, (outer_w - pad) / 2)
    before_img = r.get("orig_img") or r.get("enhanced_img")
    after_img = r.get("annotated_img") or r.get("enhanced_img") or before_img
    cap_style = ParagraphStyle(
        "dv_cap",
        parent=ST["body_sm"],
        fontSize=7.5,
        leading=10,
        alignment=TA_CENTER,
    )
    c1 = Paragraph(pr._xml_esc(cap_before), cap_style)
    c2 = Paragraph(pr._xml_esc(cap_after), cap_style)
    im1 = pr._pil_to_rl(before_img, cell_w - 4 * mm, img_h) if before_img is not None else Paragraph("<i>No image</i>", ST["body_sm"])
    im2 = pr._pil_to_rl(after_img, cell_w - 4 * mm, img_h) if after_img is not None else Paragraph("<i>No image</i>", ST["body_sm"])
    t = Table([[c1, c2], [im1, im2]], colWidths=[cell_w, cell_w])
    t.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOX", (0, 0), (-1, -1), 0.35, pr.BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, pr.BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def _two_pair_page(chapter_heading: str, batch_slice: List[Dict], cb: str, ca: str, usable_w: float, ST) -> List:
    """Up to two hull frames side-by-side (each frame is before|after)."""
    gap_mid = 4 * mm
    col_w = (usable_w - gap_mid) / 2
    img_h = 52 * mm
    out: List = []
    out.append(Paragraph(pr._xml_esc(chapter_heading), ST["h2"]))
    for i in range(0, len(batch_slice), 2):
        chunk = batch_slice[i : i + 2]
        if len(chunk) == 1:
            out.append(_photo_pair_block(chunk[0], cb, ca, usable_w - 2 * mm, img_h, ST))
        else:
            left = _photo_pair_block(chunk[0], cb, ca, col_w - 1 * mm, img_h, ST)
            right = _photo_pair_block(chunk[1], cb, ca, col_w - 1 * mm, img_h, ST)
            row_tbl = Table([[left, right]], colWidths=[col_w, col_w])
            row_tbl.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ]
                )
            )
            out.append(row_tbl)
        out.append(Spacer(1, 6))
    return out


def build_diver_style_batch_pdf(
    batch_results: List[Dict[str, Any]],
    vessel_name: str,
    inspector: str,
    pdf_password: Optional[str] = None,
    mission_id: Optional[str] = None,
    cover_ts: Optional[str] = None,
    diver_meta: Optional[Dict[str, Any]] = None,
) -> bytes:
    diver_meta = diver_meta or {}
    ts = cover_ts or datetime.datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    if not mission_id:
        mission_id = f"BATCH-{hashlib.sha256(ts.encode()).hexdigest()[:8]}"

    website = diver_meta.get("website") or os.environ.get("NAUTICAI_WEB_URL", "https://www.nauticai-ai.com")
    date_line = diver_meta.get("date_line") or _cover_date_line(ts)
    form_ref = diver_meta.get("form_ref") or _form_ref_line(ts)
    job = diver_meta.get("job_number") or _default_job_number(mission_id, ts)

    buckets = _split_into_buckets(batch_results, len(PHOTO_CHAPTERS))
    photo_pages = sum(_chapter_page_estimate(b) for b in buckets)
    fixed_pages = 5
    cert_pages = 4
    total_pages_est = fixed_pages + photo_pages + cert_pages

    web_disp = website.replace("https://", "").replace("http://", "").strip()
    web_href = website if str(website).startswith("http") else f"https://{web_disp}"
    meta_foot = {
        "vessel": vessel_name or "N/A",
        "date_line": date_line,
        "job": job,
        "form_ref": form_ref,
        "website": web_disp,
        "website_url": web_href,
        "total_pages": total_pages_est,
    }

    buf = io.BytesIO()
    usable_w = PAGE_W - 2 * MARGIN
    ST = _plain_styles()
    story: List = []

    # --- Page estimates for TOC ---
    p_cursor = 6
    toc_photo_lines: List[Tuple[str, int]] = []
    for (_, heading, _, _), bucket in zip(PHOTO_CHAPTERS, buckets):
        if not bucket:
            continue
        toc_photo_lines.append((heading, p_cursor))
        p_cursor += _chapter_page_estimate(bucket)

    cert_labels = [
        "ACP Approval.",
        "Notice of work.",
        "Work confirmation.",
        "Work certificate.",
    ]
    cert_start = p_cursor
    toc_cert = [(lab, cert_start + i) for i, lab in enumerate(cert_labels)]

    toc_fixed = [
        ("Front page.", 1),
        ("Index.", 2),
        ("Vessel’s general information.", 3),
        ("Scope of work.", 3),
        ("Client’s instructions.", 4),
        ("Executive Summary.", 4),
        ("Underwater inspection check list.", 5),
    ]

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=14 * mm,
        bottomMargin=BOTTOM_PAD,
        title=f"Hull Cleaning Report — {vessel_name}",
        author="Nautica AI",
    )

    # Cover
    meta_cover = {
        **meta_foot,
        "imo": diver_meta.get("imo") or diver_meta.get("vessel_imo") or "",
        "activity": diver_meta.get("activity") or "U/W Hull Cleaning & Propeller polishing.",
        "place": diver_meta.get("place") or diver_meta.get("report_place") or "As per attendance.",
        "ops_email": diver_meta.get("ops_email"),
        "tel": diver_meta.get("tel"),
        "address": diver_meta.get("address"),
        "form_ref": form_ref,
        "date_line": date_line,
        "job": job,
        "vessel": vessel_name or "N/A",
        "website": website.replace("https://", "").replace("http://", ""),
    }
    story.extend(_cover_story(meta_cover, usable_w, ST))
    story.append(PageBreak())

    # Index
    story.append(Paragraph("Index.", ST["h1"]))
    story.append(Spacer(1, 8))
    toc_lines = toc_fixed + toc_photo_lines + toc_cert
    # closing page line like sample
    closing_pg = total_pages_est
    toc_lines.append(("Closing page.", closing_pg))

    for label, pg in toc_lines:
        story.append(Paragraph(pr._xml_esc(_toc_dots(label, pg)), ST["toc"]))
    story.append(PageBreak())

    # Vessel general information + scope table (single page)
    story.append(Paragraph("Vessel’s general information.", ST["h1"]))
    vessel_type = diver_meta.get("vessel_type") or diver_meta.get("type") or "—"
    loc = diver_meta.get("place") or "As per attendance."
    loa = diver_meta.get("loa_m") or "—"
    beam = diver_meta.get("beam_m") or "—"
    draft_txt = diver_meta.get("draft_text") or "Fwd / aft as per master."
    hours_txt = diver_meta.get("service_hours") or f"{len(batch_results)} media frames processed."
    sup_txt = diver_meta.get("support_vessel") or "—"
    sup_hrs = diver_meta.get("support_hours") or "—"
    supervisor = diver_meta.get("supervisor") or inspector or "—"
    equip = diver_meta.get("equipment") or "Surface supplied air Diver / ROV imagery."
    water = diver_meta.get("water_condition") or "As recorded."
    sea_s = diver_meta.get("sea_state") or "As recorded."
    curr = diver_meta.get("currents") or "As recorded."
    vis = diver_meta.get("visibility_m") or "—"

    vtbl = Table(
        [
            ["Vessel name", vessel_name or "N/A", "IMO", diver_meta.get("imo") or diver_meta.get("vessel_imo") or "—"],
            ["", vessel_type, "Location", loc],
            [
                "Attendance",
                diver_meta.get("attendance_text") or f"Batch inspection {date_line}",
                "LOA (m)",
                loa,
            ],
            ["", "", "Beam (m)", beam],
            ["Draft (m)", draft_txt, "", ""],
            ["Total Hours of service", hours_txt, "", ""],
            ["Diver's support work boat / Launch name", sup_txt, "", ""],
            ["Hours of service", sup_hrs, "", ""],
            ["Diving supervisor & Equipment.", "", "", ""],
            ["Diving Supervisor", supervisor, "Equipment", equip],
            ["Water condition", water, "Sea state", sea_s],
            ["Currents", curr, "Visibility", vis],
        ],
        colWidths=[42 * mm, 52 * mm, 38 * mm, usable_w - 132 * mm],
    )
    vtbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, pr.BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(vtbl)
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "<b>Scope of work:</b> "
            + pr._xml_esc(diver_meta.get("activity") or "U/W Hull Cleaning & Propeller polishing."),
            ST["body"],
        )
    )
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Repair Job:</b> " + pr._xml_esc(diver_meta.get("repair_job") or "As noted in AI defect log."), ST["body"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>Services Offered:</b> (see operations log)", ST["body_sm"]))
    story.append(PageBreak())

    # Client / executive text (page 4)
    story.append(Paragraph("Client’s instructions.", ST["h2"]))
    story.append(
        Paragraph(
            "- After completing all paperwork, safety and dive briefs, we commenced the U/W Hull "
            "cleaning &amp; propeller polishing job.<br/>"
            "- Findings below combine diver-style hull zones with Nautica AI vision QC on uploaded frames.",
            ST["body"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(Paragraph("Executive Summary.", ST["h2"]))
    story.append(
        Paragraph(
            f"- On {pr._xml_esc(date_line)} our team commenced recording alongside the vessel.<br/>"
            "- U/W hull cleaning job progression is documented photographically by hull zone.<br/>"
            "- Attached photos of the operations / uploaded inspection frames.",
            ST["body"],
        )
    )
    story.append(PageBreak())

    # Fouling executive summary (page 5)
    story.append(Paragraph("Underwater inspection check list.", ST["h2"]))
    story.append(Spacer(1, 6))
    pr_st = pr._styles()
    fouling_rows = diver_meta.get("hull_fouling_rows")
    story.extend(
        pr._hull_fouling_executive_summary_flowables(
            pr_st, usable_w, fouling_rows=fouling_rows, include_annex_note=False
        )
    )

    # Photographic sections
    for (_toc_lbl, heading, cb, ca), bucket in zip(PHOTO_CHAPTERS, buckets):
        if not bucket:
            continue
        pages_needed = _chapter_page_estimate(bucket)
        pos = 0
        for _pn in range(pages_needed):
            slice_rows = bucket[pos : pos + 2]
            pos += 2
            story.append(PageBreak())
            story.extend(_two_pair_page(heading, slice_rows, cb, ca, usable_w, ST))

    # Certificates
    story.append(PageBreak())
    story.append(Paragraph(cert_labels[0], ST["h1"]))
    story.append(Spacer(1, 20))
    story.append(PageBreak())
    story.append(Paragraph(cert_labels[1], ST["h1"]))
    story.append(
        Paragraph(
            "This is to certify that underwater Cleaning / inspection / Repair works / has been "
            "satisfactorily accepted as far as it can be ascertained.",
            ST["body"],
        )
    )
    story.append(PageBreak())
    story.append(Paragraph(cert_labels[2], ST["h1"]))
    story.append(Spacer(1, 30))
    story.append(PageBreak())
    story.append(Paragraph(cert_labels[3], ST["h1"]))
    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            f"Prepared by: {pr._xml_esc(diver_meta.get('prepared_by') or inspector or '—')}<br/>"
            f"1st Review: {pr._xml_esc(diver_meta.get('review_1') or '—')}<br/>"
            f"2nd Review and approval: {pr._xml_esc(diver_meta.get('review_2') or '—')}",
            ST["body"],
        )
    )
    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>Closing page.</b>", ST["h2"]))

    footer_cb = _diver_footer_canvas(meta_foot)
    doc.build(story, onFirstPage=footer_cb, onLaterPages=footer_cb)

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
