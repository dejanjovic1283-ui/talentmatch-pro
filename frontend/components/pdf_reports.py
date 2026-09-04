from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
import os
import re
from typing import Any, Iterable, Mapping, Sequence

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


NAVY = colors.HexColor("#0F172A")
TEXT = colors.HexColor("#1F2937")
MUTED = colors.HexColor("#64748B")
BORDER = colors.HexColor("#D7DEE8")
SOFT = colors.HexColor("#F8FAFC")
WHITE = colors.white
CONTENT_WIDTH = 178 * mm

MODULE_ACCENTS = {
    "cv_analysis": "#2563EB",
    "ats_checker": "#F59E0B",
    "semantic_match": "#7C3AED",
    "cv_rewrite": "#0F766E",
    "recruiter_mode": "#059669",
    "history": "#4F46E5",
}

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


def _clean(value: Any, max_chars: int = 6500) -> str:
    text = str(value or "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        text = text[: max_chars - 3].rstrip() + "..."
    return text


def _items(values: Any, max_items: int = 50, max_chars: int = 650) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        source: Iterable[Any] = [values]
    elif isinstance(values, (list, tuple, set)):
        source = values
    else:
        source = [values]

    out: list[str] = []
    seen: set[str] = set()
    for item in source:
        if isinstance(item, (dict, list, tuple, set)):
            continue
        text = _clean(item, max_chars=max_chars)
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max_items:
            break
    return out


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


def _display_text(value: Any, max_chars: int = 6500) -> tuple[str, str]:
    text = _clean(value, max_chars=max_chars)
    script = _script(text)
    if script == "arabic":
        text = _arabic_visual(text)
    return escape(text).replace("\n", "<br/>"), script


def _styled(base: ParagraphStyle, script: str, *, bold: bool = False) -> ParagraphStyle:
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
    max_chars: int = 6500,
    bold: bool = False,
) -> Paragraph:
    html, script = _display_text(value, max_chars=max_chars)
    return Paragraph(html or " ", _styled(base_style, script, bold=bold))


def _styles(accent: colors.Color) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TMFinalTitle", parent=base["Title"], fontName="TMUnicodeBold",
            fontSize=22, leading=25, textColor=NAVY, alignment=TA_LEFT, spaceAfter=3,
        ),
        "subtitle": ParagraphStyle(
            "TMFinalSubtitle", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=9.2, leading=12.2, textColor=MUTED, spaceAfter=7,
        ),
        "section": ParagraphStyle(
            "TMFinalSection", parent=base["Heading2"], fontName="TMUnicodeBold",
            fontSize=12.5, leading=15, textColor=NAVY, keepWithNext=True,
            spaceBefore=7, spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "TMFinalBody", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=8.9, leading=11.7, textColor=TEXT, spaceAfter=2.5,
        ),
        "small": ParagraphStyle(
            "TMFinalSmall", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=7.7, leading=9.7, textColor=MUTED,
        ),
        "metric_label": ParagraphStyle(
            "TMFinalMetricLabel", parent=base["BodyText"], fontName="TMUnicodeBold",
            fontSize=7.2, leading=8.5, textColor=MUTED, alignment=TA_CENTER,
        ),
        "metric_value": ParagraphStyle(
            "TMFinalMetricValue", parent=base["BodyText"], fontName="TMUnicodeBold",
            fontSize=14, leading=16, textColor=NAVY, alignment=TA_CENTER,
        ),
        "accent_value": ParagraphStyle(
            "TMFinalAccentValue", parent=base["BodyText"], fontName="TMUnicodeBold",
            fontSize=14, leading=16, textColor=accent, alignment=TA_CENTER,
        ),
        "bullet": ParagraphStyle(
            "TMFinalBullet", parent=base["BodyText"], fontName="TMUnicode",
            fontSize=8.7, leading=11.4, leftIndent=10, firstLineIndent=-7,
            textColor=TEXT, spaceAfter=1.8,
        ),
    }


def build_branded_pdf_report(
    *,
    title: str,
    report_label: str,
    accent_hex: str,
    subtitle: str = "",
    metadata: Sequence[tuple[str, Any]] = (),
    metrics: Sequence[tuple[str, Any]] = (),
    sections: Sequence[Mapping[str, Any]] = (),
    filename_hint: str = "",
) -> bytes:
    _register_fonts()

    accent = colors.HexColor(accent_hex)
    styles = _styles(accent)
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=17 * mm,
        bottomMargin=16 * mm,
        title=_clean(title, 180),
        author="TalentMatch Pro",
        subject=_clean(report_label, 120),
        allowSplitting=True,
    )

    def header_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        width, height = A4
        left, right = doc.leftMargin, width - doc.rightMargin
        canvas.setStrokeColor(BORDER)
        canvas.setLineWidth(0.4)
        canvas.line(left, height - 10.7 * mm, right, height - 10.7 * mm)
        canvas.setFillColor(accent)
        canvas.roundRect(left, height - 8.5 * mm, 2.2 * mm, 2.2 * mm, 0.5 * mm, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont("TMUnicodeBold", 8.6)
        canvas.drawString(left + 4 * mm, height - 7.8 * mm, "TalentMatch Pro")
        canvas.setFillColor(MUTED)
        canvas.setFont("TMUnicode", 7.6)
        canvas.drawRightString(right, height - 7.8 * mm, _clean(report_label, 70))
        canvas.setStrokeColor(BORDER)
        canvas.line(left, 10.5 * mm, right, 10.5 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("TMUnicode", 7.4)
        canvas.drawString(left, 6.8 * mm, "Generated by TalentMatch Pro")
        canvas.drawRightString(right, 6.8 * mm, f"Page {document.page}")
        canvas.restoreState()

    story: list[Any] = [
        _paragraph(title, styles["title"], max_chars=180, bold=True),
        _paragraph(subtitle or report_label, styles["subtitle"], max_chars=500),
    ]

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    meta = [("Generated", generated), *metadata]
    if filename_hint:
        meta.append(("CV file", filename_hint))

    if meta:
        cells: list[Any] = []
        for label, value in meta[:4]:
            cells.append(_paragraph(f"{_clean(label, 40)}: {_clean(value, 180)}", styles["small"], max_chars=230))
        while len(cells) < 4:
            cells.append(_paragraph("", styles["small"], max_chars=1))
        table = Table([cells], colWidths=[CONTENT_WIDTH / 4] * 4)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), SOFT),
            ("BOX", (0, 0), (-1, -1), 0.45, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.extend([table, Spacer(1, 3.5 * mm)])

    if metrics:
        metric_cells: list[list[Any]] = []
        for index, (label, value) in enumerate(metrics[:4]):
            value_style = styles["accent_value"] if index == 0 else styles["metric_value"]
            metric_cells.append([
                _paragraph(_clean(label, 60).upper(), styles["metric_label"], max_chars=60, bold=True),
                _paragraph(value, value_style, max_chars=100, bold=True),
            ])
        cols = len(metric_cells)
        table = Table([metric_cells], colWidths=[CONTENT_WIDTH / max(cols, 1)] * max(cols, 1))
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), WHITE),
            ("BOX", (0, 0), (-1, -1), 0.55, BORDER),
            ("INNERGRID", (0, 0), (-1, -1), 0.35, BORDER),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.extend([table, Spacer(1, 3.5 * mm)])

    for section in sections:
        heading = _clean(section.get("title"), 120)
        if not heading:
            continue
        story.append(_paragraph(heading, styles["section"], max_chars=120, bold=True))
        kind = str(section.get("kind") or "text")
        value = section.get("content")

        if kind in {"bullets", "numbered"}:
            values = _items(value)
            fallback = _clean(section.get("fallback") or "No items available.", 180)
            values = values or [fallback]
            for index, item in enumerate(values, start=1):
                prefix = f"{index}. " if kind == "numbered" else "• "
                story.append(_paragraph(prefix + item, styles["bullet"], max_chars=650))
        elif kind == "card":
            body = _paragraph(value or section.get("fallback") or "No content available.", styles["body"], max_chars=5000)
            card = Table([[body]], colWidths=[CONTENT_WIDTH], splitByRow=1)
            card.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]))
            story.append(card)
        else:
            story.append(_paragraph(value or section.get("fallback") or "No content available.", styles["body"], max_chars=6500))
        story.append(Spacer(1, 1.5 * mm))

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    payload = buffer.getvalue()
    buffer.close()
    if not payload.startswith(b"%PDF"):
        raise ValueError("Generated PDF payload is invalid.")
    return payload
