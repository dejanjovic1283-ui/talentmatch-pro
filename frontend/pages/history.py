from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict
from urllib.parse import urlencode

import requests
import streamlit as st

from auth_utils import api_get, is_logged_in, is_pro_user
from components.sidebar import render_sidebar
from components.ui import (
    apply_global_styles,
    render_action_panel,
    render_empty_state,
    render_kpi_card,
    render_list_cards,
    render_page_intro,
    render_report_panel,
    render_score_card,
    render_section_title,
)


st.set_page_config(page_title="History • TalentMatch Pro", page_icon="📜", layout="wide")
apply_global_styles()
render_sidebar()

render_page_intro(
    kicker="REPORT INTELLIGENCE",
    title="History",
    subtitle=(
        "Search, compare, export, and manage every saved TalentMatch Pro report "
        "from one production-grade workspace."
    ),
    icon="📜",
    badge="PROFI-EXTRA",
)


BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")


TYPE_LABELS = {
    "cv_analysis": "CV Analysis",
    "cv_rewrite": "CV Rewrite",
    "ats_checker": "ATS Checker",
    "ats": "ATS Checker",
    "semantic_match": "Semantic",
    "recruiter_mode": "Recruiter",
}

FILTER_OPTIONS = {
    "All": None,
    "ATS Checker": "ats_checker",
    "Semantic": "semantic_match",
    "Recruiter": "recruiter_mode",
    "CV Analysis": "cv_analysis",
    "CV Rewrite": "cv_rewrite",
}

BADGE_STYLES = {
    "cv_analysis": ("CV Analysis", "#E8F0FE", "#174EA6"),
    "cv_rewrite": ("CV Rewrite", "#E0F7FA", "#006064"),
    "ats_checker": ("ATS Checker", "#E6F4EA", "#137333"),
    "ats": ("ATS Checker", "#E6F4EA", "#137333"),
    "semantic_match": ("Semantic", "#FEF7E0", "#B06000"),
    "recruiter_mode": ("Recruiter", "#F3E8FD", "#6A1B9A"),
}

PDF_TYPE_COLORS = {
    "cv_analysis": "#174EA6",
    "cv_rewrite": "#006064",
    "ats_checker": "#137333",
    "ats": "#137333",
    "semantic_match": "#B06000",
    "recruiter_mode": "#6A1B9A",
}


def clean_export_text(value: Any) -> str:
    """Normalize text for TXT/PDF exports and avoid unsupported dash characters."""
    text = str(value or "")

    replacements = {
        "\u00a0": " ",
        "\u00ad": "",
        "\u200b": "",
        "\u200c": "",
        "\u200d": "",
        "\u2060": "",
        "\ufeff": "",
        "\u2010": "-",
        "\u2011": "-",
        "\u2012": "-",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u2022": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
    }

    for old_value, new_value in replacements.items():
        text = text.replace(old_value, new_value)

    return " ".join(text.split()) if "\n" not in text else text


def safe_html(value: Any) -> str:
    text = clean_export_text(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def safe_list(value: Any) -> list[str]:
    if value is None:
        return []

    if isinstance(value, dict):
        for key in ("items", "values", "data", "results"):
            nested = value.get(key)
            normalized = safe_list(nested)
            if normalized:
                return normalized
        return []

    if isinstance(value, list):
        return [clean_export_text(item).strip() for item in value if clean_export_text(item).strip()]

    if isinstance(value, tuple):
        return [clean_export_text(item).strip() for item in value if clean_export_text(item).strip()]

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [clean_export_text(item).strip() for item in parsed if clean_export_text(item).strip()]
        except Exception:
            pass

        return [clean_export_text(item).strip() for item in raw.replace("\n", ",").split(",") if clean_export_text(item).strip()]

    text = clean_export_text(value).strip()
    return [text] if text else []


def normalize_type(item: dict[str, Any]) -> str:
    return str(item.get("analysis_type") or "cv_analysis").strip().lower()


def history_label(item: dict[str, Any]) -> str:
    analysis_type = normalize_type(item)
    return TYPE_LABELS.get(analysis_type, analysis_type.replace("_", " ").title())



def score_number(score: Any) -> int:
    """Normalize common score representations to a bounded 0-100 integer."""
    if score is None or isinstance(score, bool):
        return 0

    try:
        if isinstance(score, (int, float)):
            numeric = float(score)
        elif isinstance(score, str):
            match = re.search(r"-?\d+(?:[.,]\d+)?", score)
            if match is None:
                return 0
            numeric = float(match.group(0).replace(",", "."))
        else:
            return 0

        if 0 < numeric <= 1:
            numeric *= 100

        return max(0, min(100, int(round(numeric))))
    except (TypeError, ValueError, OverflowError):
        return 0


def _score_from_value(value: Any) -> int | None:
    if value is None or value == "":
        return None

    score = score_number(value)
    if score > 0:
        return score

    if isinstance(value, (int, float)) and not isinstance(value, bool) and float(value) == 0:
        return 0

    if isinstance(value, str) and value.strip() in {"0", "0.0", "0%", "0/100"}:
        return 0

    return None


def _score_priority(analysis_type: str) -> tuple[str, ...]:
    if analysis_type == "semantic_match":
        return (
            "combined_score",
            "score",
            "match_score",
            "semantic_score",
            "keyword_score",
            "overall_score",
        )

    if analysis_type == "recruiter_mode":
        return (
            "score",
            "combined_score",
            "match_score",
            "semantic_score",
            "keyword_score",
            "overall_score",
            "ranking_score",
            "candidate_score",
        )

    if analysis_type in {"ats_checker", "ats"}:
        return (
            "score",
            "ats_score",
            "coverage",
            "match_score",
            "overall_score",
            "score_percentage",
        )

    return (
        "score",
        "match_score",
        "overall_score",
        "combined_score",
        "semantic_score",
        "ats_score",
        "recruiter_score",
        "ranking_score",
        "compatibility_score",
        "candidate_score",
        "final_score",
        "score_percent",
        "score_percentage",
        "match_percentage",
        "percentage",
        "fit_score",
        "role_fit_score",
        "best_score",
        "top_score",
        "average_score",
        "total_score",
    )


def get_report_score(item: dict[str, Any]) -> int:
    """Extract the most relevant score for each report type without hiding richer values."""
    analysis_type = normalize_type(item)
    zero_candidate: int | None = None

    for key in _score_priority(analysis_type):
        score = _score_from_value(item.get(key))
        if score is None:
            continue
        if score > 0:
            return score
        zero_candidate = 0

    nested_sources = (
        item.get("result"),
        item.get("results"),
        item.get("report"),
        item.get("analysis_result"),
        item.get("data"),
        item.get("payload"),
        item.get("details"),
    )

    def walk(value: Any) -> list[int]:
        found: list[int] = []

        if isinstance(value, dict):
            for key, inner_value in value.items():
                key_lower = str(key).lower()
                if any(token in key_lower for token in ("score", "percentage", "coverage", "match")):
                    score = _score_from_value(inner_value)
                    if score is not None:
                        found.append(score)

                if isinstance(inner_value, (dict, list, tuple)):
                    found.extend(walk(inner_value))

        elif isinstance(value, (list, tuple)):
            for inner_item in value:
                found.extend(walk(inner_item))

        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    found.extend(walk(json.loads(stripped)))
                except (json.JSONDecodeError, TypeError):
                    pass

        return [score for score in found if 0 <= score <= 100]

    nested_scores: list[int] = []
    for source_value in nested_sources:
        nested_scores.extend(walk(source_value))

    for candidate_key in (
        "candidates",
        "rankings",
        "ranking",
        "candidate_rankings",
        "top_candidates",
    ):
        nested_scores.extend(walk(item.get(candidate_key)))

    positive_scores = [score for score in nested_scores if score > 0]
    if positive_scores:
        return max(positive_scores)

    return zero_candidate or 0

def score_color(score: Any) -> str:
    numeric_score = score_number(score)
    if numeric_score >= 75:
        return "#137333"
    if numeric_score >= 50:
        return "#B06000"
    return "#B3261E"


def get_cv_filename(item: dict[str, Any]) -> str:
    return str(
        item.get("cv_filename")
        or item.get("cv_file")
        or item.get("filename")
        or item.get("file_name")
        or "CV"
    )


def get_created_at(item: dict[str, Any]) -> str:
    return str(item.get("created_at") or item.get("date") or "")



def first_nonempty_item_list(item: dict[str, Any], *keys: str) -> list[str]:
    """Resolve the first non-empty list from flat or nested report payloads."""
    sources: list[dict[str, Any]] = [item]
    for container_key in ("result", "results", "report", "analysis_result", "data", "payload", "details"):
        nested = item.get(container_key)
        if isinstance(nested, dict):
            sources.append(nested)

    for source in sources:
        for key in keys:
            normalized = safe_list(source.get(key))
            if normalized:
                return normalized
    return []


def report_section_data(item: dict[str, Any]) -> tuple[str, list[str], str, list[str]]:
    """Return report-type-aware labels and normalized positive/negative sections."""
    analysis_type = normalize_type(item)

    if analysis_type == "semantic_match":
        positive_label = "Matched Themes"
        negative_label = "Missing Themes"
        positive = first_nonempty_item_list(
            item, "matched_themes", "matched_skills", "strengths"
        )
        negative = first_nonempty_item_list(
            item, "missing_themes", "missing_skills", "weaknesses"
        )
    elif analysis_type in {"ats_checker", "ats"}:
        positive_label = "Matched Keywords"
        negative_label = "Missing Keywords"
        positive = first_nonempty_item_list(
            item, "matched_keywords", "matched_skills", "strengths"
        )
        negative = first_nonempty_item_list(
            item, "missing_keywords", "missing_skills", "weaknesses"
        )
    elif analysis_type == "recruiter_mode":
        positive_label = "Top Candidate Strengths"
        negative_label = "Top Candidate Gaps"
        positive = first_nonempty_item_list(item, "matched_skills", "strengths")
        negative = first_nonempty_item_list(item, "missing_skills", "weaknesses")
    else:
        positive_label = "Strengths"
        negative_label = "Weaknesses / Gaps"
        positive = first_nonempty_item_list(item, "strengths", "matched_skills")
        negative = first_nonempty_item_list(item, "weaknesses", "missing_skills")

    return positive_label, positive, negative_label, negative


def format_generated_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def format_created_at(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "-"

    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return clean_export_text(raw)


def render_badge(item: dict[str, Any]) -> None:
    analysis_type = normalize_type(item)
    label, background, color = BADGE_STYLES.get(
        analysis_type,
        (history_label(item), "#ECEFF1", "#263238"),
    )
    st.markdown(
        f"""
        <span style="
            display:inline-block;
            padding:0.25rem 0.7rem;
            border-radius:999px;
            background:{background};
            color:{color};
            font-weight:700;
            font-size:0.85rem;
            margin-bottom:0.5rem;
        ">{safe_html(label)}</span>
        """,
        unsafe_allow_html=True,
    )


def render_history_info_card(title: str, value: str, subtitle: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="min-height:132px">
            <div class="tm-kicker">{safe_html(icon)} {safe_html(title)}</div>
            <div style="font-size:2rem;font-weight:900;color:#0F172A;margin:.35rem 0">
                {safe_html(value)}
            </div>
            <div class="tm-muted">{safe_html(subtitle)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_export_panel() -> None:
    st.markdown(
        """
        <div class="tm-card" style="margin-top:1rem;margin-bottom:1rem">
            <div class="tm-card-title">📦 Report export center</div>
            <div class="tm-muted">
                Download filtered history as TXT or branded PDF. PDF exports include TalentMatch Pro footer,
                page numbers and professional report formatting.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_history_state() -> None:
    st.markdown(
        """
        <div class="tm-card" style="text-align:center;padding:2rem">
            <div style="font-size:2.4rem">📭</div>
            <div class="tm-card-title">No reports found</div>
            <div class="tm-muted">
                Run your first CV analysis, ATS check, semantic match or recruiter ranking to build your report history.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def parse_history_response(response: Any) -> tuple[list[dict[str, Any]] | None, str | None]:
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "")

    if status_code != 200:
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("error") or payload
            return None, f"Failed to load history: {status_code} - {detail}"
        except Exception:
            return None, f"Failed to load history: {status_code} - {text[:1000]}"

    if content_type and "application/json" not in content_type:
        return None, f"Backend returned non-JSON response: {text[:1000]}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    items: Any
    if isinstance(payload, list):
        items = payload
    elif isinstance(payload, dict):
        items = payload.get("items") or payload.get("history") or payload.get("data") or []
    else:
        return None, "Backend returned invalid history format."

    if not isinstance(items, list):
        return None, "Backend returned invalid history format."

    normalized_items = [item for item in items if isinstance(item, dict)]
    return normalized_items, None



def build_text_report(item: dict[str, Any], index: int | None = None) -> str:
    cv_filename = clean_export_text(get_cv_filename(item))
    score = get_report_score(item)
    summary = clean_export_text(item.get("summary") or item.get("analysis") or "")
    positive_label, positive_values, negative_label, negative_values = report_section_data(item)
    recommendations = first_nonempty_item_list(item, "recommendations")
    job_description = clean_export_text(
        item.get("job_description")
        or item.get("job")
        or item.get("description")
        or ""
    )

    report_title = f"TalentMatch Pro - {history_label(item)} Report"
    if index is not None:
        report_title = f"{index}. {report_title}"

    lines = [
        report_title,
        "=" * len(report_title),
        f"Generated: {format_generated_timestamp()}",
        f"CV file: {cv_filename}",
        f"Type: {history_label(item)}",
        f"Score: {score}/100",
        f"Saved: {format_created_at(get_created_at(item))}",
        "",
        "Summary",
        "-" * 24,
        summary or "No summary returned.",
        "",
        positive_label,
        "-" * 24,
    ]

    lines.extend([f"- {value}" for value in positive_values] or [f"- No {positive_label.lower()} saved."])
    lines.extend(["", negative_label, "-" * 24])
    lines.extend([f"- {value}" for value in negative_values] or [f"- No {negative_label.lower()} saved."])
    lines.extend(["", "Recommendations", "-" * 24])
    lines.extend([f"- {value}" for value in recommendations] or ["- No recommendations saved."])

    if job_description:
        lines.extend(
            [
                "",
                "Job Description Appendix",
                "-" * 24,
                job_description,
            ]
        )

    return "\n".join(lines)

def build_history_text_report(
    items: list[dict[str, Any]],
    title: str = "TalentMatch Pro - Complete History Report",
) -> str:
    lines = [
        title,
        "=" * len(title),
        f"Generated: {format_generated_timestamp()}",
        f"Total items: {len(items)}",
        "",
    ]

    if not items:
        lines.append("No history items available.")
        return "\n".join(lines)

    counts = calculate_counts(items)
    lines.extend(
        [
            "Summary",
            "-" * 20,
            f"ATS Checker: {counts['ats_checker']}",
            f"Semantic: {counts['semantic_match']}",
            f"Recruiter: {counts['recruiter_mode']}",
            f"CV Analysis: {counts['cv_analysis']}",
            f"CV Rewrite: {counts['cv_rewrite']}",
            "",
        ]
    )

    for idx, item in enumerate(items, start=1):
        lines.append(build_text_report(item, index=idx))
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def safe_report_filename(cv_filename: str, suffix: str = "talentmatch_report") -> str:
    safe_name = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in str(cv_filename).replace(".pdf", "")
    ).strip("_")

    if not safe_name:
        safe_name = "talentmatch_cv"

    return f"{safe_name}_{suffix}"


def build_pdf_report(items: list[dict[str, Any]], title: str = "TalentMatch Pro History Report") -> bytes | None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm, inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except Exception:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=52,
        bottomMargin=58,
        title=title,
        author="TalentMatch Pro",
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TalentMatchTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#111827"),
        spaceAfter=8,
    )
    subtitle_style = ParagraphStyle(
        "TalentMatchSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=18,
    )
    section_style = ParagraphStyle(
        "TalentMatchSection",
        parent=styles["Heading2"],
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#111827"),
        spaceBefore=12,
        spaceAfter=8,
    )
    label_style = ParagraphStyle(
        "TalentMatchLabel",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    normal_style = ParagraphStyle(
        "TalentMatchNormal",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1F2937"),
    )
    small_style = ParagraphStyle(
        "TalentMatchSmall",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#6B7280"),
    )
    bullet_style = ParagraphStyle(
        "TalentMatchBullet",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12,
        leftIndent=10,
        firstLineIndent=-6,
        textColor=colors.HexColor("#1F2937"),
    )

    def draw_header_footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        width, height = A4

        canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
        canvas.setLineWidth(0.4)
        canvas.line(1.6 * cm, height - 1.12 * cm, width - 1.6 * cm, height - 1.12 * cm)

        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.drawString(1.6 * cm, height - 0.82 * cm, "TalentMatch Pro")

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawRightString(width - 1.6 * cm, height - 0.82 * cm, "History PDF Report")

        footer_y = 0.72 * cm
        line_y = 1.08 * cm
        canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
        canvas.line(1.6 * cm, line_y, width - 1.6 * cm, line_y)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawString(1.6 * cm, footer_y, "Generated by TalentMatch Pro")
        canvas.drawRightString(width - 1.6 * cm, footer_y, f"Page {document.page}")
        canvas.restoreState()

    story: list[Any] = [
        Paragraph(safe_html(title), title_style),
        Paragraph(f"Generated: {format_generated_timestamp()}", subtitle_style),
    ]

    if not items:
        story.append(Paragraph("No history items available.", normal_style))
        doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    counts = calculate_counts(items)
    summary_data = [
        ["Total", str(counts["total"])],
        ["ATS", str(counts["ats_checker"])],
        ["Semantic", str(counts["semantic_match"])],
        ["Recruiter", str(counts["recruiter_mode"])],
        ["CV Analysis", str(counts["cv_analysis"])],
        ["CV Rewrite", str(counts["cv_rewrite"])],
    ]
    summary_table = Table(summary_data, colWidths=[2.0 * inch, 1.0 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8F0FE")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1F2937")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 14))

    for idx, item in enumerate(items, start=1):
        cv_file = clean_export_text(get_cv_filename(item))
        created_at = clean_export_text(get_created_at(item))
        score = get_report_score(item)
        analysis_type = normalize_type(item)
        label = history_label(item)
        label_color = PDF_TYPE_COLORS.get(analysis_type, "#263238")
        sc_color = score_color(score)

        summary = clean_export_text(item.get("summary") or item.get("analysis") or "")
        positive_label, strengths, negative_label, weaknesses = report_section_data(item)
        recommendations = first_nonempty_item_list(item, "recommendations")
        job_description = clean_export_text(item.get("job_description") or item.get("job") or item.get("description") or "")

        story.append(Paragraph(f"{idx}. {safe_html(cv_file)}", section_style))

        meta_table = Table(
            [
                [
                    Paragraph(safe_html(label), label_style),
                    Paragraph(f"<b>Score:</b> <font color='{sc_color}'>{score}/100</font>", normal_style),
                    Paragraph(f"<b>Saved:</b> {safe_html(format_created_at(created_at))}", small_style),
                ]
            ],
            colWidths=[1.35 * inch, 1.25 * inch, 3.6 * inch],
        )
        meta_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(label_color)),
                    ("BACKGROUND", (1, 0), (-1, 0), colors.HexColor("#F9FAFB")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D1D5DB")),
                    ("PADDING", (0, 0), (-1, -1), 7),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(meta_table)
        story.append(Spacer(1, 8))

        story.append(Paragraph("<b>Summary</b>", normal_style))
        story.append(Paragraph(safe_html(summary or "No summary returned."), normal_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph(f"<b>{safe_html(positive_label)}</b>", normal_style))
        for value in strengths or [f"No {positive_label.lower()} saved."]:
            story.append(Paragraph(f"• {safe_html(value)}", bullet_style))

        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>{safe_html(negative_label)}</b>", normal_style))
        for value in weaknesses or [f"No {negative_label.lower()} saved."]:
            story.append(Paragraph(f"• {safe_html(value)}", bullet_style))

        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Recommendations</b>", normal_style))
        for value in recommendations or ["No recommendations saved."]:
            story.append(Paragraph(f"• {safe_html(value)}", bullet_style))

        if job_description:
            clean_job = safe_html(clean_export_text(job_description))
            if len(clean_job) > 2500:
                clean_job = clean_job[:2500] + "..."
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Job Description Appendix</b>", normal_style))
            story.append(Paragraph(clean_job, small_style))

        story.append(Spacer(1, 14))

    doc.build(story, onFirstPage=draw_header_footer, onLaterPages=draw_header_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def history_endpoint(selected_type: str | None) -> str:
    if not selected_type:
        return "/history"
    return "/history?" + urlencode({"analysis_type": selected_type})


def get_auth_headers() -> Dict[str, str]:
    token = (
        st.session_state.get("access_token")
        or st.session_state.get("id_token")
        or st.session_state.get("firebase_id_token")
        or st.session_state.get("auth_token")
        or st.session_state.get("token")
    )
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_delete(path: str, timeout: int = 60) -> requests.Response:
    clean_path = path if path.startswith("/") else f"/{path}"
    return requests.delete(
        f"{BACKEND_URL}{clean_path}",
        headers=get_auth_headers(),
        timeout=timeout,
    )


def clear_history_cache() -> None:
    for key in list(st.session_state.keys()):
        if str(key).startswith("history_items::"):
            st.session_state.pop(key, None)
    st.session_state.pop("history_items", None)
    st.session_state.pop("history_filter", None)


def delete_history_record(record_id: int) -> tuple[bool, str]:
    try:
        response = api_delete(f"/history/{record_id}")
        if response.status_code in (200, 204):
            return True, "History item deleted."
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        return False, f"Delete failed: {response.status_code} - {detail}"
    except Exception as exc:
        return False, f"Delete failed: {exc}"


def delete_all_history_records() -> tuple[bool, str]:
    try:
        response = api_delete("/history")
        if response.status_code in (200, 204):
            return True, "All history items deleted."
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        return False, f"Delete all failed: {response.status_code} - {detail}"
    except Exception as exc:
        return False, f"Delete all failed: {exc}"


def calculate_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(items),
        "ats_checker": sum(1 for item in items if normalize_type(item) in {"ats_checker", "ats"}),
        "semantic_match": sum(1 for item in items if normalize_type(item) == "semantic_match"),
        "recruiter_mode": sum(1 for item in items if normalize_type(item) == "recruiter_mode"),
        "cv_analysis": sum(1 for item in items if normalize_type(item) == "cv_analysis"),
        "cv_rewrite": sum(1 for item in items if normalize_type(item) == "cv_rewrite"),
    }


def sort_created_at(item: dict[str, Any]) -> str:
    return get_created_at(item)


def sort_score(item: dict[str, Any]) -> int:
    return get_report_score(item)




def render_history_css() -> None:
    st.markdown(
        """
        <style>
        .tm-history-toolbar {
            border: 1px solid rgba(148, 163, 184, .22);
            border-radius: 28px;
            padding: 1.15rem 1.2rem .35rem 1.2rem;
            background:
                radial-gradient(circle at top right, rgba(37, 99, 235, .10), transparent 34%),
                rgba(255, 255, 255, .88);
            box-shadow: 0 20px 56px rgba(15, 23, 42, .07);
            margin: .75rem 0 1.1rem 0;
        }
        .tm-history-report {
            border: 1px solid rgba(148, 163, 184, .22);
            border-radius: 30px;
            padding: 1.35rem;
            background:
                radial-gradient(circle at 100% 0%, rgba(37, 99, 235, .10), transparent 31%),
                radial-gradient(circle at 0% 100%, rgba(16, 185, 129, .08), transparent 34%),
                rgba(255, 255, 255, .94);
            box-shadow: 0 24px 68px rgba(15, 23, 42, .08);
            margin-bottom: 1rem;
        }
        .tm-history-head {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: .85rem;
        }
        .tm-history-title {
            color: #0f172a;
            font-size: 1.08rem;
            line-height: 1.35;
            font-weight: 950;
            letter-spacing: -.02em;
            overflow-wrap: anywhere;
        }
        .tm-history-meta {
            color: #64748b;
            font-size: .82rem;
            font-weight: 700;
            margin-top: .25rem;
        }
        .tm-history-score {
            min-width: 88px;
            text-align: center;
            border-radius: 22px;
            padding: .72rem .8rem;
            border: 1px solid rgba(148, 163, 184, .20);
            background: rgba(248, 250, 252, .90);
        }
        .tm-history-score-value {
            font-size: 1.55rem;
            line-height: 1;
            font-weight: 950;
            letter-spacing: -.05em;
        }
        .tm-history-score-label {
            color: #64748b;
            font-size: .7rem;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin-top: .3rem;
        }
        .tm-history-summary {
            border: 1px solid rgba(148, 163, 184, .18);
            border-radius: 20px;
            padding: .9rem 1rem;
            background: rgba(248, 250, 252, .78);
            color: #334155;
            line-height: 1.68;
            margin: .7rem 0 1rem 0;
        }
        .tm-history-pill {
            display: inline-flex;
            align-items: center;
            gap: .35rem;
            padding: .34rem .7rem;
            border-radius: 999px;
            font-size: .73rem;
            font-weight: 950;
            letter-spacing: .045em;
            text-transform: uppercase;
            border: 1px solid rgba(148, 163, 184, .20);
        }
        .tm-history-distribution {
            border: 1px solid rgba(148, 163, 184, .20);
            border-radius: 26px;
            padding: 1rem 1.1rem;
            background: rgba(255, 255, 255, .88);
            box-shadow: 0 18px 52px rgba(15, 23, 42, .06);
            min-height: 100%;
        }
        .tm-history-distribution-title {
            color: #0f172a;
            font-weight: 950;
            margin-bottom: .75rem;
        }
        .tm-history-bar-row { margin: .68rem 0; }
        .tm-history-bar-label {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            color: #475569;
            font-size: .78rem;
            font-weight: 850;
            margin-bottom: .3rem;
        }
        .tm-history-bar-track {
            height: 9px;
            border-radius: 999px;
            background: #e2e8f0;
            overflow: hidden;
        }
        .tm-history-bar-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #2563eb, #10b981);
        }
        .tm-history-danger {
            border: 1px solid rgba(239, 68, 68, .24);
            border-radius: 26px;
            padding: 1rem 1.1rem;
            background: rgba(254, 242, 242, .78);
            margin-top: 1rem;
        }
        @media (max-width: 800px) {
            .tm-history-head { flex-direction: column; }
            .tm-history-score { width: 100%; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def calculate_score_analytics(items: list[dict[str, Any]]) -> dict[str, int]:
    scores = [get_report_score(item) for item in items]
    scored = [score for score in scores if score > 0]
    if not scored:
        return {"average": 0, "highest": 0, "lowest": 0, "strong": 0}
    return {
        "average": round(sum(scored) / len(scored)),
        "highest": max(scored),
        "lowest": min(scored),
        "strong": sum(1 for score in scored if score >= 75),
    }


def render_distribution(counts: dict[str, int]) -> None:
    total = max(1, counts["total"])
    rows = (
        ("ATS Checker", counts["ats_checker"]),
        ("Semantic Match", counts["semantic_match"]),
        ("Recruiter Mode", counts["recruiter_mode"]),
        ("CV Analysis", counts["cv_analysis"]),
        ("CV Rewrite", counts["cv_rewrite"]),
    )
    html_rows = []
    for label, value in rows:
        percent = round((value / total) * 100)
        html_rows.append(
            f"""
            <div class="tm-history-bar-row">
                <div class="tm-history-bar-label"><span>{safe_html(label)}</span><span>{value} · {percent}%</span></div>
                <div class="tm-history-bar-track"><div class="tm-history-bar-fill" style="width:{percent}%"></div></div>
            </div>
            """
        )
    st.markdown(
        '<div class="tm-history-distribution">'
        '<div class="tm-history-distribution-title">Report distribution</div>'
        + "".join(html_rows)
        + "</div>",
        unsafe_allow_html=True,
    )


def render_score_distribution(items: list[dict[str, Any]]) -> None:
    scores = [get_report_score(item) for item in items if get_report_score(item) >= 0]
    buckets = {
        "Strong (75–100)": sum(1 for score in scores if score >= 75),
        "Competitive (50–74)": sum(1 for score in scores if 50 <= score < 75),
        "Needs work (0–49)": sum(1 for score in scores if score < 50),
    }
    total = max(1, len(scores))
    rows = []
    for label, value in buckets.items():
        percent = round((value / total) * 100)
        rows.append(
            f"""
            <div class="tm-history-bar-row">
                <div class="tm-history-bar-label"><span>{safe_html(label)}</span><span>{value} · {percent}%</span></div>
                <div class="tm-history-bar-track"><div class="tm-history-bar-fill" style="width:{percent}%"></div></div>
            </div>
            """
        )
    st.markdown(
        '<div class="tm-history-distribution">'
        '<div class="tm-history-distribution-title">Score distribution</div>'
        + "".join(rows)
        + "</div>",
        unsafe_allow_html=True,
    )


def report_badge_html(item: dict[str, Any]) -> str:
    analysis_type = normalize_type(item)
    label, background, color = BADGE_STYLES.get(
        analysis_type,
        (history_label(item), "#ECEFF1", "#263238"),
    )
    return (
        f'<span class="tm-history-pill" style="background:{background};color:{color}">'
        f'{safe_html(label)}</span>'
    )


def report_identity(item: dict[str, Any], index: int) -> str:
    record_id = item.get("id")
    if record_id is not None:
        return f"{record_id}"
    return f"{index}-{get_cv_filename(item)}-{get_created_at(item)}"


render_history_css()

if not is_logged_in():
    render_empty_state(
        title="Sign in to open History",
        message="Your saved reports are private and available only after authentication.",
        icon="🔐",
    )
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

render_action_panel(
    title="Report intelligence workspace",
    description=(
        "Filter every saved analysis, compare score trends, export professional records, "
        "and safely manage report retention from one place."
    ),
    icon="📚",
    eyebrow="HISTORY COMMAND CENTER",
)

st.markdown('<div class="tm-history-toolbar">', unsafe_allow_html=True)
filter_col, search_col, sort_col, refresh_col = st.columns([1.25, 2.1, 1.3, .75])

with filter_col:
    selected_label = st.selectbox(
        "Report type",
        list(FILTER_OPTIONS.keys()),
        key="history_type_filter",
    )

with search_col:
    search_query = st.text_input(
        "Search reports",
        placeholder="Filename, summary, report type, or job description...",
        key="history_search_query",
    )

with sort_col:
    sort_option = st.selectbox(
        "Sort",
        ["Newest first", "Oldest first", "Highest score", "Lowest score", "Filename A–Z"],
        key="history_sort_option",
    )

with refresh_col:
    st.write("")
    if st.button("🔄 Refresh", use_container_width=True, key="history_refresh"):
        clear_history_cache()
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)

selected_type = FILTER_OPTIONS[selected_label]
cache_key = f"history_items::{selected_type or 'all'}"

if cache_key not in st.session_state:
    with st.spinner("Loading secure report history..."):
        response = api_get(history_endpoint(selected_type), timeout=90)
        parsed_items, error = parse_history_response(response)
        if error:
            st.error(error)
            st.stop()
        st.session_state[cache_key] = parsed_items or []

items_raw = st.session_state.get(cache_key, [])
items: list[dict[str, Any]] = items_raw if isinstance(items_raw, list) else []
all_items_for_counts: list[dict[str, Any]] = items

if selected_type is not None:
    if "history_items::all" not in st.session_state:
        with st.spinner("Loading report analytics..."):
            response_all = api_get("/history", timeout=90)
            parsed_all, error_all = parse_history_response(response_all)
            all_items_for_counts = parsed_all if not error_all and isinstance(parsed_all, list) else items
            st.session_state["history_items::all"] = all_items_for_counts
    else:
        cached_all = st.session_state.get("history_items::all", [])
        all_items_for_counts = cached_all if isinstance(cached_all, list) else []

counts = calculate_counts(all_items_for_counts)
score_analytics = calculate_score_analytics(all_items_for_counts)

render_section_title(
    "Executive overview",
    "Live report inventory and score intelligence across the complete account history.",
)
metric_cols = st.columns(6)
with metric_cols[0]:
    render_kpi_card("Total reports", counts["total"], "📊", "Saved securely")
with metric_cols[1]:
    render_kpi_card("Average score", f'{score_analytics["average"]}/100', "📈", "Across scored reports")
with metric_cols[2]:
    render_kpi_card("Highest score", f'{score_analytics["highest"]}/100', "🏆", "Best recorded result")
with metric_cols[3]:
    render_kpi_card("Strong matches", score_analytics["strong"], "🔥", "Score 75 or higher")
with metric_cols[4]:
    render_kpi_card("Recruiter", counts["recruiter_mode"], "👥", "Ranking reports")
with metric_cols[5]:
    render_kpi_card("AI workflows", counts["semantic_match"] + counts["cv_rewrite"], "🧠", "Semantic + rewrite")

analytics_left, analytics_right = st.columns(2)
with analytics_left:
    render_distribution(counts)
with analytics_right:
    render_score_distribution(all_items_for_counts)

filtered_items = list(items)
query = search_query.strip().casefold()
if query:
    def searchable_text(item: dict[str, Any]) -> str:
        values = (
            get_cv_filename(item),
            history_label(item),
            item.get("summary"),
            item.get("analysis"),
            item.get("job_description"),
            item.get("job"),
        )
        return " ".join(clean_export_text(value) for value in values if value).casefold()
    filtered_items = [item for item in filtered_items if query in searchable_text(item)]

if sort_option == "Newest first":
    filtered_items.sort(key=sort_created_at, reverse=True)
elif sort_option == "Oldest first":
    filtered_items.sort(key=sort_created_at)
elif sort_option == "Highest score":
    filtered_items.sort(key=sort_score, reverse=True)
elif sort_option == "Lowest score":
    filtered_items.sort(key=sort_score)
else:
    filtered_items.sort(key=lambda item: get_cv_filename(item).casefold())

render_report_panel(
    title="History export center",
    description=(
        "Export the current filtered result set as portable TXT or a branded PDF. "
        "Individual reports remain available inside every report card."
    ),
    icon="📦",
)

history_title = (
    "TalentMatch Pro - Complete History Report"
    if selected_type is None
    else f"TalentMatch Pro - {selected_label} History Report"
)
history_txt = build_history_text_report(filtered_items, title=history_title)
history_pdf = build_pdf_report(filtered_items, title=history_title)

export_left, export_right, export_meta = st.columns([1, 1, 1.15])
with export_left:
    st.download_button(
        "⬇️ Export filtered history (.txt)",
        data=history_txt.encode("utf-8"),
        file_name="talentmatch_history.txt",
        mime="text/plain",
        use_container_width=True,
        disabled=not filtered_items,
    )
with export_right:
    if is_pro_user():
        st.download_button(
            "📄 Export filtered history (.pdf)",
            data=history_pdf or b"PDF export requires reportlab.",
            file_name="talentmatch_history_report.pdf",
            mime="application/pdf" if history_pdf else "text/plain",
            use_container_width=True,
            disabled=not filtered_items or history_pdf is None,
        )
    else:
        st.page_link("pages/pricing.py", label="🔒 Unlock PDF export with Pro")
with export_meta:
    st.info(f"Current view: {len(filtered_items)} of {len(items)} report(s).")

render_section_title(
    "Saved reports",
    "Open detailed evidence, download individual files, or remove records you no longer need.",
)

if not filtered_items:
    render_empty_state(
        title="No matching reports",
        message="Change the search text or report filter, or run a new TalentMatch analysis.",
        icon="📭",
    )
else:
    page_size = st.select_slider(
        "Reports per page",
        options=[5, 10, 20, 50],
        value=10,
        key="history_page_size",
    )
    total_pages = max(1, (len(filtered_items) + page_size - 1) // page_size)
    current_page = st.number_input(
        "Page",
        min_value=1,
        max_value=total_pages,
        value=min(int(st.session_state.get("history_current_page", 1)), total_pages),
        step=1,
        key="history_current_page",
    )
    start_index = (int(current_page) - 1) * page_size
    page_items = filtered_items[start_index : start_index + page_size]
    st.caption(
        f"Showing {start_index + 1}–{min(start_index + page_size, len(filtered_items))} "
        f"of {len(filtered_items)} report(s) · Page {current_page} of {total_pages}"
    )

    for position, item in enumerate(page_items, start=start_index + 1):
        score = get_report_score(item)
        numeric_score = score_number(score)
        cv_file = clean_export_text(get_cv_filename(item))
        created_at = format_created_at(get_created_at(item))
        positive_label, strengths, negative_label, gaps = report_section_data(item)
        recommendations = first_nonempty_item_list(item, "recommendations")
        summary = clean_export_text(item.get("summary") or item.get("analysis") or "")
        report_text = build_text_report(item)
        report_filename = safe_report_filename(cv_file)
        item_pdf_bytes = build_pdf_report([item], title=f"TalentMatch Pro - {history_label(item)} Report")
        identity = report_identity(item, position)

        st.markdown('<div class="tm-history-report">', unsafe_allow_html=True)
        score_hex = score_color(numeric_score)
        st.markdown(
            f"""
            <div class="tm-history-head">
                <div>
                    {report_badge_html(item)}
                    <div class="tm-history-title">{position}. {safe_html(cv_file)}</div>
                    <div class="tm-history-meta">Saved {safe_html(created_at)}</div>
                </div>
                <div class="tm-history-score">
                    <div class="tm-history-score-value" style="color:{score_hex}">{numeric_score}</div>
                    <div class="tm-history-score-label">out of 100</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if summary:
            st.markdown(
                f'<div class="tm-history-summary"><b>Executive summary</b><br>{safe_html(summary)}</div>',
                unsafe_allow_html=True,
            )

        evidence_left, evidence_right, evidence_action = st.columns([1, 1, 1])
        with evidence_left:
            render_list_cards(strengths, kind="success", empty_message=f"No {positive_label.lower()} saved.")
        with evidence_right:
            render_list_cards(gaps, kind="danger", empty_message=f"No {negative_label.lower()} saved.")
        with evidence_action:
            render_list_cards(recommendations, kind="info", empty_message="No recommendations saved.")

        with st.expander("📋 Full report controls", expanded=False):
            export_one, export_two = st.columns(2)
            with export_one:
                st.download_button(
                    "⬇️ Download TXT",
                    data=report_text.encode("utf-8"),
                    file_name=f"{report_filename}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key=f"history_txt_{identity}",
                )
            with export_two:
                if is_pro_user():
                    st.download_button(
                        "📄 Download PDF",
                        data=item_pdf_bytes or b"PDF export requires reportlab.",
                        file_name=f"{report_filename}.pdf",
                        mime="application/pdf" if item_pdf_bytes else "text/plain",
                        use_container_width=True,
                        disabled=item_pdf_bytes is None,
                        key=f"history_pdf_{identity}",
                    )
                else:
                    st.page_link("pages/pricing.py", label="🔒 Upgrade for PDF export")

            record_id = item.get("id")
            if record_id is None:
                st.info("This legacy report has no record ID and cannot be deleted individually.")
            else:
                confirm_delete = st.checkbox(
                    "I understand this permanently deletes the report.",
                    key=f"confirm_delete_{identity}",
                )
                if st.button(
                    "🗑 Delete this report",
                    type="secondary",
                    use_container_width=True,
                    disabled=not confirm_delete,
                    key=f"delete_history_{identity}",
                ):
                    ok, message = delete_history_record(int(record_id))
                    if ok:
                        st.success(message)
                        clear_history_cache()
                        st.rerun()
                    st.error(message)

        st.markdown("</div>", unsafe_allow_html=True)

render_section_title(
    "Data retention controls",
    "Permanent deletion is intentionally separated from normal report workflows.",
)
st.markdown('<div class="tm-history-danger">', unsafe_allow_html=True)
with st.expander("🗑 Delete all History records", expanded=False):
    st.warning("This permanently deletes every History record for your account and cannot be undone.")
    delete_all_confirm = st.text_input(
        "Type DELETE ALL to confirm",
        key="delete_all_history_confirm",
    )
    if st.button(
        "🗑 Permanently delete all History",
        type="secondary",
        use_container_width=True,
        disabled=delete_all_confirm.strip() != "DELETE ALL" or not all_items_for_counts,
        key="delete_all_history_button",
    ):
        ok, message = delete_all_history_records()
        if ok:
            st.success(message)
            clear_history_cache()
            st.rerun()
        st.error(message)
st.markdown("</div>", unsafe_allow_html=True)
