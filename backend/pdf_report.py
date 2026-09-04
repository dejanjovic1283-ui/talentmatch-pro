from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
import math
import os
import re
from typing import Any, Iterable

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


BRAND_NAVY = colors.HexColor("#0F172A")
BRAND_TEXT = colors.HexColor("#1F2937")
BRAND_MUTED = colors.HexColor("#64748B")
BRAND_BLUE = colors.HexColor("#2563EB")
BRAND_GREEN = colors.HexColor("#16A34A")
BRAND_GREEN_LIGHT = colors.HexColor("#DCFCE7")
BRAND_RED = colors.HexColor("#DC2626")
BRAND_RED_LIGHT = colors.HexColor("#FEE2E2")
BRAND_YELLOW = colors.HexColor("#D97706")
BRAND_YELLOW_LIGHT = colors.HexColor("#FEF3C7")
BRAND_BORDER = colors.HexColor("#D1D5DB")
BRAND_SOFT = colors.HexColor("#F8FAFC")
BRAND_WHITE = colors.white

CONTENT_WIDTH = 17.8 * cm
MAX_LIST_ITEMS = 40
MAX_ITEM_CHARACTERS = 650
MAX_SUMMARY_CHARACTERS = 5000
MAX_JOB_DESCRIPTION_CHARACTERS = 6500

_UNICODE_REGULAR = os.getenv(
    "TALENTMATCH_PDF_UNICODE_REGULAR",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
)
_UNICODE_BOLD = os.getenv(
    "TALENTMATCH_PDF_UNICODE_BOLD",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
)
_ARABIC_REGULAR = os.getenv(
    "TALENTMATCH_PDF_ARABIC_REGULAR",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
)
_ARABIC_BOLD = os.getenv(
    "TALENTMATCH_PDF_ARABIC_BOLD",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
)
_CJK_REGULAR = os.getenv(
    "TALENTMATCH_PDF_CJK_REGULAR",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
)

_ARABIC_RE = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)
_CJK_RE = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF]")
_FONTS_READY = False


def _clean(value: Any, max_chars: int | None = None) -> str:
    text = str(value or "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if max_chars is not None and len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text


def _items(
    value: Any,
    *,
    max_items: int = MAX_LIST_ITEMS,
    max_item_chars: int = MAX_ITEM_CHARACTERS,
) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        source: Iterable[Any] = value
    elif isinstance(value, str):
        source = [value]
    else:
        source = [value]

    normalized: list[str] = []
    seen: set[str] = set()
    for item in source:
        if isinstance(item, (dict, list, tuple, set)):
            continue
        text = _clean(item, max_item_chars)
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
    if score is None or isinstance(score, bool):
        return 0
    try:
        numeric = float(score)
        if 0 < numeric <= 1:
            numeric *= 100
        if not math.isfinite(numeric):
            return 0
    except (TypeError, ValueError, OverflowError):
        return 0
    return max(0, min(100, int(round(numeric))))


def _score_color(score: int) -> tuple[Any, Any, str]:
    if score >= 75:
        return BRAND_GREEN, BRAND_GREEN_LIGHT, "Strong"
    if score >= 50:
        return BRAND_YELLOW, BRAND_YELLOW_LIGHT, "Competitive"
    return BRAND_RED, BRAND_RED_LIGHT, "Needs work"


def _register_fonts() -> None:
    global _FONTS_READY
    if _FONTS_READY:
        return

    required = {
        "Noto Sans Regular": _UNICODE_REGULAR,
        "Noto Sans Bold": _UNICODE_BOLD,
        "Noto Sans Arabic Regular": _ARABIC_REGULAR,
        "Noto Sans Arabic Bold": _ARABIC_BOLD,
        "Droid Sans Fallback Full": _CJK_REGULAR,
    }
    missing = [f"{label}: {path}" for label, path in required.items() if not os.path.isfile(path)]
    if missing:
        raise RuntimeError(
            "TalentMatch PDF fonts are missing from the runtime: " + "; ".join(missing)
        )

    pdfmetrics.registerFont(TTFont("TMUnicode", _UNICODE_REGULAR))
    pdfmetrics.registerFont(TTFont("TMUnicodeBold", _UNICODE_BOLD))
    pdfmetrics.registerFont(TTFont("TMArabic", _ARABIC_REGULAR))
    pdfmetrics.registerFont(TTFont("TMArabicBold", _ARABIC_BOLD))
    pdfmetrics.registerFont(TTFont("TMCJK", _CJK_REGULAR))
    pdfmetrics.registerFont(TTFont("TMCJKBold", _CJK_REGULAR))

    pdfmetrics.registerFontFamily(
        "TMUnicode",
        normal="TMUnicode",
        bold="TMUnicodeBold",
        italic="TMUnicode",
        boldItalic="TMUnicodeBold",
    )
    pdfmetrics.registerFontFamily(
        "TMArabic",
        normal="TMArabic",
        bold="TMArabicBold",
        italic="TMArabic",
        boldItalic="TMArabicBold",
    )
    pdfmetrics.registerFontFamily(
        "TMCJK",
        normal="TMCJK",
        bold="TMCJKBold",
        italic="TMCJK",
        boldItalic="TMCJKBold",
    )
    _FONTS_READY = True


def _script(text: str) -> str:
    if _ARABIC_RE.search(text):
        return "arabic"
    if _CJK_RE.search(text):
        return "cjk"
    return "unicode"


def _arabic_visual(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines() or [""]:
        if not line:
            lines.append("")
            continue

        visual = get_display(arabic_reshaper.reshape(line))
        if isinstance(visual, bytes):
            visual = visual.decode("utf-8", errors="replace")

        lines.append(visual)

    return "\n".join(lines)


def _display_text(value: Any, max_chars: int) -> tuple[str, str]:
    text = _clean(value, max_chars)
    script = _script(text)
    if script == "arabic":
        text = _arabic_visual(text)
    return escape(text).replace("\n", "<br/>"), script


def _styled(
    base: ParagraphStyle,
    script: str,
    *,
    bold: bool = False,
) -> ParagraphStyle:
    style = ParagraphStyle(f"{base.name}_{script}_{'b' if bold else 'r'}", parent=base)
    if script == "arabic":
        style.fontName = "TMArabicBold" if bold else "TMArabic"
        style.alignment = TA_RIGHT
    elif script == "cjk":
        style.fontName = "TMCJKBold" if bold else "TMCJK"
        style.wordWrap = "CJK"
    else:
        style.fontName = "TMUnicodeBold" if bold else "TMUnicode"
    return style


def _paragraph(
    value: Any,
    base_style: ParagraphStyle,
    *,
    max_chars: int,
    bold: bool = False,
) -> Paragraph:
    html, script = _display_text(value, max_chars)
    return Paragraph(html or " ", _styled(base_style, script, bold=bold))


def _styles(accent: colors.Color) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TMFinalAnalysisTitle", parent=base["Title"], fontName="TMUnicodeBold",
            fontSize=22, leading=25, textColor=BRAND_NAVY, alignment=TA_LEFT, spaceAfter=3,
        ),
        "subtitle": ParagraphStyle(
            "TMFinalAnalysisSubtitle", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=9.2, leading=12.2, textColor=BRAND_MUTED, spaceAfter=7,
        ),
        "section": ParagraphStyle(
            "TMFinalAnalysisSection", parent=base["Heading2"], fontName="TMUnicodeBold",
            fontSize=12.5, leading=15, textColor=BRAND_NAVY, keepWithNext=True,
            spaceBefore=7, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "TMFinalAnalysisBody", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=8.9, leading=11.7, textColor=BRAND_TEXT, spaceAfter=2.5,
        ),
        "small": ParagraphStyle(
            "TMFinalAnalysisSmall", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=7.7, leading=9.7, textColor=BRAND_MUTED,
        ),
        "metric_label": ParagraphStyle(
            "TMFinalAnalysisMetricLabel", parent=base["BodyText"], fontName="TMUnicodeBold",
            fontSize=7.2, leading=8.5, textColor=BRAND_MUTED, alignment=TA_CENTER,
        ),
        "metric_value": ParagraphStyle(
            "TMFinalAnalysisMetricValue", parent=base["BodyText"], fontName="TMUnicodeBold",
            fontSize=14, leading=16, textColor=BRAND_NAVY, alignment=TA_CENTER,
        ),
        "accent_value": ParagraphStyle(
            "TMFinalAnalysisAccentValue", parent=base["BodyText"], fontName="TMUnicodeBold",
            fontSize=14, leading=16, textColor=accent, alignment=TA_CENTER,
        ),
        "bullet": ParagraphStyle(
            "TMFinalAnalysisBullet", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=8.7, leading=11.4, leftIndent=10, firstLineIndent=-7,
            textColor=BRAND_TEXT, spaceAfter=1.8,
        ),
    }


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
    """Generate the unified compact multilingual TalentMatch Pro CV Analysis PDF."""
    _register_fonts()

    buffer = BytesIO()
    normalized_score = _clamp_score(score)
    normalized_strengths = _items(strengths)
    normalized_weaknesses = _items(weaknesses)
    normalized_recommendations = _items(recommendations)
    _, _, default_verdict = _score_color(normalized_score)
    verdict_text = _clean(verdict or default_verdict, 120)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    accent = BRAND_BLUE
    styles = _styles(accent)

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.6 * cm,
        rightMargin=1.6 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.6 * cm,
        title="TalentMatch Pro CV Analysis Report",
        author="TalentMatch Pro",
        subject="CV Analysis",
        allowSplitting=True,
    )

    def header_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        width, height = A4
        left, right = doc.leftMargin, width - doc.rightMargin
        canvas.setStrokeColor(BRAND_BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(left, height - 1.07 * cm, right, height - 1.07 * cm)
        canvas.setFillColor(accent)
        canvas.roundRect(left, height - 0.85 * cm, 0.22 * cm, 0.22 * cm, 0.05 * cm, fill=1, stroke=0)
        canvas.setFillColor(BRAND_NAVY)
        canvas.setFont("TMUnicodeBold", 8.6)
        canvas.drawString(left + 0.4 * cm, height - 0.78 * cm, "TalentMatch Pro")
        canvas.setFillColor(BRAND_MUTED)
        canvas.setFont("TMUnicode", 7.6)
        canvas.drawRightString(right, height - 0.78 * cm, "CV Analysis")
        canvas.setStrokeColor(BRAND_BORDER)
        canvas.line(left, 1.05 * cm, right, 1.05 * cm)
        canvas.setFillColor(BRAND_MUTED)
        canvas.setFont("TMUnicode", 7.4)
        canvas.drawString(left, 0.68 * cm, "Generated by TalentMatch Pro")
        canvas.drawRightString(right, 0.68 * cm, f"Page {document.page}")
        canvas.restoreState()

    def card(value: Any) -> Table:
        body = _paragraph(
            value or "No content available.",
            styles["body"],
            max_chars=MAX_SUMMARY_CHARACTERS,
        )
        table = Table([[body]], colWidths=[CONTENT_WIDTH], splitByRow=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BRAND_SOFT),
            ("BOX", (0, 0), (-1, -1), 0.5, BRAND_BORDER),
            ("LINEBEFORE", (0, 0), (0, -1), 2.5, accent),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return table

    story: list[Any] = [
        _paragraph("CV Analysis Report", styles["title"], max_chars=180, bold=True),
        _paragraph(
            "ATS alignment, strengths, gaps and practical next-step recommendations.",
            styles["subtitle"],
            max_chars=500,
        ),
    ]

    meta_cells = [
        _paragraph(f"Generated: {generated_at}", styles["small"], max_chars=120),
        _paragraph(f"CV file: {_clean(cv_filename, 180)}", styles["small"], max_chars=230),
        _paragraph("", styles["small"], max_chars=1),
        _paragraph("", styles["small"], max_chars=1),
    ]
    meta = Table([meta_cells], colWidths=[CONTENT_WIDTH / 4] * 4)
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_SOFT),
        ("BOX", (0, 0), (-1, -1), 0.45, BRAND_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, BRAND_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([meta, Spacer(1, 0.35 * cm)])

    metric_cells = [
        [
            _paragraph("OVERALL SCORE", styles["metric_label"], max_chars=60, bold=True),
            _paragraph(f"{normalized_score}/100", styles["accent_value"], max_chars=100, bold=True),
        ],
        [
            _paragraph("STATUS", styles["metric_label"], max_chars=60, bold=True),
            _paragraph(verdict_text, styles["metric_value"], max_chars=120, bold=True),
        ],
        [
            _paragraph("STRENGTHS", styles["metric_label"], max_chars=60, bold=True),
            _paragraph(str(len(normalized_strengths)), styles["metric_value"], max_chars=20, bold=True),
        ],
        [
            _paragraph("GAPS", styles["metric_label"], max_chars=60, bold=True),
            _paragraph(str(len(normalized_weaknesses)), styles["metric_value"], max_chars=20, bold=True),
        ],
    ]
    metrics = Table([metric_cells], colWidths=[CONTENT_WIDTH / 4] * 4)
    metrics.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_WHITE),
        ("BOX", (0, 0), (-1, -1), 0.55, BRAND_BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, BRAND_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([
        metrics,
        Spacer(1, 0.35 * cm),
        _paragraph("Executive Summary", styles["section"], max_chars=120, bold=True),
        card(summary),
        Spacer(1, 0.15 * cm),
    ])

    for title, values, fallback in (
        ("Strengths", normalized_strengths, "No strengths returned."),
        ("Weaknesses / Gaps", normalized_weaknesses, "No weaknesses returned."),
    ):
        story.append(_paragraph(title, styles["section"], max_chars=120, bold=True))
        for item in values or [fallback]:
            story.append(_paragraph("• " + item, styles["bullet"], max_chars=MAX_ITEM_CHARACTERS))
        story.append(Spacer(1, 0.15 * cm))

    story.append(_paragraph("Priority Recommendations", styles["section"], max_chars=120, bold=True))
    for index, item in enumerate(
        normalized_recommendations or ["No recommendations returned."],
        start=1,
    ):
        story.append(_paragraph(f"{index}. {item}", styles["bullet"], max_chars=MAX_ITEM_CHARACTERS))
    story.append(Spacer(1, 0.15 * cm))

    clean_job_description = _clean(job_description, MAX_JOB_DESCRIPTION_CHARACTERS)
    if clean_job_description:
        story.append(_paragraph("Job Description Appendix", styles["section"], max_chars=120, bold=True))
        story.append(_paragraph(clean_job_description, styles["body"], max_chars=MAX_JOB_DESCRIPTION_CHARACTERS))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    payload = buffer.getvalue()
    buffer.close()

    if not payload.startswith(b"%PDF"):
        raise RuntimeError("Generated CV Analysis report is not a valid PDF.")
    return payload
