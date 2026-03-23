"""
pdf_report.py  —  PDF Report Generator for LCY3 AFM Dashboard
Generates a professional multi-page PDF report using ReportLab.
"""

import io
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Colour palette ────────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#1a237e")
INDIGO    = colors.HexColor("#3949ab")
LIGHT_BG  = colors.HexColor("#e8eaf6")
RED       = colors.HexColor("#d32f2f")
ORANGE    = colors.HexColor("#f57c00")
GREEN     = colors.HexColor("#388e3c")
WHITE     = colors.white
GREY      = colors.HexColor("#666666")
LIGHT_GREY = colors.HexColor("#f5f5f5")

DEFAULT_THRESHOLD = 5
THRESHOLDS = {"Amnesty": 10, "Drive Lacking Capability": 10}
NO_THRESHOLD = ["Unreachable Charger"]


def _get_threshold(andon_type):
    if andon_type in NO_THRESHOLD:
        return None
    return THRESHOLDS.get(andon_type, DEFAULT_THRESHOLD)


def _status_color(avg, threshold):
    if threshold is None:
        return GREEN
    if avg > threshold * 1.5:
        return RED
    elif avg > threshold:
        return ORANGE
    return GREEN


# ── Styles ────────────────────────────────────────────────────────────────────
def _get_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ReportTitle",
        fontSize=24, textColor=WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="ReportSubtitle",
        fontSize=11, textColor=colors.HexColor("#c5cae9"),
        fontName="Helvetica", alignment=TA_CENTER, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontSize=14, textColor=NAVY, fontName="Helvetica-Bold",
        spaceBefore=14, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="SubHeader",
        fontSize=11, textColor=INDIGO, fontName="Helvetica-Bold",
        spaceBefore=8, spaceAfter=4
    ))
    styles.add(ParagraphStyle(
        name="BodyText2",
        fontSize=9, textColor=colors.HexColor("#333333"),
        fontName="Helvetica", spaceAfter=3
    ))
    styles.add(ParagraphStyle(
        name="SmallGrey",
        fontSize=8, textColor=GREY,
        fontName="Helvetica", spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="KPIValue",
        fontSize=20, textColor=NAVY, fontName="Helvetica-Bold",
        alignment=TA_CENTER
    ))
    styles.add(ParagraphStyle(
        name="KPILabel",
        fontSize=8, textColor=GREY, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=2
    ))
    styles.add(ParagraphStyle(
        name="Footer",
        fontSize=8, textColor=GREY, fontName="Helvetica",
        alignment=TA_CENTER
    ))
    return styles


# ── Header/Footer canvas ──────────────────────────────────────────────────────
def _header_footer(canvas, doc, report_type, generated_at):
    canvas.saveState()
    w, h = A4

    # Header bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 45, w, 45, fill=1, stroke=0)
    canvas.setFillColor(INDIGO)
    canvas.rect(0, h - 50, w, 5, fill=1, stroke=0)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(1.5 * cm, h - 30, f"LCY3 AFM Dashboard — {report_type}")
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(w - 1.5 * cm, h - 30, f"Generated: {generated_at}")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 1.5 * cm, h - 42, f"Made by Manish Karki")

    # Footer
    canvas.setFillColor(LIGHT_BG)
    canvas.rect(0, 0, w, 28, fill=1, stroke=0)
    canvas.setFillColor(INDIGO)
    canvas.rect(0, 27, w, 2, fill=1, stroke=0)
    canvas.setFillColor(GREY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(1.5 * cm, 10, "LCY3 AFM Dashboard  |  Confidential")
    canvas.drawRightString(w - 1.5 * cm, 10, f"Page {doc.page}")

    canvas.restoreState()


# ── KPI table ─────────────────────────────────────────────────────────────────
def _kpi_table(fdf, within_threshold_fn, styles):
    within_pct = fdf.apply(within_threshold_fn, axis=1).mean() * 100
    eff = (fdf.groupby("Resolver").agg(n=("Resolve_Min", "count"), avg=("Resolve_Min", "mean"))
           .apply(lambda r: r["n"] / r["avg"] if r["avg"] > 0 else 0, axis=1).mean())

    kpis = [
        ("Total Andons", f"{len(fdf):,}"),
        ("Avg Resolve Time", f"{fdf['Resolve_Min'].mean():.2f} min"),
        ("Median Time", f"{fdf['Resolve_Min'].median():.2f} min"),
        ("% Within Threshold", f"{within_pct:.1f}%"),
        ("Avg Efficiency", f"{eff:.1f}"),
    ]

    cells = []
    for label, value in kpis:
        cells.append([
            Paragraph(value, styles["KPIValue"]),
            Paragraph(label, styles["KPILabel"]),
        ])

    # Build as a single row of 5 KPI boxes
    row_vals = [Paragraph(v, styles["KPIValue"]) for _, v in kpis]
    row_lbls = [Paragraph(l, styles["KPILabel"]) for l, _ in kpis]

    col_w = (A4[0] - 3 * cm) / 5
    tbl = Table(
        [row_vals, row_lbls],
        colWidths=[col_w] * 5,
        rowHeights=[28, 16]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), LIGHT_BG),
        ("BACKGROUND",  (0, 0), (-1, 0),  WHITE),
        ("BOX",         (0, 0), (-1, -1), 0.5, INDIGO),
        ("INNERGRID",   (0, 0), (-1, -1), 0.5, INDIGO),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("ALIGN",       (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


# ── Leaderboard table ─────────────────────────────────────────────────────────
def _leaderboard_table(fdf, within_threshold_fn, styles):
    lb = (fdf.groupby("Resolver")
          .agg(Total=("Resolve_Min", "count"), Avg=("Resolve_Min", "mean"))
          .reset_index())
    lb["Avg"] = lb["Avg"].round(2)
    lb["Eff"] = (lb["Total"] / lb["Avg"]).round(2)
    lb["Pct"] = fdf.groupby("Resolver").apply(
        lambda g: g.apply(within_threshold_fn, axis=1).mean() * 100
    ).round(1).values
    lb = lb.sort_values("Avg").reset_index(drop=True)
    lb.index += 1

    headers = ["Rank", "Resolver", "Total Andons", "Avg Time (min)", "Efficiency", "% On Target", "Status"]
    col_w = [(A4[0] - 3 * cm) / 7] * 7
    col_w[1] = 3.5 * cm  # wider for resolver name

    data = [[Paragraph(h, ParagraphStyle("H", fontSize=8, textColor=WHITE,
                fontName="Helvetica-Bold", alignment=TA_CENTER)) for h in headers]]

    for rank, row in lb.iterrows():
        t = _get_threshold(None)
        if row["Avg"] > DEFAULT_THRESHOLD * 1.5:
            status = "Slow"
            sc = RED
        elif row["Avg"] > DEFAULT_THRESHOLD:
            status = "Above Target"
            sc = ORANGE
        else:
            status = "On Target"
            sc = GREEN

        data.append([
            Paragraph(str(rank), ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(row["Resolver"]), ParagraphStyle("C", fontSize=8)),
            Paragraph(f"{int(row['Total']):,}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{row['Avg']:.2f}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{row['Eff']:.2f}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{row['Pct']:.1f}%", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(status, ParagraphStyle("C", fontSize=8, textColor=sc,
                      fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ])

    tbl = Table(data, colWidths=col_w)
    style = TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  NAVY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",          (0, 0), (-1, -1), 0.5, INDIGO),
        ("INNERGRID",    (0, 0), (-1, -1), 0.3, colors.HexColor("#c5cae9")),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
    ])
    tbl.setStyle(style)
    return tbl


# ── Andon Type table ──────────────────────────────────────────────────────────
def _andon_type_table(fdf, styles):
    tc = fdf["Andon Type"].value_counts().reset_index()
    tc.columns = ["Andon Type", "Count"]
    tc["% of Total"] = (tc["Count"] / tc["Count"].sum() * 100).round(1)
    tc["Avg Time"] = tc["Andon Type"].map(
        fdf.groupby("Andon Type")["Resolve_Min"].mean().round(2))

    headers = ["Andon Type", "Count", "% of Total", "Avg Time (min)", "Status"]
    col_w = [5 * cm, 2 * cm, 2.5 * cm, 3 * cm, 3 * cm]

    data = [[Paragraph(h, ParagraphStyle("H", fontSize=8, textColor=WHITE,
                fontName="Helvetica-Bold", alignment=TA_CENTER)) for h in headers]]

    for _, row in tc.iterrows():
        t = _get_threshold(row["Andon Type"])
        avg = row["Avg Time"]
        if t is None:
            status, sc = "No Target", GREY
        elif avg > t * 1.5:
            status, sc = "Above Target", RED
        elif avg > t:
            status, sc = "Borderline", ORANGE
        else:
            status, sc = "OK", GREEN

        data.append([
            Paragraph(str(row["Andon Type"]), ParagraphStyle("C", fontSize=8)),
            Paragraph(f"{int(row['Count']):,}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{row['% of Total']:.1f}%", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{avg:.2f}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(status, ParagraphStyle("C", fontSize=8, textColor=sc,
                      fontName="Helvetica-Bold", alignment=TA_CENTER)),
        ])

    tbl = Table(data, colWidths=col_w)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",           (0, 0), (-1, -1), 0.5, INDIGO),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#c5cae9")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


# ── Weekly summary table ──────────────────────────────────────────────────────
def _weekly_summary_table(fdf, styles):
    weeks = sorted(fdf["Week"].dropna().unique())
    headers = ["Week", "Total Andons", "Avg Time (min)", "Top Andon Type"]
    col_w = [2.5 * cm, 3 * cm, 3.5 * cm, 6.5 * cm]

    data = [[Paragraph(h, ParagraphStyle("H", fontSize=8, textColor=WHITE,
                fontName="Helvetica-Bold", alignment=TA_CENTER)) for h in headers]]

    for w in weeks:
        sub = fdf[fdf["Week"] == w]
        top_type = sub["Andon Type"].value_counts().index[0] if not sub.empty else "—"
        data.append([
            Paragraph(f"Week {int(w)}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{len(sub):,}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{sub['Resolve_Min'].mean():.2f}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(str(top_type), ParagraphStyle("C", fontSize=8)),
        ])

    tbl = Table(data, colWidths=col_w)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",           (0, 0), (-1, -1), 0.5, INDIGO),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#c5cae9")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


# ── Slowest resolvers highlight ───────────────────────────────────────────────
def _slow_resolvers_table(fdf, styles):
    slow = (fdf.groupby("Resolver")["Resolve_Min"]
            .agg(Count="count", Avg="mean").reset_index()
            .sort_values("Avg", ascending=False))
    slow["Avg"] = slow["Avg"].round(2)
    slow = slow[slow["Avg"] > DEFAULT_THRESHOLD]

    if slow.empty:
        return Paragraph("✅ All resolvers are within target thresholds.", styles["BodyText2"])

    headers = ["Resolver", "Total Andons", "Avg Time (min)", "Above Target By"]
    col_w = [4 * cm, 3 * cm, 3.5 * cm, 4 * cm]

    data = [[Paragraph(h, ParagraphStyle("H", fontSize=8, textColor=WHITE,
                fontName="Helvetica-Bold", alignment=TA_CENTER)) for h in headers]]

    for _, row in slow.iterrows():
        above = row["Avg"] - DEFAULT_THRESHOLD
        data.append([
            Paragraph(str(row["Resolver"]), ParagraphStyle("C", fontSize=8)),
            Paragraph(f"{int(row['Count']):,}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER)),
            Paragraph(f"{row['Avg']:.2f}", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER,
                      textColor=RED, fontName="Helvetica-Bold")),
            Paragraph(f"+{above:.2f} min", ParagraphStyle("C", fontSize=8, alignment=TA_CENTER,
                      textColor=ORANGE, fontName="Helvetica-Bold")),
        ])

    tbl = Table(data, colWidths=col_w)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.HexColor("#fff3e0"), colors.HexColor("#fff8e1")]),
        ("BOX",           (0, 0), (-1, -1), 0.5, ORANGE),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#ffe0b2")),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


# ── Cover page ────────────────────────────────────────────────────────────────
def _cover_page(story, styles, report_type, fdf, uploaded_files, generated_at):
    # Big colour block as title area
    story.append(Spacer(1, 2 * cm))

    title_data = [[
        Paragraph(f"LCY3 AFM Dashboard", styles["ReportTitle"]),
    ], [
        Paragraph(f"{report_type}", styles["ReportSubtitle"]),
    ]]
    title_tbl = Table(title_data, colWidths=[A4[0] - 3 * cm])
    title_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(title_tbl)
    story.append(Spacer(1, 1 * cm))

    # Date range info
    date_min = fdf["Date"].min()
    date_max = fdf["Date"].max()
    weeks    = sorted(fdf["Week"].dropna().unique().tolist())
    weeks_str = ", ".join([f"Wk {int(w)}" for w in weeks])

    info_data = [
        ["Report Generated", generated_at],
        ["Data Period", f"{date_min} → {date_max}"],
        ["Weeks Covered", weeks_str],
        ["Files Uploaded", str(len(uploaded_files))],
        ["Total Andons", f"{len(fdf):,}"],
        ["Prepared By", "Manish Karki — LCY3 AFM"],
    ]

    info_tbl = Table(info_data, colWidths=[4 * cm, 10 * cm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), LIGHT_BG),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR",     (1, 0), (1, -1), colors.HexColor("#333333")),
        ("BOX",           (0, 0), (-1, -1), 0.5, INDIGO),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#c5cae9")),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    story.append(info_tbl)
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=2, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "This report is auto-generated from Andon data uploaded to the LCY3 AFM Dashboard. "
        "All figures reflect resolved andons only, excluding 'Product Problem' and 'Out of Work' types.",
        styles["SmallGrey"]
    ))
    story.append(PageBreak())


# ── Public API ────────────────────────────────────────────────────────────────

def build_pdf_daily(fdf, uploaded_files, within_threshold_fn) -> bytes:
    buf = io.BytesIO()
    generated_at = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
    report_type  = "Daily Report"

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=2.2 * cm, bottomMargin=1.8 * cm
    )

    styles = _get_styles()
    story  = []

    # Cover
    _cover_page(story, styles, report_type, fdf, uploaded_files, generated_at)

    # ── Page 2: KPIs + Top Issue ──────────────────────────────────────────────
    story.append(Paragraph("Summary KPIs", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_kpi_table(fdf, within_threshold_fn, styles))
    story.append(Spacer(1, 0.6 * cm))

    # Top issue banner
    top_issue = fdf["Andon Type"].value_counts().index[0]
    top_count = fdf["Andon Type"].value_counts().iloc[0]
    top_pct   = top_count / len(fdf) * 100
    top_avg   = fdf[fdf["Andon Type"] == top_issue]["Resolve_Min"].mean()

    banner = Table([[
        Paragraph(
            f"Top Recurring Issue: {top_issue}  |  "
            f"{int(top_count):,} andons ({top_pct:.1f}%)  |  "
            f"Avg resolve time: {top_avg:.2f} min",
            ParagraphStyle("B", fontSize=9, textColor=WHITE,
                           fontName="Helvetica-Bold", alignment=TA_CENTER)
        )
    ]], colWidths=[A4[0] - 3 * cm])
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#e65100")),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(banner)
    story.append(Spacer(1, 0.6 * cm))

    # ── Leaderboard ───────────────────────────────────────────────────────────
    story.append(Paragraph("Resolver Leaderboard", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_leaderboard_table(fdf, within_threshold_fn, styles))
    story.append(Spacer(1, 0.6 * cm))

    # ── Flagged resolvers ─────────────────────────────────────────────────────
    story.append(Paragraph("Resolvers Above Threshold", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ORANGE))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_slow_resolvers_table(fdf, styles))
    story.append(PageBreak())

    # ── Page 3: Andon Types ───────────────────────────────────────────────────
    story.append(Paragraph("Andon Type Breakdown", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_andon_type_table(fdf, styles))
    story.append(Spacer(1, 0.8 * cm))

    # ── Weekly summary ────────────────────────────────────────────────────────
    story.append(Paragraph("Weekly Summary", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_weekly_summary_table(fdf, styles))

    doc.build(
        story,
        onFirstPage=lambda c, d: _header_footer(c, d, report_type, generated_at),
        onLaterPages=lambda c, d: _header_footer(c, d, report_type, generated_at),
    )
    buf.seek(0)
    return buf.getvalue()


def build_pdf_weekly(fdf, uploaded_files, within_threshold_fn) -> bytes:
    buf = io.BytesIO()
    generated_at = datetime.utcnow().strftime("%d %b %Y %H:%M UTC")
    report_type  = "Weekly Report"

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=2.2 * cm, bottomMargin=1.8 * cm
    )

    styles = _get_styles()
    story  = []

    # Cover
    _cover_page(story, styles, report_type, fdf, uploaded_files, generated_at)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    story.append(Paragraph("Weekly KPI Summary", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_kpi_table(fdf, within_threshold_fn, styles))
    story.append(Spacer(1, 0.6 * cm))

    # ── Week-by-week breakdown ────────────────────────────────────────────────
    story.append(Paragraph("Week-by-Week Breakdown", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_weekly_summary_table(fdf, styles))
    story.append(Spacer(1, 0.6 * cm))

    # ── System vs Non-System ──────────────────────────────────────────────────
    story.append(Paragraph("System vs Non-System Breakdown", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))

    fdf2 = fdf.copy()
    fdf2["_rtype"] = fdf2["Resolver"].apply(lambda r: "System" if r == "System" else "Non-System")
    sys_data = [
        ["Resolver Type", "Total Andons", "Avg Time (min)", "% of Total"],
    ]
    for rtype in ["System", "Non-System"]:
        sub = fdf2[fdf2["_rtype"] == rtype]
        pct = len(sub) / len(fdf2) * 100
        sys_data.append([
            rtype,
            f"{len(sub):,}",
            f"{sub['Resolve_Min'].mean():.2f}" if not sub.empty else "—",
            f"{pct:.1f}%",
        ])

    sys_tbl = Table(sys_data, colWidths=[4 * cm, 3.5 * cm, 3.5 * cm, 3.5 * cm])
    sys_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GREY]),
        ("BOX",           (0, 0), (-1, -1), 0.5, INDIGO),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#c5cae9")),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(sys_tbl)
    story.append(PageBreak())

    # ── Leaderboard ───────────────────────────────────────────────────────────
    story.append(Paragraph("Resolver Leaderboard", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_leaderboard_table(fdf, within_threshold_fn, styles))
    story.append(Spacer(1, 0.6 * cm))

    # ── Andon Types ───────────────────────────────────────────────────────────
    story.append(Paragraph("Andon Type Breakdown", styles["SectionHeader"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=INDIGO))
    story.append(Spacer(1, 0.3 * cm))
    story.append(_andon_type_table(fdf, styles))

    doc.build(
        story,
        onFirstPage=lambda c, d: _header_footer(c, d, report_type, generated_at),
        onLaterPages=lambda c, d: _header_footer(c, d, report_type, generated_at),
    )
    buf.seek(0)
    return buf.getvalue()
