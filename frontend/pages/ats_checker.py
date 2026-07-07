from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from auth_utils import api_post, is_logged_in
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(page_title="ATS Checker • TalentMatch Pro", page_icon="📋", layout="wide")
apply_global_styles()
render_sidebar()


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


def normalize_response(raw: Any) -> Tuple[Optional[Any], Optional[str]]:
    """Normalize different api_post return formats into response and error."""
    if isinstance(raw, tuple):
        if len(raw) >= 2:
            return raw[0], raw[1]
        if len(raw) == 1:
            return raw[0], None
        return None, "Empty response from backend."
    return raw, None


def response_to_json(response: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Convert backend response into a JSON dictionary with clear error messages."""
    if response is None:
        return None, "No response from backend."

    if isinstance(response, dict):
        return response, None

    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "")

    if status_code is not None and status_code >= 400:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload.get("error") or payload
            else:
                detail = payload
            return None, f"ATS check failed: {status_code} - {detail}"
        except Exception:
            return None, f"ATS check failed: {status_code} - {text[:1000]}"

    if content_type and "application/json" not in content_type:
        return None, f"Backend returned non-JSON response: {text[:1000]}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    if not isinstance(payload, dict):
        return None, "Backend response is not a JSON object."

    if payload.get("error") or payload.get("detail"):
        return None, str(payload.get("error") or payload.get("detail"))

    return payload, None


def extract_list(data: Dict[str, Any], *keys: str) -> List[str]:
    """Extract a string list from the first existing key."""
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if isinstance(value, str) and value.strip():
            parts = [part.strip() for part in value.replace("\n", ",").split(",")]
            return [part for part in parts if part]
    return []


def score_level(score: Any) -> tuple[str, str, int]:
    if score is None:
        return "Not scored", "No numeric score returned", 0

    try:
        numeric_score = int(float(str(score).replace("%", "").strip()))
    except (TypeError, ValueError):
        return "Not scored", "No numeric score returned", 0

    numeric_score = max(0, min(numeric_score, 100))
    if numeric_score >= 85:
        return "Excellent", "Strong match for this job description", numeric_score
    if numeric_score >= 70:
        return "Good", "Solid match with a few keyword gaps", numeric_score
    if numeric_score >= 50:
        return "Needs polish", "Improve missing keywords and role alignment", numeric_score
    return "Weak match", "Rewrite CV sections before applying", numeric_score


def render_keyword_group(title: str, items: List[str], empty_text: str, icon: str, green: bool = False) -> None:
    pill_class = "tm-pill tm-pill-green" if green else "tm-pill"
    if items:
        chips = "".join(f"<span class='{pill_class}'>{safe_html(item)}</span>" for item in items[:50])
    else:
        chips = f"<div class='tm-muted'>{safe_html(empty_text)}</div>"

    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div>{chips}</div>
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
            <div class="tm-card" style="margin-bottom:.75rem">
                <div class="tm-kicker">Recommendation {index}</div>
                <div class="tm-muted">{safe_html(item)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_text_report(data: Dict[str, Any], cv_filename: str, job_description: str) -> str:
    matched_keywords = extract_list(data, "matched_keywords", "matched", "found_keywords", "strengths")
    missing_keywords = extract_list(data, "missing_keywords", "missing", "missing_skills")
    recommendations = extract_list(data, "recommendations", "tips", "suggestions")
    score = data.get("score") or data.get("match_score") or data.get("ats_score")
    label, _message, numeric_score = score_level(score)

    report_lines = [
        "TalentMatch Pro - ATS Keyword Checker",
        "=" * 42,
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"CV file: {cv_filename}",
        "",
        f"ATS Score: {numeric_score if score is not None else 'N/A'}",
        f"Result: {label}",
        "",
        "Matched Keywords:",
        *[f"- {item}" for item in matched_keywords],
        "",
        "Missing Keywords:",
        *[f"- {item}" for item in missing_keywords],
        "",
        "Recommendations:",
        *[f"- {item}" for item in recommendations],
        "",
        "Job Description:",
        job_description,
    ]

    return "\n".join(report_lines)


def draw_wrapped_lines(
    canvas_obj: Any,
    text: str,
    x: float,
    y: float,
    max_width: float,
    line_height: float,
    font_name: str,
    font_size: int,
) -> float:
    words = str(text).split()
    if not words:
        return y - line_height

    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if canvas_obj.stringWidth(candidate, font_name, font_size) <= max_width:
            line = candidate
            continue

        canvas_obj.drawString(x, y, line)
        y -= line_height
        line = word

    if line:
        canvas_obj.drawString(x, y, line)
        y -= line_height

    return y


def create_pdf_report(data: Dict[str, Any], cv_filename: str, job_description: str) -> Optional[bytes]:
    """Create ATS PDF report locally without re-running backend analysis."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except Exception:
        st.error("PDF export requires ReportLab. Add `reportlab` to frontend requirements.")
        return None

    matched_keywords = extract_list(data, "matched_keywords", "matched", "found_keywords", "strengths")
    missing_keywords = extract_list(data, "missing_keywords", "missing", "missing_skills")
    recommendations = extract_list(data, "recommendations", "tips", "suggestions")
    score = data.get("score") or data.get("match_score") or data.get("ats_score")
    label, message, numeric_score = score_level(score)

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    margin = 18 * mm
    x = margin
    y = height - margin

    def add_footer_and_new_page() -> None:
        nonlocal y
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.HexColor("#64748B"))
        pdf.drawString(margin, 12 * mm, "Generated by TalentMatch Pro")
        pdf.drawRightString(width - margin, 12 * mm, f"Page {pdf.getPageNumber()}")
        pdf.showPage()
        y = height - margin

    def ensure_space(required: float = 35 * mm) -> None:
        if y < required:
            add_footer_and_new_page()

    def section_title(title: str) -> None:
        nonlocal y
        ensure_space(28 * mm)
        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(x, y, title)
        y -= 10 * mm

    def bullet_list(items: List[str], fallback: str) -> None:
        nonlocal y
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#1E293B"))

        values = items if items else [fallback]
        for item in values:
            ensure_space(25 * mm)
            pdf.setFont("Helvetica", 10)
            pdf.drawString(x + 4 * mm, y, "•")
            y = draw_wrapped_lines(
                canvas_obj=pdf,
                text=item,
                x=x + 10 * mm,
                y=y,
                max_width=width - (2 * margin) - 10 * mm,
                line_height=5.4 * mm,
                font_name="Helvetica",
                font_size=10,
            )
            y -= 1.5 * mm

    pdf.setFillColor(colors.HexColor("#2563EB"))
    pdf.roundRect(x, y - 10 * mm, 5 * mm, 5 * mm, 1 * mm, fill=1, stroke=0)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x + 8 * mm, y - 8 * mm, "TalentMatch Pro")

    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - margin, y - 8 * mm, "ATS Keyword Checker")

    y -= 24 * mm

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(x, y, "ATS Checker Report")
    y -= 10 * mm

    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 12)
    y = draw_wrapped_lines(
        canvas_obj=pdf,
        text="AI-powered ATS keyword coverage report for CV optimization and role alignment.",
        x=x,
        y=y,
        max_width=width - 2 * margin,
        line_height=6 * mm,
        font_name="Helvetica",
        font_size=12,
    )

    y -= 8 * mm

    card_h = 34 * mm
    pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.roundRect(x, y - card_h, width - 2 * margin, card_h, 4 * mm, fill=1, stroke=1)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(x + 8 * mm, y - 17 * mm, f"{numeric_score}%")

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x + 42 * mm, y - 13 * mm, label)

    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.drawString(x + 42 * mm, y - 21 * mm, message)
    pdf.drawString(x + 42 * mm, y - 29 * mm, f"CV file: {cv_filename}")

    pdf.drawRightString(width - margin - 8 * mm, y - 13 * mm, f"Matched: {len(matched_keywords)}")
    pdf.drawRightString(width - margin - 8 * mm, y - 22 * mm, f"Missing: {len(missing_keywords)}")
    pdf.drawRightString(width - margin - 8 * mm, y - 31 * mm, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    y -= card_h + 14 * mm

    section_title("Matched Keywords")
    bullet_list(matched_keywords, "No matched keywords returned.")

    y -= 3 * mm
    section_title("Missing Keywords")
    bullet_list(missing_keywords, "No missing keywords found.")

    y -= 3 * mm
    section_title("Recommendations")
    bullet_list(recommendations, "No recommendations returned.")

    y -= 3 * mm
    section_title("Job Description")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#1E293B"))

    for paragraph in str(job_description).splitlines():
        ensure_space(25 * mm)
        if not paragraph.strip():
            y -= 4 * mm
            continue

        y = draw_wrapped_lines(
            canvas_obj=pdf,
            text=paragraph,
            x=x,
            y=y,
            max_width=width - 2 * margin,
            line_height=5.4 * mm,
            font_name="Helvetica",
            font_size=10,
        )
        y -= 1.5 * mm

    add_footer_and_new_page()
    pdf.save()

    buffer.seek(0)
    return buffer.getvalue()


def clear_ats_state() -> None:
    for key in [
        "ats_checker_result",
        "ats_checker_filename",
        "ats_checker_job_description",
        "ats_checker_txt_report",
        "ats_checker_pdf_report",
    ]:
        st.session_state.pop(key, None)


def render_results(data: Dict[str, Any]) -> None:
    matched_keywords = extract_list(data, "matched_keywords", "matched", "found_keywords", "strengths")
    missing_keywords = extract_list(data, "missing_keywords", "missing", "missing_skills")
    recommendations = extract_list(data, "recommendations", "tips", "suggestions")
    score = data.get("score") or data.get("match_score") or data.get("ats_score")
    label, message, numeric_score = score_level(score)

    cv_filename = st.session_state.get("ats_checker_filename", "uploaded_cv.pdf")
    job_description = st.session_state.get("ats_checker_job_description", "")

    st.success("ATS check completed.")

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("ATS Score", f"{numeric_score}%" if score is not None else "N/A", label)
    with m2:
        st.metric("Matched keywords", len(matched_keywords))
    with m3:
        st.metric("Missing keywords", len(missing_keywords))

    st.progress(numeric_score)
    st.caption(message)

    st.markdown('<div class="tm-section-title">ATS Coverage</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        render_keyword_group(
            "Matched keywords",
            matched_keywords,
            "No matched keywords returned.",
            "✅",
            green=True,
        )
    with col2:
        render_keyword_group(
            "Missing keywords",
            missing_keywords,
            "No missing keywords found.",
            "🎯",
            green=False,
        )

    st.markdown('<div class="tm-section-title">AI Improvements</div>', unsafe_allow_html=True)
    render_recommendations(recommendations)

    if "ats_checker_txt_report" not in st.session_state:
        st.session_state["ats_checker_txt_report"] = build_text_report(
            data=data,
            cv_filename=cv_filename,
            job_description=job_description,
        )

    st.markdown("---")
    st.markdown('<div class="tm-section-title">Download Report</div>', unsafe_allow_html=True)

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
            with st.spinner("Preparing PDF report..."):
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
    "ATS Checker",
    "ATS Checker",
    "Optimize your CV before every application.",
    "📋",
)

if not is_logged_in():
    st.warning("Please login before using ATS Checker.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

st.markdown('<div class="tm-section-title">Run a new ATS check</div>', unsafe_allow_html=True)
left, right = st.columns([1, 1.25])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📄 CV upload</div>
            <div class="tm-muted">Use a PDF version of your CV. The checker compares your content with the job description.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader("Upload CV (PDF)", type=["pdf"])

    if uploaded_file is not None:
        st.success(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

with right:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🧾 Job description</div>
            <div class="tm-muted">Paste the full job ad for the best keyword coverage analysis.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    job_description = st.text_area(
        "Job Description",
        height=310,
        placeholder=EXAMPLE_JOB_DESCRIPTION,
    )

run_clicked = st.button(
    "🚀 Analyze ATS Match",
    use_container_width=True,
    disabled=uploaded_file is None or not job_description.strip(),
)

if run_clicked:
    if uploaded_file is None:
        st.error("Please upload your CV as a PDF.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste the job description.")
        st.stop()

    clear_ats_state()

    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    data = {"job_description": job_description.strip()}

    with st.spinner("Running ATS keyword check..."):
        raw_response = api_post("/ats-test", data=data, files=files)

    response, call_error = normalize_response(raw_response)
    if call_error:
        st.error(f"ATS check failed: {call_error}")
        st.stop()

    payload, parse_error = response_to_json(response)
    if parse_error:
        st.error(parse_error)
        st.stop()

    if not payload:
        st.error("ATS check failed: empty backend response.")
        st.stop()

    st.session_state["ats_checker_result"] = payload
    st.session_state["ats_checker_filename"] = uploaded_file.name
    st.session_state["ats_checker_job_description"] = job_description.strip()

result = st.session_state.get("ats_checker_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
