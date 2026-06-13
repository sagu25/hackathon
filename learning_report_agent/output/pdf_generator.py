"""PDF report generator — produces professional A4 PDFs from report dicts."""
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

BRAND_BLUE  = colors.HexColor("#0078D4")
BRAND_DARK  = colors.HexColor("#1a1a2e")
LIGHT_GREY  = colors.HexColor("#f5f5f5")
MID_GREY    = colors.HexColor("#cccccc")

PAGE_W = A4[0]


def _styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("BrandTitle",  fontName="Helvetica-Bold",  fontSize=20, textColor=BRAND_BLUE,  spaceAfter=4))
    s.add(ParagraphStyle("SectionHead", fontName="Helvetica-Bold",  fontSize=12, textColor=BRAND_BLUE,  spaceAfter=6, spaceBefore=12))
    s.add(ParagraphStyle("Body",        fontName="Helvetica",        fontSize=9,  textColor=BRAND_DARK,  spaceAfter=4))
    s.add(ParagraphStyle("Caption",     fontName="Helvetica-Oblique",fontSize=8,  textColor=colors.grey, spaceAfter=4))
    s.add(ParagraphStyle("MetricVal",   fontName="Helvetica-Bold",   fontSize=18, textColor=BRAND_BLUE,  spaceAfter=0, alignment=TA_CENTER))
    s.add(ParagraphStyle("MetricLbl",   fontName="Helvetica",        fontSize=8,  textColor=colors.grey, spaceAfter=0, alignment=TA_CENTER))
    s.add(ParagraphStyle("TblHdr",      fontName="Helvetica-Bold",   fontSize=8,  textColor=colors.white,alignment=TA_CENTER))
    s.add(ParagraphStyle("TblCell",     fontName="Helvetica",        fontSize=8,  textColor=BRAND_DARK))
    return s


def _on_page(canvas, doc):
    canvas.saveState()
    # Header bar
    canvas.setFillColor(BRAND_BLUE)
    canvas.rect(0, A4[1] - 1.15*cm, PAGE_W, 1.15*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(1.5*cm, A4[1] - 0.8*cm, "Learning Report Agent  |  Unified Analytics Platform")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - 1.5*cm, A4[1] - 0.8*cm, "LTM – HackToFuture 2026")
    # Footer bar
    canvas.setFillColor(LIGHT_GREY)
    canvas.rect(0, 0, PAGE_W, 0.9*cm, fill=1, stroke=0)
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(1.5*cm, 0.32*cm, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Confidential")
    canvas.drawRightString(PAGE_W - 1.5*cm, 0.32*cm, f"Page {doc.page}")
    canvas.restoreState()


def _metric_band(metrics: list[tuple], s) -> Table:
    """metrics = [(value, label), ...]"""
    n = len(metrics)
    col_w = (PAGE_W - 3*cm) / n
    top_row = [Paragraph(str(v), s["MetricVal"]) for v, _ in metrics]
    bot_row = [Paragraph(lbl,    s["MetricLbl"]) for _, lbl in metrics]
    t = Table([top_row, bot_row], colWidths=[col_w]*n, rowHeights=[1.1*cm, 0.45*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), LIGHT_GREY),
        ("BOX",        (0,0), (-1,-1), 0.5, MID_GREY),
        ("INNERGRID",  (0,0), (-1,-1), 0.3, MID_GREY),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return t


def _table(headers: list, rows: list, col_widths=None, s=None) -> Table:
    avail = PAGE_W - 3*cm
    if col_widths is None:
        col_widths = [avail / len(headers)] * len(headers)
    data = [[Paragraph(h, s["TblHdr"]) for h in headers]]
    for row in rows:
        data.append([Paragraph("—" if (v is None or v == "") else str(v), s["TblCell"]) for v in row])
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  BRAND_BLUE),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, LIGHT_GREY]),
        ("GRID",          (0,0), (-1,-1), 0.3, MID_GREY),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ]))
    return t


def generate_pdf(report: dict) -> bytes:
    """Convert a report dict to PDF. Returns raw bytes ready for download."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.8*cm, bottomMargin=1.5*cm,
    )
    s = _styles()
    story: list = []

    story.append(Spacer(1, 0.4*cm))
    story.append(Paragraph(report.get("title", "Learning Report"), s["BrandTitle"]))
    story.append(Paragraph(
        f"Generated: {str(report.get('generated_at', ''))[:19]}  "
        f"|  Report type: {report.get('report_type','').replace('_',' ').title()}",
        s["Caption"],
    ))
    story.append(HRFlowable(width="100%", thickness=2, color=BRAND_BLUE, spaceAfter=10))

    rtype = report.get("report_type")
    if   rtype == "compliance":    _compliance(story, report, s)
    elif rtype == "learning_kpis": _kpis(story, report, s)
    elif rtype == "skill_gap":     _skill_gap(story, report, s)
    else:
        import json
        story.append(Paragraph(json.dumps(report, default=str, indent=2)[:3000], s["Body"]))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()


# ── per-type builders ─────────────────────────────────────────────────────────

def _compliance(story, report, s):
    story.append(Paragraph("Executive Summary", s["SectionHead"]))
    story.append(_metric_band([
        (f"{report.get('avg_compliance_rate', 0)}%", "Avg Compliance Rate"),
        (len(report.get("at_risk_departments", [])),  "At-Risk Departments"),
        (report.get("total_at_risk", 0),              "Overdue Learners"),
    ], s))
    story.append(Spacer(1, 0.3*cm))

    summary = report.get("summary", [])
    if summary:
        story.append(Paragraph("Completion Rate by Department & Course", s["SectionHead"]))
        rows = [
            [r.get("department"), r.get("course_title"),
             f"{r.get('completion_rate', 0)}%", f"{r.get('avg_score') or 'N/A'}",
             r.get("total_enrolled"), r.get("completed")]
            for r in summary[:35]
        ]
        story.append(_table(
            ["Department", "Course", "Rate", "Avg Score", "Enrolled", "Completed"],
            rows,
            col_widths=[3*cm, 7.5*cm, 2*cm, 2.5*cm, 2*cm, 2*cm],
            s=s,
        ))
        story.append(Spacer(1, 0.3*cm))

    overdue = report.get("overdue_learners", [])
    if overdue:
        story.append(Paragraph(f"Overdue Learners  ({len(overdue)} records)", s["SectionHead"]))
        rows = [
            [r.get("name"), r.get("department", ""), r.get("role", ""),
             r.get("course_title"), r.get("status")]
            for r in overdue[:30]
        ]
        story.append(_table(
            ["Employee", "Department", "Role", "Course", "Status"],
            rows,
            col_widths=[3.5*cm, 2.5*cm, 3*cm, 7*cm, 2*cm],
            s=s,
        ))


def _kpis(story, report, s):
    story.append(Paragraph("Executive Summary", s["SectionHead"]))
    top = report.get("top_performing", {})
    story.append(_metric_band([
        (f"{report.get('org_avg_completion', 0)}%", "Org Avg Completion"),
        (f"{report.get('org_avg_hours', 0)}h",       "Avg Hours / Employee"),
        (top.get("department", "N/A"),                "Top Department"),
    ], s))
    story.append(Spacer(1, 0.3*cm))

    kpis = report.get("kpis", [])
    if kpis:
        story.append(Paragraph("Department Learning KPIs", s["SectionHead"]))
        rows = [
            [r.get("department"), r.get("headcount"),
             f"{r.get('completion_rate', 0)}%", f"{r.get('required_completion_rate', 0)}%",
             f"{r.get('avg_hours_per_employee', 0)}h",
             f"${r.get('budget_usd', 0):,.0f}", f"{r.get('budget_utilization', 0)}%"]
            for r in kpis
        ]
        story.append(_table(
            ["Department", "HC", "Completion", "Req'd %", "Avg Hrs", "Budget", "Utilised"],
            rows,
            col_widths=[3.5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm],
            s=s,
        ))


def _skill_gap(story, report, s):
    story.append(Paragraph("Overview", s["SectionHead"]))
    story.append(_metric_band([
        (report.get("total_skill_areas", 0),           "Skill Areas Analysed"),
        (len(report.get("overrated_skills", [])),       "Overrated Skills"),
        (len(report.get("underrated_skills", [])),      "Underrated Skills"),
    ], s))
    story.append(Spacer(1, 0.3*cm))

    gaps = report.get("gaps", [])
    if gaps:
        story.append(Paragraph("Skill Gap Detail  (Self Rating − Manager Rating)", s["SectionHead"]))
        rows = [
            [r.get("department"), r.get("skill"),
             f"{r.get('avg_self_rating', 0):.2f}",
             f"{r.get('avg_manager_rating'):.2f}" if r.get("avg_manager_rating") else "N/A",
             f"{r.get('gap', 0):.2f}", r.get("employee_count")]
            for r in gaps[:35]
        ]
        story.append(_table(
            ["Department", "Skill", "Self", "Manager", "Gap", "Employees"],
            rows,
            col_widths=[3.5*cm, 3.5*cm, 2*cm, 2.5*cm, 2*cm, 2.5*cm],
            s=s,
        ))

        over = report.get("overrated_skills", [])
        under = report.get("underrated_skills", [])
        if over:
            story.append(Paragraph("Top Overrated Skills  (self >> manager)", s["SectionHead"]))
            rows = [[r.get("department"), r.get("skill"), f"{r.get('gap', 0):.2f}"] for r in over]
            story.append(_table(["Department", "Skill", "Gap"], rows,
                                 col_widths=[5*cm, 5*cm, 3*cm], s=s))
        if under:
            story.append(Paragraph("Top Underrated Skills  (manager >> self)", s["SectionHead"]))
            rows = [[r.get("department"), r.get("skill"), f"{r.get('gap', 0):.2f}"] for r in under]
            story.append(_table(["Department", "Skill", "Gap"], rows,
                                 col_widths=[5*cm, 5*cm, 3*cm], s=s))
