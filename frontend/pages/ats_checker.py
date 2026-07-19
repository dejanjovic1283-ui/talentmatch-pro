from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
import logging
import math
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import streamlit as st

from auth_utils import api_post, is_logged_in
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


LOGGER = logging.getLogger(__name__)

MAX_JOB_DESCRIPTION_CHARACTERS = 15_000
MAX_SUMMARY_CHARACTERS = 4_000
MAX_LIST_ITEMS = 50
MAX_LIST_ITEM_CHARACTERS = 500
PDF_JOB_DESCRIPTION_CHARACTERS = 6_500

EXAMPLE_JOB_DESCRIPTION = """Founding Full-Stack AI SaaS Engineer

What we are looking for:
- Python
- FastAPI
- PostgreSQL
- Docker
- Firebase
- PayPal
- Render deployment
- Product mindset
- API integrations
- AI-powered workflows
""".strip()


st.set_page_config(
    page_title="ATS Checker • TalentMatch Pro",
    page_icon="📋",
    layout="wide",
)
apply_global_styles()
render_sidebar()


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def clean_text(
    value: Any,
    *,
    max_chars: int = MAX_SUMMARY_CHARACTERS,
) -> str:
    text = str(value or "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"

    return text


def normalize_response(
    raw: Any,
) -> Tuple[Optional[Any], Optional[str]]:
    if isinstance(raw, tuple):
        if len(raw) >= 2:
            return raw[0], raw[1]
        if len(raw) == 1:
            return raw[0], None
        return None, "Empty response from backend."

    return raw, None


def response_to_json(
    response: Any,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if response is None:
        return None, "No response from backend."

    if isinstance(response, dict):
        return response, None

    status_code = getattr(response, "status_code", None)
    response_text = clean_text(
        getattr(response, "text", "") or "",
        max_chars=800,
    )
    headers = getattr(response, "headers", {}) or {}
    content_type = str(headers.get("content-type", "")).lower()

    if status_code is not None and status_code >= 400:
        detail = "Request failed."

        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = clean_text(
                    payload.get("detail")
                    or payload.get("error")
                    or payload.get("message")
                    or detail,
                    max_chars=500,
                )
        except (TypeError, ValueError):
            if response_text:
                detail = response_text

        if status_code == 401:
            return None, "Your session expired. Please log in again."
        if status_code == 403:
            return None, "ATS Checker is blocked by backend permissions."
        if status_code == 429:
            return None, "Too many requests. Please wait and try again."

        return None, f"ATS check failed ({status_code}): {detail}"

    if content_type and "application/json" not in content_type:
        return None, "Backend returned an unexpected response format."

    try:
        payload = response.json()
    except (TypeError, ValueError):
        return None, "Backend returned invalid JSON."

    if not isinstance(payload, dict):
        return None, "Backend response is not a JSON object."

    error_value = payload.get("error") or payload.get("detail")
    if error_value:
        return None, clean_text(error_value, max_chars=500)

    return payload, None


def normalize_list(
    value: Any,
    *,
    max_items: int = MAX_LIST_ITEMS,
    max_item_chars: int = MAX_LIST_ITEM_CHARACTERS,
) -> List[str]:
    if value is None:
        return []

    raw_items: Iterable[Any]
    if isinstance(value, (list, tuple, set)):
        raw_items = value
    elif isinstance(value, str):
        raw_items = re.split(r"[\n,;]+", value)
    else:
        raw_items = [value]

    result: List[str] = []
    seen: set[str] = set()

    for item in raw_items:
        if isinstance(item, (dict, list, tuple, set)):
            continue

        normalized = clean_text(item, max_chars=max_item_chars)
        if not normalized:
            continue

        key = normalized.casefold()
        if key in seen:
            continue

        seen.add(key)
        result.append(normalized)

        if len(result) >= max_items:
            break

    return result


def extract_list(
    data: Dict[str, Any],
    *keys: str,
) -> List[str]:
    for key in keys:
        if key not in data:
            continue

        normalized = normalize_list(data.get(key))
        if normalized:
            return normalized

    return []


def score_number(value: Any) -> Optional[int]:
    if value is None or isinstance(value, bool):
        return None

    try:
        if isinstance(value, (int, float)):
            numeric = float(value)
        elif isinstance(value, str):
            match = re.search(r"-?\d+(?:[.,]\d+)?", value)
            if match is None:
                return None
            numeric = float(match.group(0).replace(",", "."))
        else:
            return None

        if not math.isfinite(numeric):
            return None

        if 0 < numeric <= 1:
            numeric *= 100

        return max(0, min(100, int(round(numeric))))
    except (TypeError, ValueError, OverflowError):
        return None


def get_ats_score(data: Dict[str, Any]) -> int:
    for key in (
        "score",
        "match_score",
        "ats_score",
        "overall_score",
        "compatibility_score",
    ):
        score = score_number(data.get(key))
        if score is not None:
            return score

    return 0


def score_level(score: Any) -> Tuple[str, str, int]:
    numeric_score = score_number(score)
    if numeric_score is None:
        return "Not scored", "No numeric score returned", 0

    if numeric_score >= 85:
        return (
            "Excellent",
            "Strong ATS alignment for this job description",
            numeric_score,
        )
    if numeric_score >= 70:
        return (
            "Good",
            "Solid match with a limited number of keyword gaps",
            numeric_score,
        )
    if numeric_score >= 50:
        return (
            "Needs polish",
            "Improve missing keywords and role alignment",
            numeric_score,
        )

    return (
        "Weak match",
        "Rewrite important CV sections before applying",
        numeric_score,
    )


def score_tone(score: int) -> Tuple[str, str]:
    if score >= 85:
        return "#059669", "High confidence"
    if score >= 70:
        return "#2563EB", "Competitive"
    if score >= 50:
        return "#D97706", "Needs optimization"
    return "#DC2626", "Low alignment"


def extract_report_data(data: Dict[str, Any]) -> Dict[str, Any]:
    score = get_ats_score(data)
    label, message, _ = score_level(score)

    return {
        "score": score,
        "label": label,
        "message": message,
        "summary": clean_text(
            data.get("summary")
            or data.get("analysis")
            or data.get("executive_summary")
            or "",
            max_chars=MAX_SUMMARY_CHARACTERS,
        ),
        "matched_keywords": extract_list(
            data,
            "matched_keywords",
            "matched",
            "found_keywords",
            "strengths",
        ),
        "missing_keywords": extract_list(
            data,
            "missing_keywords",
            "missing",
            "missing_skills",
            "gaps",
        ),
        "recommendations": extract_list(
            data,
            "recommendations",
            "tips",
            "suggestions",
        ),
    }


def build_text_report(
    data: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> str:
    report = extract_report_data(data)
    job_description_clean = clean_text(
        job_description,
        max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
    )

    lines = [
        "TalentMatch Pro - ATS Checker Report",
        "=" * 40,
        f"Generated: {utc_timestamp()}",
        f"CV file: {clean_text(cv_filename, max_chars=200)}",
        f"ATS Score: {report['score']}/100",
        f"Result: {report['label']}",
        f"Assessment: {report['message']}",
        "",
    ]

    if report["summary"]:
        lines.extend(
            [
                "Executive Summary",
                "-" * 24,
                report["summary"],
                "",
            ]
        )

    lines.extend(["Matched Keywords", "-" * 20])
    lines.extend(
        [f"- {item}" for item in report["matched_keywords"]]
        or ["- No matched keywords returned."]
    )

    lines.extend(["", "Missing Keywords", "-" * 20])
    lines.extend(
        [f"- {item}" for item in report["missing_keywords"]]
        or ["- No missing keywords returned."]
    )

    lines.extend(["", "Priority Recommendations", "-" * 28])
    lines.extend(
        [
            f"{index}. {item}"
            for index, item in enumerate(
                report["recommendations"],
                start=1,
            )
        ]
        or ["1. No recommendations returned."]
    )

    if job_description_clean:
        lines.extend(
            [
                "",
                "Job Description Appendix",
                "-" * 26,
                job_description_clean,
            ]
        )

    return "\n".join(lines)


def create_pdf_report(
    data: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> Optional[bytes]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            HRFlowable,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        st.error(
            "PDF export requires ReportLab. "
            "Add `reportlab` to frontend requirements."
        )
        return None

    try:
        report = extract_report_data(data)
        cv_name = clean_text(cv_filename, max_chars=200)
        job_description_clean = clean_text(
            job_description,
            max_chars=PDF_JOB_DESCRIPTION_CHARACTERS,
        )

        buffer = BytesIO()
        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=19 * mm,
            bottomMargin=18 * mm,
            title="TalentMatch Pro ATS Checker Report",
            author="TalentMatch Pro",
            subject="ATS keyword coverage report",
            allowSplitting=True,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ATSReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=29,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_LEFT,
            spaceAfter=5,
        )
        subtitle_style = ParagraphStyle(
            "ATSReportSubtitle",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=8,
        )
        section_style = ParagraphStyle(
            "ATSReportSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#0F172A"),
            keepWithNext=True,
            spaceBefore=9,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "ATSReportBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4,
        )
        small_style = ParagraphStyle(
            "ATSReportSmall",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748B"),
        )
        metric_label_style = ParagraphStyle(
            "ATSMetricLabel",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#64748B"),
            alignment=TA_CENTER,
        )
        metric_value_style = ParagraphStyle(
            "ATSMetricValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_CENTER,
        )
        verdict_style = ParagraphStyle(
            "ATSVerdict",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#2563EB"),
            alignment=TA_CENTER,
        )

        def pdf_text(
            value: Any,
            *,
            max_chars: int = MAX_LIST_ITEM_CHARACTERS,
        ) -> str:
            return escape(clean_text(value, max_chars=max_chars))

        def footer(canvas: Any, doc: Any) -> None:
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
            canvas.line(
                document.leftMargin,
                13 * mm,
                A4[0] - document.rightMargin,
                13 * mm,
            )
            canvas.setFont("Helvetica", 7.5)
            canvas.setFillColor(colors.HexColor("#64748B"))
            canvas.drawString(
                document.leftMargin,
                8.5 * mm,
                "Generated by TalentMatch Pro",
            )
            canvas.drawRightString(
                A4[0] - document.rightMargin,
                8.5 * mm,
                f"Page {doc.page}",
            )
            canvas.restoreState()

        def section_banner(
            title: str,
            background: str,
            border: str,
        ) -> Table:
            banner = Table(
                [[
                    Paragraph(
                        f"<b>{pdf_text(title, max_chars=120)}</b>",
                        body_style,
                    )
                ]],
                colWidths=[176 * mm],
            )
            banner.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            colors.HexColor(background),
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.6,
                            colors.HexColor(border),
                        ),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            return banner

        def bullet_paragraphs(
            values: List[str],
            fallback: str,
        ) -> List[Paragraph]:
            source_values = values or [fallback]
            return [
                Paragraph(f"- {pdf_text(value)}", body_style)
                for value in source_values
            ]

        story: List[Any] = []

        brand_table = Table(
            [[
                Paragraph("<b>TalentMatch Pro</b>", body_style),
                Paragraph("ATS Intelligence Report", small_style),
            ]],
            colWidths=[88 * mm, 88 * mm],
        )
        brand_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#F8FAFC"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        colors.HexColor("#CBD5E1"),
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        story.extend(
            [
                brand_table,
                Spacer(1, 7 * mm),
                Paragraph("ATS Checker Report", title_style),
                Paragraph(
                    f"Generated: {utc_timestamp()} &nbsp;&nbsp; | &nbsp;&nbsp; "
                    f"CV: {pdf_text(cv_name, max_chars=200)}",
                    subtitle_style,
                ),
            ]
        )

        metric_data = [
            [
                Paragraph("ATS SCORE", metric_label_style),
                Paragraph("MATCHED", metric_label_style),
                Paragraph("MISSING", metric_label_style),
            ],
            [
                Paragraph(
                    f"<nobr>{report['score']}/100</nobr>",
                    metric_value_style,
                ),
                Paragraph(
                    str(len(report["matched_keywords"])),
                    metric_value_style,
                ),
                Paragraph(
                    str(len(report["missing_keywords"])),
                    metric_value_style,
                ),
            ],
            [
                Paragraph(
                    pdf_text(report["label"], max_chars=120),
                    verdict_style,
                ),
                Paragraph("confirmed keywords", small_style),
                Paragraph("priority keyword gaps", small_style),
            ],
        ]
        metrics_table = Table(
            metric_data,
            colWidths=[58.6 * mm, 58.6 * mm, 58.6 * mm],
            rowHeights=[8 * mm, 13 * mm, 9 * mm],
        )
        metrics_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        colors.HexColor("#F8FAFC"),
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.7,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "INNERGRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        colors.HexColor("#E2E8F0"),
                    ),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )

        story.extend(
            [
                metrics_table,
                Spacer(1, 5 * mm),
                section_banner("ATS Assessment", "#EFF6FF", "#BFDBFE"),
                Spacer(1, 1.5 * mm),
                Paragraph(
                    pdf_text(
                        report["message"],
                        max_chars=MAX_SUMMARY_CHARACTERS,
                    ),
                    body_style,
                ),
            ]
        )

        if report["summary"]:
            story.extend(
                [
                    Paragraph("Executive Summary", section_style),
                    section_banner(
                        "Recruiter Perspective",
                        "#F8FAFC",
                        "#CBD5E1",
                    ),
                    Spacer(1, 1.5 * mm),
                    Paragraph(
                        pdf_text(
                            report["summary"],
                            max_chars=MAX_SUMMARY_CHARACTERS,
                        ),
                        body_style,
                    ),
                ]
            )

        story.extend(
            [
                Paragraph("Keyword Coverage", section_style),
                section_banner("Matched Keywords", "#ECFDF5", "#A7F3D0"),
                Spacer(1, 1.5 * mm),
                *bullet_paragraphs(
                    report["matched_keywords"],
                    "No matched keywords returned.",
                ),
                Spacer(1, 2 * mm),
                section_banner("Missing Keywords", "#FFF7ED", "#FED7AA"),
                Spacer(1, 1.5 * mm),
                *bullet_paragraphs(
                    report["missing_keywords"],
                    "No missing keywords returned.",
                ),
                Paragraph("Priority Recommendations", section_style),
            ]
        )

        recommendations = report["recommendations"] or [
            "No recommendations returned."
        ]

        for index, recommendation in enumerate(
            recommendations,
            start=1,
        ):
            recommendation_table = Table(
                [[
                    Paragraph(f"<b>{index}</b>", verdict_style),
                    Paragraph(pdf_text(recommendation), body_style),
                ]],
                colWidths=[12 * mm, 164 * mm],
                splitByRow=1,
            )
            recommendation_table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (0, 0),
                            colors.HexColor("#EFF6FF"),
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            colors.HexColor("#DBEAFE"),
                        ),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ALIGN", (0, 0), (0, 0), "CENTER"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 7),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.extend([recommendation_table, Spacer(1, 2 * mm)])

        story.extend(
            [
                Spacer(1, 2 * mm),
                HRFlowable(
                    width="100%",
                    thickness=0.6,
                    color=colors.HexColor("#CBD5E1"),
                ),
                Spacer(1, 2 * mm),
                Paragraph(
                    "This report is generated automatically by TalentMatch Pro "
                    "and should be reviewed before making final application "
                    "decisions.",
                    small_style,
                ),
            ]
        )

        if job_description_clean:
            story.extend(
                [
                    PageBreak(),
                    Paragraph("Job Description Appendix", title_style),
                    Paragraph(
                        "The appendix preserves the source job description "
                        "used for this ATS analysis.",
                        subtitle_style,
                    ),
                    section_banner(
                        "Source Job Description",
                        "#F8FAFC",
                        "#CBD5E1",
                    ),
                    Spacer(1, 2 * mm),
                    Paragraph(
                        pdf_text(
                            job_description_clean,
                            max_chars=PDF_JOB_DESCRIPTION_CHARACTERS,
                        ).replace("\n", "<br/>"),
                        body_style,
                    ),
                ]
            )

        document.build(
            story,
            onFirstPage=footer,
            onLaterPages=footer,
        )

        buffer.seek(0)
        pdf_bytes = buffer.getvalue()

        if not pdf_bytes.startswith(b"%PDF"):
            raise ValueError("Generated ATS PDF payload is invalid.")

        return pdf_bytes

    except Exception as exc:
        LOGGER.exception(
            "ATS PDF generation failed.",
            extra={
                "event": "ats_pdf_generation_failed",
                "error_type": type(exc).__name__,
            },
        )
        st.error(
            "The ATS PDF report could not be generated. "
            "TXT export remains available."
        )
        return None


def clear_ats_state() -> None:
    for key in (
        "ats_checker_result",
        "ats_checker_filename",
        "ats_checker_job_description",
        "ats_checker_txt_report",
        "ats_checker_pdf_report",
    ):
        st.session_state.pop(key, None)


def render_kpi_card(
    label: str,
    value: str,
    caption: str,
    accent: str,
) -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="
            border-top:4px solid {safe_html(accent)};
            min-height:160px;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
        ">
            <div class="tm-kicker">{safe_html(label)}</div>
            <div style="
                font-size:2.2rem;
                font-weight:800;
                line-height:1;
                color:#0F172A;
                margin:.55rem 0;
            ">{safe_html(value)}</div>
            <div class="tm-muted">{safe_html(caption)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_keyword_group(
    title: str,
    items: List[str],
    empty_text: str,
    icon: str,
    *,
    green: bool = False,
) -> None:
    pill_class = "tm-pill tm-pill-green" if green else "tm-pill"

    if items:
        chips = "".join(
            f"<span class='{pill_class}'>{safe_html(item)}</span>"
            for item in items[:MAX_LIST_ITEMS]
        )
    else:
        chips = f"<div class='tm-muted'>{safe_html(empty_text)}</div>"

    st.markdown(
        f"""
        <div class="tm-card" style="min-height:220px">
            <div class="tm-card-title">
                {safe_html(icon)} {safe_html(title)}
            </div>
            <div style="margin-top:.8rem">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_recommendations(items: List[str]) -> None:
    if not items:
        st.info("No recommendations returned.")
        return

    for index, item in enumerate(items, start=1):
        st.markdown(
            f"""
            <div class="tm-card" style="
                margin-bottom:.75rem;
                display:grid;
                grid-template-columns:54px 1fr;
                gap:1rem;
                align-items:start;
            ">
                <div style="
                    width:42px;
                    height:42px;
                    border-radius:12px;
                    display:flex;
                    align-items:center;
                    justify-content:center;
                    background:#EFF6FF;
                    color:#2563EB;
                    font-weight:800;
                ">{index}</div>
                <div>
                    <div class="tm-kicker">Priority {index}</div>
                    <div class="tm-muted" style="margin-top:.25rem">
                        {safe_html(item)}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_results(data: Dict[str, Any]) -> None:
    report = extract_report_data(data)

    score = report["score"]
    label = report["label"]
    message = report["message"]
    matched_keywords = report["matched_keywords"]
    missing_keywords = report["missing_keywords"]
    recommendations = report["recommendations"]
    summary = report["summary"]

    cv_filename = clean_text(
        st.session_state.get(
            "ats_checker_filename",
            "uploaded_cv.pdf",
        ),
        max_chars=200,
    )
    job_description = clean_text(
        st.session_state.get(
            "ats_checker_job_description",
            "",
        ),
        max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
    )

    accent, confidence = score_tone(score)

    st.success("ATS check completed and saved to History.")

    st.markdown(
        '<div class="tm-section-title">ATS Intelligence</div>',
        unsafe_allow_html=True,
    )

    kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

    with kpi_1:
        render_kpi_card("ATS Score", f"{score}/100", label, accent)

    with kpi_2:
        render_kpi_card(
            "Matched",
            str(len(matched_keywords)),
            "Confirmed job keywords",
            "#059669",
        )

    with kpi_3:
        render_kpi_card(
            "Missing",
            str(len(missing_keywords)),
            "Priority keyword gaps",
            "#D97706",
        )

    with kpi_4:
        render_kpi_card(
            "Readiness",
            confidence,
            f"{len(recommendations)} priority actions",
            "#2563EB",
        )

    st.markdown(
        f"""
        <div class="tm-card" style="margin-top:.8rem">
            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                gap:1rem;
                flex-wrap:wrap;
            ">
                <div>
                    <div class="tm-kicker">Overall ATS alignment</div>
                    <div class="tm-card-title" style="margin-top:.25rem">
                        {safe_html(label)}
                    </div>
                    <div class="tm-muted" style="margin-top:.25rem">
                        {safe_html(message)}
                    </div>
                </div>
                <div style="font-weight:800;color:{safe_html(accent)}">
                    {score}/100
                </div>
            </div>
            <div style="
                width:100%;
                height:14px;
                margin-top:1rem;
                border-radius:999px;
                background:#E2E8F0;
                overflow:hidden;
            ">
                <div style="
                    width:{score}%;
                    height:100%;
                    background:{safe_html(accent)};
                    border-radius:999px;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if summary:
        st.markdown(
            '<div class="tm-section-title">Executive Summary</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="tm-card" style="
                border-left:5px solid #2563EB;
                padding:1.35rem 1.5rem;
            ">
                <div class="tm-kicker">Recruiter perspective</div>
                <div style="
                    margin-top:.55rem;
                    line-height:1.7;
                    color:#475569;
                    font-size:1rem;
                ">{safe_html(summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="tm-section-title">Keyword Coverage</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        render_keyword_group(
            "Matched Keywords",
            matched_keywords,
            "No matched keywords returned.",
            "✅",
            green=True,
        )

    with right:
        render_keyword_group(
            "Missing Keywords",
            missing_keywords,
            "No missing keywords found.",
            "🎯",
        )

    st.markdown(
        '<div class="tm-section-title">Priority Recommendations</div>',
        unsafe_allow_html=True,
    )
    render_recommendations(recommendations)

    if "ats_checker_txt_report" not in st.session_state:
        st.session_state["ats_checker_txt_report"] = build_text_report(
            data=data,
            cv_filename=cv_filename,
            job_description=job_description,
        )

    st.markdown("---")
    st.markdown(
        '<div class="tm-section-title">Download Report</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Exports include ATS score, keyword coverage, recommendations "
        "and a bounded Job Description appendix."
    )

    col_txt, col_pdf = st.columns(2)

    with col_txt:
        st.download_button(
            "📥 Export ATS Report (.txt)",
            data=st.session_state["ats_checker_txt_report"].encode("utf-8"),
            file_name="talentmatch_ats_checker_summary.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_pdf:
        if "ats_checker_pdf_report" not in st.session_state:
            with st.spinner("Preparing enterprise PDF report..."):
                st.session_state["ats_checker_pdf_report"] = create_pdf_report(
                    data=data,
                    cv_filename=cv_filename,
                    job_description=job_description,
                )

        pdf_bytes = st.session_state.get("ats_checker_pdf_report")
        if pdf_bytes:
            st.download_button(
                "📄 Export ATS Report (.pdf)",
                data=pdf_bytes,
                file_name="talentmatch_ats_checker_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


render_hero(
    "ATS INTELLIGENCE",
    "ATS Checker",
    "Measure keyword coverage, identify critical gaps and optimize your CV before every application.",
    "📋",
)

if not is_logged_in():
    st.warning("Please login before using ATS Checker.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

st.markdown(
    '<div class="tm-section-title">Run a new ATS check</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.25])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📄 CV upload</div>
            <div class="tm-muted">
                Upload one PDF CV. TalentMatch Pro compares its content
                with the target job description.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Upload CV (PDF)",
        type=["pdf"],
        accept_multiple_files=False,
        help="Upload one PDF CV or resume.",
    )

    if uploaded_file is not None:
        safe_filename = clean_text(uploaded_file.name, max_chars=200)
        st.success(
            f"Selected file: {safe_filename} "
            f"({uploaded_file.size / 1024:.1f} KB)"
        )

with right:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🧾 Job description</div>
            <div class="tm-muted">
                Paste the complete job advertisement for the most accurate
                ATS keyword coverage analysis.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    job_description = st.text_area(
        "Job Description",
        height=330,
        max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
        placeholder=EXAMPLE_JOB_DESCRIPTION,
    )

run_clicked = st.button(
    "🚀 Analyze ATS Match",
    type="primary",
    use_container_width=True,
    disabled=uploaded_file is None or not job_description.strip(),
)

if run_clicked:
    if uploaded_file is None:
        st.error("Please upload your CV as a PDF.")
        st.stop()

    job_description_clean = clean_text(
        job_description,
        max_chars=MAX_JOB_DESCRIPTION_CHARACTERS,
    )
    if not job_description_clean:
        st.error("Please paste the job description.")
        st.stop()

    clear_ats_state()

    safe_filename = clean_text(uploaded_file.name, max_chars=200)
    files = {
        "file": (
            safe_filename,
            uploaded_file.getvalue(),
            "application/pdf",
        )
    }
    request_data = {"job_description": job_description_clean}

    with st.spinner("Running ATS keyword analysis..."):
        raw_response = api_post(
            "/ats-test",
            data=request_data,
            files=files,
            timeout=180,
        )

    response, call_error = normalize_response(raw_response)
    if call_error:
        st.error(
            "ATS check failed: "
            + clean_text(call_error, max_chars=500)
        )
        st.stop()

    payload, parse_error = response_to_json(response)
    if parse_error:
        st.error(parse_error)
        st.stop()

    if not payload:
        st.error("ATS check failed: empty backend response.")
        st.stop()

    st.session_state["ats_checker_result"] = payload
    st.session_state["ats_checker_filename"] = safe_filename
    st.session_state["ats_checker_job_description"] = job_description_clean

result = st.session_state.get("ats_checker_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
