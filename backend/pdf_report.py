from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BRAND_NAVY = colors.HexColor("#0F172A")
BRAND_DARK = colors.HexColor("#111827")
BRAND_TEXT = colors.HexColor("#1F2937")
BRAND_MUTED = colors.HexColor("#64748B")
BRAND_BLUE = colors.HexColor("#2563EB")
BRAND_BLUE_LIGHT = colors.HexColor("#DBEAFE")
BRAND_GREEN = colors.HexColor("#16A34A")
BRAND_GREEN_LIGHT = colors.HexColor("#DCFCE7")
BRAND_RED = colors.HexColor("#DC2626")
BRAND_RED_LIGHT = colors.HexColor("#FEE2E2")
BRAND_YELLOW = colors.HexColor("#D97706")
BRAND_YELLOW_LIGHT = colors.HexColor("#FEF3C7")
BRAND_BORDER = colors.HexColor("#D1D5DB")
BRAND_SOFT = colors.HexColor("#F8FAFC")
BRAND_WHITE = colors.white


def _safe_text(value: Any) -> str:
    """Convert any value into safe printable ReportLab text."""
    if value is None:
        return ""

    text = str(value).strip()
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _as_list(value: Any) -> list[str]:
    """Normalize any value into a clean list of strings."""
    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [_safe_text(item) for item in value if str(item).strip()]

    text = str(value).strip()
    return [_safe_text(text)] if text else []


def _clamp_score(score: Any) -> int:
    try:
        numeric_score = int(float(score or 0))
    except Exception:
        numeric_score = 0
    return max(0, min(100, numeric_score))


def _score_color(score: int) -> tuple[Any, Any, str]:
    if score >= 75:
        return BRAND_GREEN, BRAND_GREEN_LIGHT, "Strong Match"
    if score >= 50:
        return BRAND_YELLOW, BRAND_YELLOW_LIGHT, "Moderate Match"
    return BRAND_RED, BRAND_RED_LIGHT, "Needs Improvement"


def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()

    return {
        "cover_title": ParagraphStyle(
            "TMCoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=BRAND_NAVY,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "cover_subtitle": ParagraphStyle(
            "TMCoverSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=BRAND_MUTED,
            alignment=TA_LEFT,
            spaceAfter=16,
        ),
        "section": ParagraphStyle(
            "TMSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=20,
            textColor=BRAND_NAVY,
            spaceBefore=16,
            spaceAfter=8,
        ),
        "body": ParagraphStyle(
            "TMBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=BRAND_TEXT,
            spaceAfter=6,
        ),
        "body_center": ParagraphStyle(
            "TMBodyCenter",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=BRAND_TEXT,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "TMSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=BRAND_MUTED,
        ),
        "tiny": ParagraphStyle(
            "TMTiny",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=BRAND_MUTED,
        ),
        "metric_label": ParagraphStyle(
            "TMMetricLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=BRAND_MUTED,
        ),
        "metric_value": ParagraphStyle(
            "TMMetricValue",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=BRAND_NAVY,
        ),
        "score_value": ParagraphStyle(
            "TMScoreValue",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=26,
            leading=30,
            textColor=BRAND_NAVY,
            alignment=TA_CENTER,
        ),
        "score_label": ParagraphStyle(
            "TMScoreLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=BRAND_MUTED,
            alignment=TA_CENTER,
        ),
        "bullet": ParagraphStyle(
            "TMBullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            leftIndent=13,
            firstLineIndent=-8,
            textColor=BRAND_TEXT,
            spaceAfter=4,
        ),
    }


def _header_footer(canvas, doc) -> None:
    """Draw professional header and footer on every PDF page."""
    canvas.saveState()

    width, height = A4

    # Header
    canvas.setStrokeColor(BRAND_BORDER)
    canvas.setLineWidth(0.45)
    canvas.line(1.6 * cm, height - 1.15 * cm, width - 1.6 * cm, height - 1.15 * cm)

    canvas.setFillColor(BRAND_BLUE)
    canvas.roundRect(1.6 * cm, height - 0.98 * cm, 0.22 * cm, 0.22 * cm, 0.05 * cm, fill=1, stroke=0)

    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(BRAND_NAVY)
    canvas.drawString(1.95 * cm, height - 0.9 * cm, "TalentMatch Pro")

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawRightString(width - 1.6 * cm, height - 0.9 * cm, "AI-powered CV Analysis")

    # Footer
    canvas.setStrokeColor(BRAND_BORDER)
    canvas.setLineWidth(0.45)
    canvas.line(1.6 * cm, 1.08 * cm, width - 1.6 * cm, 1.08 * cm)

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawString(1.6 * cm, 0.72 * cm, "Generated by TalentMatch Pro")
    canvas.drawRightString(width - 1.6 * cm, 0.72 * cm, f"Page {doc.page}")

    canvas.restoreState()


def _bullet_list(items: Any, style: ParagraphStyle) -> list[Paragraph]:
    normalized = _as_list(items)

    if not normalized:
        return [Paragraph("• No items available.", style)]

    return [Paragraph(f"• {item}", style) for item in normalized]


def _section_block(title: str, items: Any, style: ParagraphStyle) -> KeepTogether:
    styles = _build_styles()
    return KeepTogether(
        [
            Paragraph(_safe_text(title), styles["section"]),
            *_bullet_list(items, style),
        ]
    )


def _summary_card(summary: str, styles: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[Paragraph(_safe_text(summary) or "No summary available.", styles["body"])]],
        colWidths=[16.2 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _cover_band(
    *,
    cv_filename: str,
    score: int,
    verdict: str,
    generated_at: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    score_color, score_bg, default_verdict = _score_color(score)
    verdict_text = _safe_text(verdict or default_verdict)

    data = [
        [
            Paragraph("Score", styles["score_label"]),
            Paragraph("Verdict", styles["metric_label"]),
            Paragraph("CV File", styles["metric_label"]),
            Paragraph("Generated", styles["metric_label"]),
        ],
        [
            Paragraph(f"{score}/100", styles["score_value"]),
            Paragraph(verdict_text, styles["metric_value"]),
            Paragraph(_safe_text(cv_filename) or "Uploaded CV", styles["body"]),
            Paragraph(_safe_text(generated_at), styles["body"]),
        ],
    ]

    table = Table(data, colWidths=[3.3 * cm, 4.0 * cm, 5.0 * cm, 3.9 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), score_bg),
                ("BACKGROUND", (1, 0), (-1, -1), BRAND_WHITE),
                ("BOX", (0, 0), (-1, -1), 0.8, BRAND_BORDER),
                ("LINEBEFORE", (1, 0), (1, -1), 1.0, score_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, BRAND_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _insight_table(
    *,
    strengths: Any,
    weaknesses: Any,
    recommendations: Any,
    styles: dict[str, ParagraphStyle],
) -> Table:
    strengths_items = _as_list(strengths)
    weakness_items = _as_list(weaknesses)
    rec_items = _as_list(recommendations)

    def cell(title: str, icon: str, items: list[str]) -> list[Any]:
        content: list[Any] = [
            Paragraph(f"<b>{icon} {title}</b>", styles["body"]),
            Spacer(1, 4),
        ]
        if items:
            content.extend(Paragraph(f"• {item}", styles["bullet"]) for item in items[:8])
        else:
            content.append(Paragraph("• No items available.", styles["bullet"]))
        return content

    table = Table(
        [
            [
                cell("Strengths", "✅", strengths_items),
                cell("Gaps", "⚠️", weakness_items),
                cell("Next steps", "💡", rec_items),
            ]
        ],
        colWidths=[5.2 * cm, 5.2 * cm, 5.2 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F0FDF4")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFFBEB")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 0.6, BRAND_BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, BRAND_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _job_description_block(job_description: str, styles: dict[str, ParagraphStyle]) -> list[Any]:
    clean_job = _safe_text(job_description)

    if len(clean_job) > 4500:
        clean_job = clean_job[:4500] + "..."

    return [
        Paragraph("Job Description", styles["section"]),
        Table(
            [[Paragraph(clean_job or "No job description provided.", styles["body"])]],
            colWidths=[16.2 * cm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                    ("BOX", (0, 0), (-1, -1), 0.6, BRAND_BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 11),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                    ("TOPPADDING", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            ),
        ),
    ]


def build_analysis_pdf_report(
    *,
    cv_filename: str,
    score: int,
    summary: str,
    strengths: list[str],
    weaknesses: list[str],
    recommendations: list[str],
    job_description: str,
    verdict: str | None = None,
) -> bytes:
    """Generate a polished branded TalentMatch Pro PDF analysis report."""
    buffer = BytesIO()

    score = _clamp_score(score)
    styles = _build_styles()
    _, _, default_verdict = _score_color(score)
    generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    verdict_text = verdict or default_verdict

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.75 * cm,
        bottomMargin=1.55 * cm,
        title="TalentMatch Pro CV Analysis Report",
        author="TalentMatch Pro",
    )

    story: list[Any] = []

    story.append(Paragraph("TalentMatch Pro", styles["cover_title"]))
    story.append(
        Paragraph(
            "Professional AI-powered CV analysis report for ATS matching, skill gaps, recruiter fit and practical next steps.",
            styles["cover_subtitle"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1.0, color=BRAND_BLUE))
    story.append(Spacer(1, 14))

    story.append(
        _cover_band(
            cv_filename=cv_filename,
            score=score,
            verdict=verdict_text,
            generated_at=generated_at,
            styles=styles,
        )
    )
    story.append(Spacer(1, 14))

    story.append(Paragraph("Executive Summary", styles["section"]))
    story.append(_summary_card(summary, styles))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Key Insights", styles["section"]))
    story.append(
        _insight_table(
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            styles=styles,
        )
    )

    story.append(Spacer(1, 10))
    story.append(Paragraph("Detailed Recommendations", styles["section"]))
    story.extend(_bullet_list(recommendations, styles["bullet"]))

    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=0.6, color=BRAND_BORDER))
    story.append(
        Paragraph(
            "This report is generated automatically by TalentMatch Pro and should be reviewed before making final hiring or application decisions.",
            styles["tiny"],
        )
    )

    if job_description:
        story.append(PageBreak())
        story.extend(_job_description_block(job_description, styles))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
