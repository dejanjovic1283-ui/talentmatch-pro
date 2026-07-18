from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
import math
import re
from typing import Any, Iterable, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
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

CONTENT_WIDTH = 16.2 * cm
MAX_LIST_ITEMS = 40
MAX_ITEM_CHARACTERS = 650
MAX_SUMMARY_CHARACTERS = 5000
MAX_JOB_DESCRIPTION_CHARACTERS = 6500


def _strip_control_characters(value: str) -> str:
    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", value)


def _safe_text(
    value: Any,
    *,
    max_chars: int | None = None,
) -> str:
    """Convert a value into bounded, ReportLab-safe paragraph text."""
    if value is None:
        return ""

    text = _strip_control_characters(str(value))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if max_chars is not None and len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _as_list(
    value: Any,
    *,
    max_items: int = MAX_LIST_ITEMS,
    max_item_chars: int = MAX_ITEM_CHARACTERS,
) -> list[str]:
    """Normalize arbitrary input into a clean, bounded, deduplicated list."""
    if value is None:
        return []

    raw_items: Iterable[Any]
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    elif isinstance(value, str):
        raw_items = [value]
    else:
        raw_items = [value]

    normalized: list[str] = []
    seen: set[str] = set()

    for item in raw_items:
        if isinstance(item, (dict, list, tuple, set)):
            continue

        text = _safe_text(item, max_chars=max_item_chars)
        if not text:
            continue

        key = text.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(text)

        if len(normalized) >= max_items:
            break

    return normalized


def _clamp_score(score: Any) -> int:
    """Normalize score-like input to an integer from 0 to 100."""
    if score is None or isinstance(score, bool):
        return 0

    try:
        numeric_score = float(score)
        if 0 < numeric_score <= 1:
            numeric_score *= 100
        if not math.isfinite(numeric_score):
            return 0
    except (TypeError, ValueError, OverflowError):
        return 0

    return max(0, min(100, int(round(numeric_score))))


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
            fontSize=26,
            leading=31,
            textColor=BRAND_NAVY,
            alignment=TA_LEFT,
            spaceAfter=5,
        ),
        "cover_subtitle": ParagraphStyle(
            "TMCoverSubtitle",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=BRAND_MUTED,
            alignment=TA_LEFT,
            spaceAfter=10,
        ),
        "section": ParagraphStyle(
            "TMSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=BRAND_NAVY,
            keepWithNext=True,
            spaceBefore=10,
            spaceAfter=6,
        ),
        "subsection": ParagraphStyle(
            "TMSubsection",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=BRAND_NAVY,
            keepWithNext=True,
            spaceBefore=0,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "TMBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13.5,
            textColor=BRAND_TEXT,
            spaceAfter=4,
        ),
        "body_center": ParagraphStyle(
            "TMBodyCenter",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=BRAND_TEXT,
            alignment=TA_CENTER,
            spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "TMSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=10.5,
            textColor=BRAND_MUTED,
        ),
        "tiny": ParagraphStyle(
            "TMTiny",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9.5,
            textColor=BRAND_MUTED,
        ),
        "metric_label": ParagraphStyle(
            "TMMetricLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=BRAND_MUTED,
        ),
        "metric_value": ParagraphStyle(
            "TMMetricValue",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=BRAND_NAVY,
        ),
        "score_value": ParagraphStyle(
            "TMScoreValue",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=25,
            textColor=BRAND_NAVY,
            alignment=TA_CENTER,
            allowWidows=0,
            allowOrphans=0,
        ),
        "score_label": ParagraphStyle(
            "TMScoreLabel",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=10,
            textColor=BRAND_MUTED,
            alignment=TA_CENTER,
        ),
        "bullet": ParagraphStyle(
            "TMBullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13,
            leftIndent=13,
            firstLineIndent=-8,
            bulletIndent=0,
            textColor=BRAND_TEXT,
            spaceAfter=3,
        ),
        "numbered": ParagraphStyle(
            "TMNumbered",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.4,
            leading=13,
            leftIndent=16,
            firstLineIndent=-13,
            textColor=BRAND_TEXT,
            spaceAfter=5,
        ),
        "card_label_green": ParagraphStyle(
            "TMCardLabelGreen",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=BRAND_GREEN,
            keepWithNext=True,
            spaceAfter=4,
        ),
        "card_label_yellow": ParagraphStyle(
            "TMCardLabelYellow",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=BRAND_YELLOW,
            keepWithNext=True,
            spaceAfter=4,
        ),
    }


def _header_footer(canvas, doc) -> None:
    """Draw the branded header and footer on every page."""
    canvas.saveState()

    width, height = A4

    canvas.setStrokeColor(BRAND_BORDER)
    canvas.setLineWidth(0.45)
    canvas.line(
        1.6 * cm,
        height - 1.15 * cm,
        width - 1.6 * cm,
        height - 1.15 * cm,
    )

    canvas.setFillColor(BRAND_BLUE)
    canvas.roundRect(
        1.6 * cm,
        height - 0.98 * cm,
        0.22 * cm,
        0.22 * cm,
        0.05 * cm,
        fill=1,
        stroke=0,
    )

    canvas.setFont("Helvetica-Bold", 9)
    canvas.setFillColor(BRAND_NAVY)
    canvas.drawString(
        1.95 * cm,
        height - 0.9 * cm,
        "TalentMatch Pro",
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawRightString(
        width - 1.6 * cm,
        height - 0.9 * cm,
        "AI-powered CV Analysis",
    )

    canvas.setStrokeColor(BRAND_BORDER)
    canvas.setLineWidth(0.45)
    canvas.line(
        1.6 * cm,
        1.08 * cm,
        width - 1.6 * cm,
        1.08 * cm,
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(BRAND_MUTED)
    canvas.drawString(
        1.6 * cm,
        0.72 * cm,
        "Generated by TalentMatch Pro",
    )
    canvas.drawRightString(
        width - 1.6 * cm,
        0.72 * cm,
        f"Page {doc.page}",
    )

    canvas.restoreState()


def _bullet_list(
    items: Any,
    style: ParagraphStyle,
) -> list[Paragraph]:
    normalized = _as_list(items)

    if not normalized:
        return [Paragraph("- No items available.", style)]

    return [
        Paragraph(f"- {item}", style)
        for item in normalized
    ]


def _numbered_list(
    items: Any,
    style: ParagraphStyle,
) -> list[Paragraph]:
    normalized = _as_list(items)

    if not normalized:
        return [Paragraph("1. No recommendations available.", style)]

    return [
        Paragraph(f"{index}. {item}", style)
        for index, item in enumerate(normalized, start=1)
    ]


def _summary_card(
    summary: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    table = Table(
        [[
            Paragraph(
                _safe_text(
                    summary,
                    max_chars=MAX_SUMMARY_CHARACTERS,
                ) or "No summary available.",
                styles["body"],
            )
        ]],
        colWidths=[CONTENT_WIDTH],
        splitByRow=1,
        repeatRows=0,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_SOFT),
                ("BOX", (0, 0), (-1, -1), 0.7, BRAND_BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3.0, BRAND_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
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
    verdict_text = _safe_text(verdict or default_verdict, max_chars=120)

    data = [
        [
            Paragraph("Score", styles["score_label"]),
            Paragraph("Verdict", styles["metric_label"]),
            Paragraph("CV File", styles["metric_label"]),
            Paragraph("Generated", styles["metric_label"]),
        ],
        [
            Paragraph(
                f"<nobr>{score}/100</nobr>",
                styles["score_value"],
            ),
            Paragraph(verdict_text, styles["metric_value"]),
            Paragraph(
                _safe_text(cv_filename, max_chars=180) or "Uploaded CV",
                styles["body"],
            ),
            Paragraph(
                _safe_text(generated_at, max_chars=80),
                styles["body"],
            ),
        ],
    ]

    table = Table(
        data,
        colWidths=[
            4.25 * cm,
            3.75 * cm,
            4.85 * cm,
            3.35 * cm,
        ],
        splitByRow=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), score_bg),
                ("BACKGROUND", (1, 0), (-1, -1), BRAND_WHITE),
                ("BOX", (0, 0), (-1, -1), 0.8, BRAND_BORDER),
                ("LINEBEFORE", (1, 0), (1, -1), 1.2, score_color),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, BRAND_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _insight_card(
    *,
    title: str,
    items: Any,
    background: Any,
    accent: Any,
    title_style: ParagraphStyle,
    bullet_style: ParagraphStyle,
) -> Table:
    normalized_items = _as_list(items)

    rows: list[list[Any]] = [[Paragraph(title, title_style)]]

    if normalized_items:
        rows.extend(
            [[Paragraph(f"- {item}", bullet_style)]]
            for item in normalized_items
        )
    else:
        rows.append(
            [Paragraph("- No items available.", bullet_style)]
        )

    table = Table(
        rows,
        colWidths=[CONTENT_WIDTH],
        splitByRow=1,
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.6, BRAND_BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 3.0, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _recommendation_card(
    index: int,
    recommendation: str,
    styles: dict[str, ParagraphStyle],
) -> Table:
    index_cell = Paragraph(
        str(index),
        ParagraphStyle(
            f"TMRecommendationIndex{index}",
            parent=styles["body_center"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=BRAND_BLUE,
            alignment=TA_CENTER,
        ),
    )
    recommendation_cell = Paragraph(
        _safe_text(
            recommendation,
            max_chars=MAX_ITEM_CHARACTERS,
        ),
        styles["body"],
    )

    table = Table(
        [[index_cell, recommendation_cell]],
        colWidths=[1.1 * cm, 15.1 * cm],
        splitByRow=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), BRAND_BLUE_LIGHT),
                ("BACKGROUND", (1, 0), (1, 0), BRAND_WHITE),
                ("BOX", (0, 0), (-1, -1), 0.55, BRAND_BORDER),
                ("LINEBEFORE", (1, 0), (1, 0), 0.7, BRAND_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def _job_description_block(
    job_description: str,
    styles: dict[str, ParagraphStyle],
) -> list[Any]:
    clean_job = _safe_text(
        job_description,
        max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
    )

    return [
        Paragraph("Job Description Appendix", styles["section"]),
        Paragraph(
            "The appendix preserves the source job description used for this analysis.",
            styles["small"],
        ),
        Spacer(1, 5),
        Table(
            [[
                Paragraph(
                    clean_job or "No job description provided.",
                    styles["body"],
                )
            ]],
            colWidths=[CONTENT_WIDTH],
            splitByRow=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
                    ("BOX", (0, 0), (-1, -1), 0.6, BRAND_BORDER),
                    ("LEFTPADDING", (0, 0), (-1, -1), 11),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
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
    """Generate a branded, page-safe TalentMatch Pro CV Analysis PDF."""
    buffer = BytesIO()

    normalized_score = _clamp_score(score)
    normalized_strengths = _as_list(strengths)
    normalized_weaknesses = _as_list(weaknesses)
    normalized_recommendations = _as_list(recommendations)

    styles = _build_styles()
    _, _, default_verdict = _score_color(normalized_score)
    generated_at = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )
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
        subject="AI-powered CV analysis report",
        allowSplitting=True,
    )

    story: list[Any] = [
        Paragraph("TalentMatch Pro", styles["cover_title"]),
        Paragraph(
            "Professional AI-powered CV analysis report for ATS matching, "
            "skill gaps, recruiter fit and practical next steps.",
            styles["cover_subtitle"],
        ),
        HRFlowable(
            width="100%",
            thickness=1.0,
            color=BRAND_BLUE,
        ),
        Spacer(1, 8),
        _cover_band(
            cv_filename=cv_filename,
            score=normalized_score,
            verdict=verdict_text,
            generated_at=generated_at,
            styles=styles,
        ),
        Spacer(1, 8),
        Paragraph("Executive Summary", styles["section"]),
        _summary_card(summary, styles),
        Spacer(1, 5),
        Paragraph("CV Coverage", styles["section"]),
        _insight_card(
            title="Strengths",
            items=normalized_strengths,
            background=colors.HexColor("#F0FDF4"),
            accent=BRAND_GREEN,
            title_style=styles["card_label_green"],
            bullet_style=styles["bullet"],
        ),
        Spacer(1, 6),
        _insight_card(
            title="Weaknesses / Gaps",
            items=normalized_weaknesses,
            background=colors.HexColor("#FFFBEB"),
            accent=BRAND_YELLOW,
            title_style=styles["card_label_yellow"],
            bullet_style=styles["bullet"],
        ),
        Spacer(1, 5),
        Paragraph(
            "Priority Recommendations",
            styles["section"],
        ),
    ]

    if normalized_recommendations:
        for index, recommendation in enumerate(
            normalized_recommendations,
            start=1,
        ):
            story.append(
                _recommendation_card(
                    index,
                    recommendation,
                    styles,
                )
            )
            story.append(Spacer(1, 4))
    else:
        story.extend(
            _numbered_list(
                [],
                styles["numbered"],
            )
        )

    story.extend(
        [
            Spacer(1, 4),
            HRFlowable(
                width="100%",
                thickness=0.6,
                color=BRAND_BORDER,
            ),
            Spacer(1, 4),
            Paragraph(
                "This report is generated automatically by TalentMatch Pro "
                "and should be reviewed before making final hiring or "
                "application decisions.",
                styles["tiny"],
            ),
        ]
    )

    if _safe_text(job_description):
        story.append(PageBreak())
        story.extend(
            _job_description_block(
                job_description,
                styles,
            )
        )

    doc.build(
        story,
        onFirstPage=_header_footer,
        onLaterPages=_header_footer,
    )

    pdf_bytes = buffer.getvalue()
    buffer.close()

    if not pdf_bytes.startswith(b"%PDF"):
        raise RuntimeError("Generated CV Analysis report is not a valid PDF.")

    return pdf_bytes
