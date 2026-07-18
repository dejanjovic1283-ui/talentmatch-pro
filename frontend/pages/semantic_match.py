from __future__ import annotations

from datetime import datetime, timezone
from html import escape
from io import BytesIO
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

import streamlit as st

from auth_utils import api_post, is_logged_in, is_pro_user
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(
    page_title="Semantic Match • TalentMatch Pro",
    page_icon="🧠",
    layout="wide",
)
apply_global_styles()
render_sidebar()


DEFAULT_JOB_DESCRIPTION = """Python Backend Developer (FastAPI)

We are looking for a Python Backend Developer to join our engineering team and help build scalable web applications and AI-powered services.

Responsibilities
Design, develop and maintain REST APIs using FastAPI.
Build scalable backend services with Python.
Integrate PostgreSQL databases and optimize SQL queries.
Work with Firebase Authentication and Firebase Storage.
Integrate third-party APIs including OpenAI and PayPal.
Collaborate with frontend developers using Streamlit.
Write clean, maintainable and well-tested code.
Participate in code reviews and improve application performance.
Deploy and maintain applications on Render.

Requirements
2+ years of Python development experience.
Strong knowledge of FastAPI.
Experience with PostgreSQL.
Experience with REST API development.
Experience with Git and GitHub.
Experience with Docker.
Knowledge of authentication and authorization.
Familiarity with cloud deployment.
Understanding of software architecture and clean code principles.
Good English communication skills.
""".strip()

MAX_LIST_ITEMS = 40
MAX_LIST_ITEM_CHARS = 500
MAX_SUMMARY_CHARS = 4_000
MAX_JOB_DESCRIPTION_CHARS = 15_000
PDF_JOB_DESCRIPTION_CHARS = 5_000


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def clean_text(value: Any, *, max_chars: int = 4_000) -> str:
    text = str(value or "")
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1].rstrip() + "…"
    return text


def normalize_response(raw: Any) -> Tuple[Optional[Any], Optional[str]]:
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
    text = clean_text(getattr(response, "text", "") or "", max_chars=800)

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
            if text:
                detail = text

        return None, f"Semantic Match failed ({status_code}): {detail}"

    try:
        payload = response.json()
    except (TypeError, ValueError):
        return None, "Backend returned an invalid response."

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
    max_item_chars: int = MAX_LIST_ITEM_CHARS,
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

        if 0 < numeric <= 1:
            numeric *= 100

        return max(0, min(100, int(round(numeric))))
    except (TypeError, ValueError, OverflowError):
        return None


def get_score(
    data: Dict[str, Any],
    *keys: str,
    default: int = 0,
) -> int:
    zero_found = False

    for key in keys:
        score = score_number(data.get(key))
        if score is None:
            continue
        if score > 0:
            return score
        zero_found = True

    return 0 if zero_found else default


def get_verdict(score: int, existing: str = "") -> str:
    normalized = clean_text(existing, max_chars=120)
    if normalized:
        return normalized

    if score >= 85:
        return "Excellent Semantic Match"
    if score >= 75:
        return "Strong Semantic Match"
    if score >= 60:
        return "Good Semantic Match"
    if score >= 40:
        return "Moderate Semantic Match"
    return "Weak Semantic Match"


def score_tone(score: int) -> Tuple[str, str]:
    if score >= 80:
        return "#059669", "High confidence"
    if score >= 60:
        return "#2563EB", "Competitive"
    if score >= 40:
        return "#D97706", "Needs optimization"
    return "#DC2626", "Low alignment"


def extract_report_data(data: Dict[str, Any]) -> Dict[str, Any]:
    combined_score = get_score(
        data,
        "combined_score",
        "overall_score",
        "overall_match",
        "score",
        "match_score",
        "ai_score",
        "recruiter_score",
    )
    semantic_score = get_score(
        data,
        "semantic_score",
        "semantic_match_score",
        "semantic_match",
    )
    keyword_score = get_score(
        data,
        "keyword_score",
        "keyword_match_score",
        "keyword_match",
    )

    return {
        "combined_score": combined_score,
        "semantic_score": semantic_score,
        "keyword_score": keyword_score,
        "verdict": get_verdict(
            combined_score,
            str(data.get("verdict") or data.get("recommendation") or ""),
        ),
        "summary": clean_text(
            data.get("summary")
            or data.get("recruiter_summary")
            or data.get("executive_summary")
            or "Semantic match completed.",
            max_chars=MAX_SUMMARY_CHARS,
        ),
        "matched_themes": normalize_list(
            data.get("matched_themes")
            or data.get("matched_skills")
            or data.get("strengths")
        ),
        "missing_themes": normalize_list(
            data.get("missing_themes")
            or data.get("missing_skills")
            or data.get("weaknesses")
        ),
        "matched_keywords": normalize_list(data.get("matched_keywords")),
        "missing_keywords": normalize_list(data.get("missing_keywords")),
        "recommendations": normalize_list(data.get("recommendations")),
    }


def build_text_report(
    data: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> str:
    report = extract_report_data(data)
    job_description_clean = clean_text(
        job_description,
        max_chars=MAX_JOB_DESCRIPTION_CHARS,
    )

    lines = [
        "TalentMatch Pro - Semantic Match Report",
        "=" * 44,
        f"Generated: {utc_timestamp()}",
        f"CV file: {clean_text(cv_filename, max_chars=200)}",
        f"Combined Score: {report['combined_score']}/100",
        f"Semantic Score: {report['semantic_score']}/100",
        f"Keyword Score: {report['keyword_score']}/100",
        f"Verdict: {report['verdict']}",
        "",
        "Executive Recruiter Summary",
        "-" * 28,
        report["summary"],
        "",
        "Matched Themes",
        "-" * 20,
    ]

    lines.extend(
        [f"- {item}" for item in report["matched_themes"]]
        or ["- No matched themes returned."]
    )
    lines.extend(["", "Missing Themes", "-" * 20])
    lines.extend(
        [f"- {item}" for item in report["missing_themes"]]
        or ["- No missing themes returned."]
    )
    lines.extend(["", "Matched Keywords", "-" * 20])
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
        [f"{index}. {item}" for index, item in enumerate(report["recommendations"], 1)]
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
            KeepTogether,
            ListFlowable,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError:
        st.error(
            "PDF export requires ReportLab. Add `reportlab` to frontend requirements."
        )
        return None

    report = extract_report_data(data)
    cv_name = clean_text(cv_filename, max_chars=200)
    job_description_clean = clean_text(
        job_description,
        max_chars=PDF_JOB_DESCRIPTION_CHARS,
    )

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=19 * mm,
        bottomMargin=18 * mm,
        title="TalentMatch Pro Semantic Match Report",
        author="TalentMatch Pro",
        subject="Semantic Match Report",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TMTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=29,
        textColor=colors.HexColor("#0F172A"),
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "TMSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=8,
    )
    section_style = ParagraphStyle(
        "TMSection",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=9,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "TMBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5,
    )
    small_style = ParagraphStyle(
        "TMSmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748B"),
    )
    metric_label_style = ParagraphStyle(
        "TMMetricLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#64748B"),
        alignment=TA_CENTER,
    )
    metric_value_style = ParagraphStyle(
        "TMMetricValue",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        alignment=TA_CENTER,
    )
    verdict_style = ParagraphStyle(
        "TMVerdict",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#2563EB"),
        alignment=TA_CENTER,
    )

    def pdf_text(value: Any) -> str:
        return escape(clean_text(value, max_chars=4_000))

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

    def bullet_flowable(
        values: List[str],
        fallback: str,
    ) -> ListFlowable:
        source_values = values or [fallback]
        paragraphs = [
            Paragraph(pdf_text(value), body_style)
            for value in source_values
        ]
        return ListFlowable(
            paragraphs,
            bulletType="bullet",
            start="circle",
            leftIndent=15,
            bulletFontName="Helvetica",
            bulletFontSize=7,
            bulletColor=colors.HexColor("#2563EB"),
            spaceAfter=5,
        )

    story: List[Any] = []

    brand_table = Table(
        [
            [
                Paragraph("<b>TalentMatch Pro</b>", body_style),
                Paragraph("Semantic Intelligence Report", small_style),
            ]
        ],
        colWidths=[88 * mm, 88 * mm],
    )
    brand_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
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
            Spacer(1, 8 * mm),
            Paragraph("Semantic Match Report", title_style),
            Paragraph(
                f"Generated: {utc_timestamp()} &nbsp;&nbsp; | &nbsp;&nbsp; "
                f"CV: {pdf_text(cv_name)}",
                subtitle_style,
            ),
        ]
    )

    metric_data = [
        [
            Paragraph("OVERALL MATCH", metric_label_style),
            Paragraph("SEMANTIC", metric_label_style),
            Paragraph("KEYWORD", metric_label_style),
        ],
        [
            Paragraph(
                f"{report['combined_score']}/100",
                metric_value_style,
            ),
            Paragraph(
                f"{report['semantic_score']}/100",
                metric_value_style,
            ),
            Paragraph(
                f"{report['keyword_score']}/100",
                metric_value_style,
            ),
        ],
        [
            Paragraph(pdf_text(report["verdict"]), verdict_style),
            Paragraph(
                f"{len(report['matched_themes'])} matched themes",
                small_style,
            ),
            Paragraph(
                f"{len(report['matched_keywords'])} matched keywords",
                small_style,
            ),
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
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#CBD5E1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#E2E8F0")),
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
            Spacer(1, 6 * mm),
            Paragraph("Executive Recruiter Summary", section_style),
            Table(
                [[Paragraph(pdf_text(report["summary"]), body_style)]],
                colWidths=[176 * mm],
                style=TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            colors.HexColor("#EFF6FF"),
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.7,
                            colors.HexColor("#BFDBFE"),
                        ),
                        ("LEFTPADDING", (0, 0), (-1, -1), 9),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            Spacer(1, 4 * mm),
        ]
    )

    coverage_table = Table(
        [
            [
                KeepTogether(
                    [
                        Paragraph("Matched Themes", section_style),
                        bullet_flowable(
                            report["matched_themes"],
                            "No matched themes returned.",
                        ),
                    ]
                ),
                KeepTogether(
                    [
                        Paragraph("Missing Themes", section_style),
                        bullet_flowable(
                            report["missing_themes"],
                            "No missing themes returned.",
                        ),
                    ]
                ),
            ]
        ],
        colWidths=[87 * mm, 87 * mm],
    )
    coverage_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#ECFDF5")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#FFF7ED")),
                ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#A7F3D0")),
                ("BOX", (1, 0), (1, 0), 0.6, colors.HexColor("#FED7AA")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            Paragraph("Semantic Coverage", section_style),
            coverage_table,
            Spacer(1, 4 * mm),
        ]
    )

    keyword_table = Table(
        [
            [
                KeepTogether(
                    [
                        Paragraph("Matched Keywords", section_style),
                        bullet_flowable(
                            report["matched_keywords"],
                            "No matched keywords returned.",
                        ),
                    ]
                ),
                KeepTogether(
                    [
                        Paragraph("Missing Keywords", section_style),
                        bullet_flowable(
                            report["missing_keywords"],
                            "No missing keywords returned.",
                        ),
                    ]
                ),
            ]
        ],
        colWidths=[87 * mm, 87 * mm],
    )
    keyword_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#F0FDFA")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F8FAFC")),
                ("BOX", (0, 0), (0, 0), 0.6, colors.HexColor("#99F6E4")),
                ("BOX", (1, 0), (1, 0), 0.6, colors.HexColor("#CBD5E1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend(
        [
            keyword_table,
            Paragraph("Priority Recommendations", section_style),
        ]
    )

    recommendations = report["recommendations"] or [
        "No recommendations returned."
    ]
    recommendation_rows = []
    for index, recommendation in enumerate(recommendations, start=1):
        recommendation_rows.append(
            [
                Paragraph(f"<b>{index}</b>", verdict_style),
                Paragraph(pdf_text(recommendation), body_style),
            ]
        )

    recommendations_table = Table(
        recommendation_rows,
        colWidths=[12 * mm, 164 * mm],
    )
    recommendations_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EFF6FF")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#DBEAFE")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E2E8F0")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(recommendations_table)

    if job_description_clean:
        story.extend(
            [
                PageBreak(),
                Paragraph("Job Description Appendix", title_style),
                Paragraph(
                    "Included for auditability and report context. "
                    "Long job descriptions are intentionally bounded.",
                    subtitle_style,
                ),
                Table(
                    [[Paragraph(pdf_text(job_description_clean), body_style)]],
                    colWidths=[176 * mm],
                    style=TableStyle(
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
                                0.6,
                                colors.HexColor("#CBD5E1"),
                            ),
                            ("LEFTPADDING", (0, 0), (-1, -1), 9),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                            ("TOPPADDING", (0, 0), (-1, -1), 8),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ]
                    ),
                ),
            ]
        )

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer.getvalue()


def clear_semantic_state() -> None:
    for key in (
        "semantic_result",
        "semantic_filename",
        "semantic_job_description",
        "semantic_txt_report",
        "semantic_pdf_report",
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
            min-height:168px;
            display:flex;
            flex-direction:column;
            justify-content:space-between;
        ">
            <div class="tm-kicker">{safe_html(label)}</div>
            <div style="
                font-size:2.35rem;
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


def render_progress_card(
    combined_score: int,
    verdict: str,
) -> None:
    accent, confidence = score_tone(combined_score)
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
                    <div class="tm-kicker">Overall role alignment</div>
                    <div class="tm-card-title" style="margin-top:.25rem">
                        {safe_html(verdict)}
                    </div>
                </div>
                <div style="font-weight:800;color:{safe_html(accent)}">
                    {safe_html(confidence)}
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
                    width:{combined_score}%;
                    height:100%;
                    background:{safe_html(accent)};
                    border-radius:999px;
                "></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_list_card(
    title: str,
    items: List[str],
    icon: str,
    *,
    positive: bool = False,
) -> None:
    pill_class = "tm-pill tm-pill-green" if positive else "tm-pill"
    if items:
        chips = "".join(
            f"<span class='{pill_class}'>{safe_html(item)}</span>"
            for item in items[:MAX_LIST_ITEMS]
        )
    else:
        chips = "<div class='tm-muted'>No items returned.</div>"

    st.markdown(
        f"""
        <div class="tm-card" style="min-height:230px">
            <div class="tm-card-title">
                {safe_html(icon)} {safe_html(title)}
            </div>
            <div style="margin-top:.8rem">{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results(data: Dict[str, Any]) -> None:
    cv_filename = clean_text(
        st.session_state.get("semantic_filename", "uploaded_cv.pdf"),
        max_chars=200,
    )
    job_description = clean_text(
        st.session_state.get("semantic_job_description", ""),
        max_chars=MAX_JOB_DESCRIPTION_CHARS,
    )
    report = extract_report_data(data)

    combined_score = report["combined_score"]
    semantic_score = report["semantic_score"]
    keyword_score = report["keyword_score"]
    verdict = report["verdict"]
    summary = report["summary"]
    matched_themes = report["matched_themes"]
    missing_themes = report["missing_themes"]
    matched_keywords = report["matched_keywords"]
    missing_keywords = report["missing_keywords"]
    recommendations = report["recommendations"]

    st.success("Semantic match completed and saved to History.")

    st.markdown(
        '<div class="tm-section-title">Match Intelligence</div>',
        unsafe_allow_html=True,
    )
    kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)

    accent, confidence = score_tone(combined_score)
    with kpi_1:
        render_kpi_card(
            "Overall Match",
            f"{combined_score}/100",
            verdict,
            accent,
        )
    with kpi_2:
        render_kpi_card(
            "Semantic Alignment",
            f"{semantic_score}/100",
            f"{len(matched_themes)} matched themes",
            "#0EA5E9",
        )
    with kpi_3:
        render_kpi_card(
            "Keyword Coverage",
            f"{keyword_score}/100",
            f"{len(matched_keywords)} matched keywords",
            "#8B5CF6",
        )
    with kpi_4:
        render_kpi_card(
            "Recruiter Readiness",
            confidence,
            f"{len(recommendations)} priority actions",
            "#14B8A6",
        )

    render_progress_card(combined_score, verdict)

    st.markdown(
        '<div class="tm-section-title">Executive Recruiter Summary</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="tm-card" style="
            border-left:5px solid #2563EB;
            padding:1.35rem 1.5rem;
        ">
            <div class="tm-kicker">Hiring perspective</div>
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
        '<div class="tm-section-title">Semantic Coverage</div>',
        unsafe_allow_html=True,
    )
    left, right = st.columns(2)
    with left:
        render_list_card(
            "Matched Themes",
            matched_themes,
            "✅",
            positive=True,
        )
    with right:
        render_list_card(
            "Missing Themes",
            missing_themes,
            "⚠️",
        )

    keyword_left, keyword_right = st.columns(2)
    with keyword_left:
        render_list_card(
            "Matched Keywords",
            matched_keywords,
            "🔎",
            positive=True,
        )
    with keyword_right:
        render_list_card(
            "Missing Keywords",
            missing_keywords,
            "🎯",
        )

    st.markdown(
        '<div class="tm-section-title">Priority Recommendations</div>',
        unsafe_allow_html=True,
    )
    if recommendations:
        for index, item in enumerate(recommendations, start=1):
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
    else:
        st.info("No recommendations returned.")

    if "semantic_txt_report" not in st.session_state:
        st.session_state["semantic_txt_report"] = build_text_report(
            data,
            cv_filename,
            job_description,
        )

    st.markdown("---")
    st.markdown(
        '<div class="tm-section-title">Download Report</div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Exports include the complete score breakdown, recruiter summary, "
        "semantic coverage and a bounded Job Description appendix."
    )

    col_txt, col_pdf = st.columns(2)

    with col_txt:
        st.download_button(
            "📥 Export Semantic Match Report (.txt)",
            data=st.session_state["semantic_txt_report"].encode("utf-8"),
            file_name="talentmatch_semantic_match_summary.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_pdf:
        if "semantic_pdf_report" not in st.session_state:
            with st.spinner("Preparing enterprise PDF report..."):
                st.session_state["semantic_pdf_report"] = create_pdf_report(
                    data,
                    cv_filename,
                    job_description,
                )

        pdf_bytes = st.session_state.get("semantic_pdf_report")
        if pdf_bytes:
            st.download_button(
                "📄 Export Semantic Match Report (.pdf)",
                data=pdf_bytes,
                file_name="talentmatch_semantic_match_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


render_hero(
    "SEMANTIC INTELLIGENCE",
    "Semantic Match",
    "Compare meaning, role alignment, skills coverage and recruiter readiness.",
    "🧠",
)

if not is_logged_in():
    st.warning("Please login before using Semantic Match.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

if not is_pro_user():
    st.warning("Semantic Match is a Pro feature.")
    st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
    st.stop()

st.markdown(
    '<div class="tm-section-title">Run a new semantic match</div>',
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1.25])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📄 CV upload</div>
            <div class="tm-muted">
                Upload one PDF CV. TalentMatch Pro compares role meaning,
                experience signals, themes and keyword coverage.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_file = st.file_uploader(
        "Upload CV (PDF)",
        type=["pdf"],
        accept_multiple_files=False,
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
                semantic, keyword and recruiter-readiness scoring.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    job_description = st.text_area(
        "Job Description",
        value=DEFAULT_JOB_DESCRIPTION,
        height=330,
        max_chars=MAX_JOB_DESCRIPTION_CHARS,
    )

run_clicked = st.button(
    "🚀 Run Semantic Match",
    use_container_width=True,
    disabled=uploaded_file is None or not job_description.strip(),
)

if run_clicked:
    if uploaded_file is None:
        st.error("Please upload your CV as a PDF.")
        st.stop()

    job_description_clean = clean_text(
        job_description,
        max_chars=MAX_JOB_DESCRIPTION_CHARS,
    )
    if not job_description_clean:
        st.error("Please paste the job description.")
        st.stop()

    clear_semantic_state()

    safe_filename = clean_text(uploaded_file.name, max_chars=200)
    files = {
        "file": (
            safe_filename,
            uploaded_file.getvalue(),
            "application/pdf",
        )
    }
    request_data = {"job_description": job_description_clean}

    with st.spinner("Running AI-powered semantic analysis..."):
        raw_response = api_post(
            "/semantic-match",
            data=request_data,
            files=files,
            timeout=180,
        )

    response, call_error = normalize_response(raw_response)
    if call_error:
        st.error(
            f"Semantic Match failed: "
            f"{clean_text(call_error, max_chars=500)}"
        )
        st.stop()

    payload, parse_error = response_to_json(response)
    if parse_error:
        st.error(parse_error)
        st.stop()

    if not payload:
        st.error("Semantic Match failed: empty backend response.")
        st.stop()

    st.session_state["semantic_result"] = payload
    st.session_state["semantic_filename"] = safe_filename
    st.session_state["semantic_job_description"] = job_description_clean

result = st.session_state.get("semantic_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
