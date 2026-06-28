# pyright: reportArgumentType=false
import json
import os
from datetime import datetime
from io import BytesIO
from urllib.parse import urlencode
from typing import Any, Dict

import requests
import streamlit as st

from auth_utils import api_get, is_logged_in, is_pro_user
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero


st.set_page_config(page_title="History • TalentMatch Pro", page_icon="📜", layout="wide")
apply_global_styles()
render_sidebar()

render_hero(
    "Analysis history",
    "Your saved TalentMatch Pro reports",
    "Search, filter, sort and export previous CV analyses with branded PDF reports.",
    "📜",
)


BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")


TYPE_LABELS = {
    "cv_analysis": "CV Analysis",
    "cv_rewrite": "CV Rewrite",
    "ats_checker": "ATS",
    "ats": "ATS",
    "semantic_match": "Semantic",
    "recruiter_mode": "Recruiter",
}

FILTER_OPTIONS = {
    "All": None,
    "ATS": "ats_checker",
    "Semantic": "semantic_match",
    "Recruiter": "recruiter_mode",
    "CV Analysis": "cv_analysis",
    "CV Rewrite": "cv_rewrite",
}

BADGE_STYLES = {
    "cv_analysis": ("CV Analysis", "#E8F0FE", "#174EA6"),
    "cv_rewrite": ("CV Rewrite", "#E0F7FA", "#006064"),
    "ats_checker": ("ATS", "#E6F4EA", "#137333"),
    "ats": ("ATS", "#E6F4EA", "#137333"),
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


def safe_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass

        return [item.strip() for item in raw.replace("\n", ",").split(",") if item.strip()]

    return [str(value).strip()] if str(value).strip() else []


def normalize_type(item: dict) -> str:
    return str(item.get("analysis_type") or "cv_analysis").strip().lower()


def history_label(item: dict) -> str:
    analysis_type = normalize_type(item)
    return TYPE_LABELS.get(analysis_type, analysis_type.replace("_", " ").title())


def render_badge(item: dict) -> None:
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
        ">{label}</span>
        """,
        unsafe_allow_html=True,
    )


def score_color(score) -> str:
    try:
        numeric_score = int(float(score))
    except Exception:
        numeric_score = 0

    if numeric_score >= 75:
        return "#137333"
    if numeric_score >= 50:
        return "#B06000"
    return "#B3261E"


def parse_history_response(response):
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

    if isinstance(payload, list):
        return payload, None

    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("history") or payload.get("data") or []
        if isinstance(items, list):
            return items, None

    return None, "Backend returned invalid history format."


def build_history_text_report(items: list[dict], title: str = "TalentMatch Pro - Complete History Report") -> str:
    lines = [
        title,
        "=" * len(title),
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"Total items: {len(items)}",
        "",
    ]

    if not items:
        lines.append("No history items available.")
        return "\n".join(lines)

    counts = {
        "ATS": sum(1 for item in items if normalize_type(item) in {"ats_checker", "ats"}),
        "Semantic": sum(1 for item in items if normalize_type(item) == "semantic_match"),
        "Recruiter": sum(1 for item in items if normalize_type(item) == "recruiter_mode"),
        "CV Analysis": sum(1 for item in items if normalize_type(item) == "cv_analysis"),
        "CV Rewrite": sum(1 for item in items if normalize_type(item) == "cv_rewrite"),
    }

    lines.extend(
        [
            "Summary",
            "-" * 20,
            f"ATS: {counts['ATS']}",
            f"Semantic: {counts['Semantic']}",
            f"Recruiter: {counts['Recruiter']}",
            f"CV Analysis: {counts['CV Analysis']}",
            f"CV Rewrite: {counts['CV Rewrite']}",
            "",
        ]
    )

    for idx, item in enumerate(items, start=1):
        lines.append(build_text_report(item, index=idx))
        lines.append("")
        lines.append("-" * 60)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_text_report(item: dict, index: int | None = None) -> str:
    cv_filename = item.get("cv_filename") or item.get("filename") or "CV"
    score = item.get("score") or item.get("match_score") or 0
    summary = item.get("summary") or item.get("analysis") or ""
    strengths = safe_list(item.get("strengths") or item.get("matched_skills") or item.get("matched_keywords"))
    weaknesses = safe_list(item.get("weaknesses") or item.get("missing_skills") or item.get("missing_keywords"))
    recommendations = safe_list(item.get("recommendations"))
    job_description = item.get("job_description") or item.get("job") or item.get("description") or ""

    report_title = f"TalentMatch Pro - {history_label(item)} Report"
    if index is not None:
        report_title = f"{index}. " + report_title

    lines = [
        report_title,
        "=" * len(report_title),
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"CV file: {cv_filename}",
        f"Type: {history_label(item)}",
        f"Score: {score}/100",
        "",
        "Summary",
        "-" * 20,
        summary or "No summary returned.",
        "",
        "Strengths / Matched Skills",
        "-" * 20,
    ]

    lines.extend([f"- {value}" for value in strengths] or ["- No strengths returned."])

    lines.extend(["", "Weaknesses / Gaps", "-" * 20])
    lines.extend([f"- {value}" for value in weaknesses] or ["- No weaknesses returned."])

    lines.extend(["", "Recommendations", "-" * 20])
    lines.extend([f"- {value}" for value in recommendations] or ["- No recommendations returned."])

    if job_description:
        lines.extend(["", "Job Description", "-" * 20, str(job_description)])

    return "\n".join(lines)


def safe_report_filename(cv_filename: str, suffix: str = "talentmatch_report") -> str:
    safe_name = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in str(cv_filename).replace(".pdf", "")
    ).strip("_")

    if not safe_name:
        safe_name = "talentmatch_cv"

    return f"{safe_name}_{suffix}"


def build_pdf_report(items: list[dict], title: str = "TalentMatch Pro History Report") -> bytes | None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm, inch
        from reportlab.platypus import (
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except Exception:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=42,
        leftMargin=42,
        topMargin=42,
        bottomMargin=56,
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
        textColor=colors.HexColor("#1F2937"),
        spaceAfter=12,
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
        textColor=colors.HexColor("#1F2937"),
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

    def draw_footer(canvas, doc) -> None:
        canvas.saveState()
        width, _ = A4
        footer_y = 0.72 * cm
        line_y = 1.08 * cm
        canvas.setStrokeColor(colors.HexColor("#D1D5DB"))
        canvas.setLineWidth(0.4)
        canvas.line(1.6 * cm, line_y, width - 1.6 * cm, line_y)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawString(1.6 * cm, footer_y, "Generated by TalentMatch Pro")
        canvas.drawRightString(width - 1.6 * cm, footer_y, f"Page {doc.page}")
        canvas.restoreState()

    story: list[Any] = [
        Paragraph(title, title_style),
        Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", subtitle_style),
    ]

    if not items:
        story.append(Paragraph("No history items available.", normal_style))
        doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
        return buffer.getvalue()

    counts = {
        "ATS": sum(1 for item in items if normalize_type(item) in {"ats_checker", "ats"}),
        "Semantic": sum(1 for item in items if normalize_type(item) == "semantic_match"),
        "Recruiter": sum(1 for item in items if normalize_type(item) == "recruiter_mode"),
        "CV Analysis": sum(1 for item in items if normalize_type(item) == "cv_analysis"),
        "CV Rewrite": sum(1 for item in items if normalize_type(item) == "cv_rewrite"),
    }

    summary_data = [["Total", str(len(items))]] + [[key, str(value)] for key, value in counts.items()]
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
        cv_file = item.get("cv_filename") or item.get("cv_file") or item.get("filename") or item.get("file_name") or "CV"
        created_at = item.get("created_at") or item.get("date") or ""
        score = item.get("score") or item.get("match_score") or 0
        analysis_type = normalize_type(item)
        label = history_label(item)
        label_color = PDF_TYPE_COLORS.get(analysis_type, "#263238")
        sc_color = score_color(score)

        summary = item.get("summary") or item.get("analysis") or ""
        strengths = safe_list(item.get("matched_skills") or item.get("strengths") or item.get("matched_keywords"))
        weaknesses = safe_list(item.get("missing_skills") or item.get("missing_keywords") or item.get("weaknesses"))
        recommendations = safe_list(item.get("recommendations"))
        job_description = item.get("job_description") or item.get("job") or item.get("description") or ""

        story.append(Paragraph(f"{idx}. {cv_file}", section_style))

        meta_table = Table(
            [
                [
                    Paragraph(label, label_style),
                    Paragraph(f"<b>Score:</b> <font color='{sc_color}'>{score}/100</font>", normal_style),
                    Paragraph(f"<b>Date:</b> {created_at or '-'}", small_style),
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
        story.append(Paragraph(str(summary or "No summary returned."), normal_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("<b>Strengths / Matched Skills</b>", normal_style))
        for value in strengths or ["No strengths saved."]:
            story.append(Paragraph(f"• {value}", bullet_style))

        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Weaknesses / Gaps</b>", normal_style))
        for value in weaknesses or ["No weaknesses saved."]:
            story.append(Paragraph(f"• {value}", bullet_style))

        story.append(Spacer(1, 4))
        story.append(Paragraph("<b>Recommendations</b>", normal_style))
        for value in recommendations or ["No recommendations saved."]:
            story.append(Paragraph(f"• {value}", bullet_style))

        if job_description:
            story.append(Spacer(1, 4))
            story.append(Paragraph("<b>Job Description</b>", normal_style))
            story.append(Paragraph(str(job_description), small_style))

        story.append(Spacer(1, 14))

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue()


def history_endpoint(selected_type: str | None) -> str:
    if not selected_type:
        return "/history"
    return "/history?" + urlencode({"analysis_type": selected_type})


def get_auth_headers() -> Dict[str, str]:
    token = st.session_state.get("access_token") or st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def api_delete(path: str, timeout: int = 60):
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


if not is_logged_in():
    st.warning("Please login before viewing history.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

left, right = st.columns([2, 1])
with left:
    selected_label = st.radio(
        "Filter by analysis type",
        list(FILTER_OPTIONS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
with right:
    if st.button("Refresh history", width="stretch"):
        clear_history_cache()
        st.rerun()

selected_type = FILTER_OPTIONS[selected_label]
cache_key = f"history_items::{selected_type or 'all'}"

if cache_key not in st.session_state:
    with st.spinner("Loading history..."):
        resp = api_get(history_endpoint(selected_type), timeout=90)
        parsed_items, error = parse_history_response(resp)

        if error:
            st.error(error)
            st.stop()

        st.session_state[cache_key] = parsed_items or []

items_raw = st.session_state.get(cache_key, [])
items: list[dict] = items_raw if isinstance(items_raw, list) else []
all_items_for_counts: list[dict] = items

st.markdown("### 🔍 Search & Sort")

search_col, sort_col = st.columns([2, 1])

with search_col:
    search_query = st.text_input(
        "Search by CV filename",
        placeholder="Example: 20260501_cv2.pdf",
        label_visibility="collapsed",
    )

with sort_col:
    sort_option = st.selectbox(
        "Sort history",
        ["Newest first", "Oldest first", "Highest score", "Lowest score"],
        label_visibility="collapsed",
    )

filtered_items: list[dict] = items

if search_query.strip():
    query = search_query.strip().lower()
    filtered_items = [
        item
        for item in filtered_items
        if query
        in str(
            item.get("cv_filename")
            or item.get("cv_file")
            or item.get("filename")
            or item.get("file_name")
            or ""
        ).lower()
    ]


def _sort_created_at(item: dict) -> str:
    return str(item.get("created_at") or item.get("date") or "")


def _sort_score(item: dict) -> int:
    try:
        return int(float(item.get("score") or item.get("match_score") or 0))
    except Exception:
        return 0


if sort_option == "Newest first":
    filtered_items = sorted(filtered_items, key=_sort_created_at, reverse=True)
elif sort_option == "Oldest first":
    filtered_items = sorted(filtered_items, key=_sort_created_at)
elif sort_option == "Highest score":
    filtered_items = sorted(filtered_items, key=_sort_score, reverse=True)
elif sort_option == "Lowest score":
    filtered_items = sorted(filtered_items, key=_sort_score)

items = filtered_items

if selected_type is not None:
    if "history_items::all" not in st.session_state:
        with st.spinner("Loading counters..."):
            resp_all = api_get("/history", timeout=90)
            parsed_all, err_all = parse_history_response(resp_all)
            if err_all or not isinstance(parsed_all, list):
                all_items_for_counts = items
            else:
                all_items_for_counts = parsed_all
            st.session_state["history_items::all"] = all_items_for_counts
    else:
        cached_all = st.session_state.get("history_items::all", [])
        all_items_for_counts = cached_all if isinstance(cached_all, list) else []

counts = {
    "total": len(all_items_for_counts),
    "ats_checker": sum(1 for item in all_items_for_counts if normalize_type(item) in {"ats_checker", "ats"}),
    "semantic_match": sum(1 for item in all_items_for_counts if normalize_type(item) == "semantic_match"),
    "recruiter_mode": sum(1 for item in all_items_for_counts if normalize_type(item) == "recruiter_mode"),
    "cv_analysis": sum(1 for item in all_items_for_counts if normalize_type(item) == "cv_analysis"),
    "cv_rewrite": sum(1 for item in all_items_for_counts if normalize_type(item) == "cv_rewrite"),
}

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total", counts["total"])
m2.metric("ATS", counts["ats_checker"])
m3.metric("Semantic", counts["semantic_match"])
m4.metric("Recruiter", counts["recruiter_mode"])
m5.metric("CV Analysis", counts["cv_analysis"])
m6.metric("CV Rewrite", counts["cv_rewrite"])

st.divider()

history_txt = build_history_text_report(
    items,
    title="TalentMatch Pro - Complete History Report" if selected_type is None else f"TalentMatch Pro - {selected_label} History Report",
)
all_history_pdf = build_pdf_report(
    items,
    title="TalentMatch Pro - Complete History Report" if selected_type is None else f"TalentMatch Pro - {selected_label} History Report",
)

st.markdown("## Download Report")
all_report_col1, all_report_col2 = st.columns(2)

with all_report_col1:
    st.download_button(
        "⬇️ Download History TXT",
        data=history_txt.encode("utf-8"),
        file_name="talentmatch_history.txt",
        mime="text/plain",
        width="stretch",
        disabled=not items,
    )

with all_report_col2:
    if is_pro_user():
        st.download_button(
            "📄 Download History PDF Report",
            data=all_history_pdf or b"PDF export requires reportlab.",
            file_name="talentmatch_history_report.pdf",
            mime="application/pdf" if all_history_pdf else "text/plain",
            width="stretch",
            disabled=not items or all_history_pdf is None,
        )
    else:
        st.info("🔒 History PDF Report is available in Pro.")
        st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")

st.markdown("## Danger Zone")
with st.expander("🗑 Delete All History"):
    st.warning("This deletes all history records for your account. This action cannot be undone.")
    delete_all_confirm = st.text_input(
        "Type DELETE ALL to confirm",
        key="delete_all_history_confirm",
    )
    delete_all_disabled = delete_all_confirm.strip() != "DELETE ALL"
    if st.button(
        "🗑 Delete All History",
        type="secondary",
        width="stretch",
        disabled=delete_all_disabled or not all_items_for_counts,
        key="delete_all_history_button",
    ):
        ok, message = delete_all_history_records()
        if ok:
            st.success(message)
            clear_history_cache()
            st.rerun()
        else:
            st.error(message)

st.divider()

if not items:
    st.info("No analyses found for this filter.")
    st.page_link("app.py", label="🚀 Run your first CV analysis")
    st.stop()

for idx, item in enumerate(items, start=1):
    if not isinstance(item, dict):
        continue

    score = item.get("score") or item.get("match_score") or 0
    cv_file = item.get("cv_filename") or item.get("cv_file") or item.get("filename") or item.get("file_name") or "CV"
    created_at = item.get("created_at") or item.get("date") or ""
    strengths = safe_list(item.get("matched_skills") or item.get("strengths") or item.get("matched_keywords"))
    missing = safe_list(item.get("missing_skills") or item.get("missing_keywords") or item.get("weaknesses"))
    recommendations = safe_list(item.get("recommendations"))
    summary = item.get("summary") or ""
    report_text = build_text_report(item)
    report_filename = safe_report_filename(cv_file)
    item_pdf_bytes = build_pdf_report([item], title=f"TalentMatch Pro - {history_label(item)} Report")

    with st.container(border=True):
        render_badge(item)
        top_left, top_mid, top_right = st.columns([2.4, 1, 1])
        with top_left:
            st.subheader(f"{idx}. {cv_file}")
            if created_at:
                st.caption(str(created_at))
        with top_mid:
            st.caption("Score")
            st.markdown(
                f"""
                <div style="font-size:2rem; font-weight:700; color:{score_color(score)};">
                    {score}/100
                </div>
                """,
                unsafe_allow_html=True,
            )
        with top_right:
            st.caption("Type")
            st.metric(label="Status", value=history_label(item))

        if summary:
            st.markdown("**Summary**")
            st.write(summary)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("✅ **Strengths / Matched Skills**")
            if strengths:
                for skill in strengths:
                    st.markdown(f"- {skill}")
            else:
                st.caption("No matched skills saved.")

        with col2:
            st.markdown("❌ **Missing Skills**")
            if missing:
                for skill in missing:
                    st.markdown(f"- {skill}")
            else:
                st.caption("No missing skills saved.")

        if recommendations:
            st.markdown("💡 **Recommendations**")
            for rec in recommendations:
                st.markdown(f"- {rec}")

        st.markdown("---")
        st.markdown("### Download Report")

        report_col1, report_col2 = st.columns(2)

        with report_col1:
            st.download_button(
                label="⬇️ Download Report TXT",
                data=report_text.encode("utf-8"),
                file_name=f"{report_filename}.txt",
                mime="text/plain",
                width="stretch",
                key=f"history_txt_{idx}_{cv_file}_{created_at}",
            )

        with report_col2:
            if is_pro_user():
                st.download_button(
                    label="📄 Download PDF Report",
                    data=item_pdf_bytes or b"PDF export requires reportlab.",
                    file_name=f"{report_filename}.pdf",
                    mime="application/pdf" if item_pdf_bytes else "text/plain",
                    width="stretch",
                    disabled=item_pdf_bytes is None,
                    key=f"history_pdf_{idx}_{cv_file}_{created_at}",
                )
            else:
                st.info("🔒 PDF Report is available in Pro.")
                st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")

        st.markdown("---")
        st.markdown("### Delete History Item")
        record_id = item.get("id")
        if record_id is None:
            st.info("This history item cannot be deleted because it has no record ID.")
        else:
            confirm_key = f"confirm_delete_{record_id}_{idx}"
            button_key = f"delete_history_{record_id}_{idx}"
            confirm_delete = st.checkbox(
                "I understand this will permanently delete this history item.",
                key=confirm_key,
            )
            if st.button(
                "🗑 Delete this history item",
                type="secondary",
                width="stretch",
                disabled=not confirm_delete,
                key=button_key,
            ):
                ok, message = delete_history_record(int(record_id))
                if ok:
                    st.success(message)
                    clear_history_cache()
                    st.rerun()
                else:
                    st.error(message)
