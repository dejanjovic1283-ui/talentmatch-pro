from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from auth_utils import api_post, is_logged_in, is_pro_user
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(page_title="Semantic Match • TalentMatch Pro", page_icon="🧠", layout="wide")
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


def normalize_response(raw: Any) -> Tuple[Optional[Any], Optional[str]]:
    if isinstance(raw, tuple):
        if len(raw) >= 2:
            return raw[0], raw[1]
        if len(raw) == 1:
            return raw[0], None
        return None, "Empty response from backend."
    return raw, None


def response_to_json(response: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if response is None:
        return None, "No response from backend."

    if isinstance(response, dict):
        return response, None

    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""

    if status_code is not None and status_code >= 400:
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("error") or payload
        except Exception:
            detail = text[:1000]
        return None, f"Semantic Match failed: {status_code} - {detail}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    if not isinstance(payload, dict):
        return None, "Backend response is not a JSON object."

    if payload.get("error") or payload.get("detail"):
        return None, str(payload.get("error") or payload.get("detail"))

    return payload, None


def normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace("\n", ",").split(",")]
        return [part for part in parts if part]
    return [str(value)]


def get_score(data: Dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        value = data.get(key)
        if value is not None:
            try:
                return max(0, min(int(float(str(value).replace("%", "").strip())), 100))
            except Exception:
                continue
    return default


def get_verdict(score: int, existing: str = "") -> str:
    if existing:
        return existing
    if score >= 80:
        return "Strong Semantic Match"
    if score >= 60:
        return "Good Semantic Match"
    return "Weak Semantic Match"


def draw_wrapped_lines(canvas_obj: Any, text: str, x: float, y: float, max_width: float, line_height: float, font_name: str, font_size: int) -> float:
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


def build_text_report(data: Dict[str, Any], cv_filename: str, job_description: str) -> str:
    combined_score = get_score(data, "combined_score", "score", "match_score")
    semantic_score = get_score(data, "semantic_score")
    keyword_score = get_score(data, "keyword_score")
    verdict = get_verdict(combined_score, str(data.get("verdict") or ""))
    summary = str(data.get("summary") or data.get("recruiter_summary") or "Semantic match completed.")

    matched_themes = normalize_list(data.get("matched_themes") or data.get("strengths"))
    missing_themes = normalize_list(data.get("missing_themes") or data.get("weaknesses"))
    matched_keywords = normalize_list(data.get("matched_keywords"))
    missing_keywords = normalize_list(data.get("missing_keywords"))
    recommendations = normalize_list(data.get("recommendations"))

    lines = [
        "TalentMatch Pro - Semantic Match Report",
        "=" * 44,
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"CV file: {cv_filename}",
        f"Combined Score: {combined_score}/100",
        f"Semantic Score: {semantic_score}/100",
        f"Keyword Score: {keyword_score}/100",
        f"Verdict: {verdict}",
        "",
        "Recruiter Summary",
        "-" * 24,
        summary,
        "",
        "Matched Themes",
        "-" * 24,
    ]
    lines.extend([f"- {item}" for item in matched_themes] or ["- No matched themes returned."])
    lines.extend(["", "Missing Themes", "-" * 24])
    lines.extend([f"- {item}" for item in missing_themes] or ["- No missing themes returned."])
    lines.extend(["", "Matched Keywords", "-" * 24])
    lines.extend([f"- {item}" for item in matched_keywords] or ["- No matched keywords returned."])
    lines.extend(["", "Missing Keywords", "-" * 24])
    lines.extend([f"- {item}" for item in missing_keywords] or ["- No missing keywords returned."])
    lines.extend(["", "Recommendations", "-" * 24])
    lines.extend([f"- {item}" for item in recommendations] or ["- No recommendations returned."])
    lines.extend(["", "Job Description", "-" * 24, job_description])

    return "\n".join(lines)


def create_pdf_report(data: Dict[str, Any], cv_filename: str, job_description: str) -> Optional[bytes]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except Exception:
        st.error("PDF export requires ReportLab. Add `reportlab` to frontend requirements.")
        return None

    combined_score = get_score(data, "combined_score", "score", "match_score")
    semantic_score = get_score(data, "semantic_score")
    keyword_score = get_score(data, "keyword_score")
    verdict = get_verdict(combined_score, str(data.get("verdict") or ""))
    summary = str(data.get("summary") or data.get("recruiter_summary") or "Semantic match completed.")

    matched_themes = normalize_list(data.get("matched_themes") or data.get("strengths"))
    missing_themes = normalize_list(data.get("missing_themes") or data.get("weaknesses"))
    matched_keywords = normalize_list(data.get("matched_keywords"))
    missing_keywords = normalize_list(data.get("missing_keywords"))
    recommendations = normalize_list(data.get("recommendations"))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    x = margin
    y = height - margin

    def footer_new_page() -> None:
        nonlocal y
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.HexColor("#64748B"))
        pdf.drawString(margin, 12 * mm, "Generated by TalentMatch Pro")
        pdf.drawRightString(width - margin, 12 * mm, f"Page {pdf.getPageNumber()}")
        pdf.showPage()
        y = height - margin

    def ensure_space(required: float = 35 * mm) -> None:
        if y < required:
            footer_new_page()

    def section(title: str) -> None:
        nonlocal y
        ensure_space(28 * mm)
        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(x, y, title)
        y -= 10 * mm

    def paragraph(text: str, font_size: int = 10) -> None:
        nonlocal y
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(colors.HexColor("#1E293B"))
        for raw_line in str(text).splitlines() or [""]:
            ensure_space(22 * mm)
            if not raw_line.strip():
                y -= 4 * mm
                continue
            y = draw_wrapped_lines(pdf, raw_line, x, y, width - 2 * margin, 5.4 * mm, "Helvetica", font_size)
            y -= 1.5 * mm

    def bullets(items: List[str], fallback: str) -> None:
        nonlocal y
        values = items if items else [fallback]
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#1E293B"))
        for item in values:
            ensure_space(24 * mm)
            pdf.drawString(x + 4 * mm, y, "•")
            y = draw_wrapped_lines(pdf, item, x + 10 * mm, y, width - 2 * margin - 10 * mm, 5.4 * mm, "Helvetica", 10)
            y -= 1.5 * mm

    pdf.setFillColor(colors.HexColor("#2563EB"))
    pdf.roundRect(x, y - 10 * mm, 5 * mm, 5 * mm, 1 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x + 8 * mm, y - 8 * mm, "TalentMatch Pro")
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - margin, y - 8 * mm, "Semantic Match")
    y -= 24 * mm

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(x, y, "Semantic Match Report")
    y -= 11 * mm

    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 11)
    pdf.drawString(x, y, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    pdf.drawRightString(width - margin, y, f"CV file: {cv_filename}")
    y -= 12 * mm

    card_h = 36 * mm
    pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.roundRect(x, y - card_h, width - 2 * margin, card_h, 4 * mm, fill=1, stroke=1)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawString(x + 8 * mm, y - 17 * mm, f"{combined_score}/100")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x + 50 * mm, y - 13 * mm, verdict)
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.drawString(x + 50 * mm, y - 22 * mm, f"Semantic: {semantic_score}/100")
    pdf.drawString(x + 50 * mm, y - 30 * mm, f"Keyword: {keyword_score}/100")
    pdf.drawRightString(width - margin - 8 * mm, y - 17 * mm, f"Matched keywords: {len(matched_keywords)}")
    pdf.drawRightString(width - margin - 8 * mm, y - 27 * mm, f"Missing keywords: {len(missing_keywords)}")
    y -= card_h + 14 * mm

    section("Recruiter Summary")
    paragraph(summary)

    section("Matched Themes")
    bullets(matched_themes, "No matched themes returned.")

    section("Missing Themes")
    bullets(missing_themes, "No missing themes returned.")

    section("Matched Keywords")
    bullets(matched_keywords, "No matched keywords returned.")

    section("Missing Keywords")
    bullets(missing_keywords, "No missing keywords returned.")

    section("Recommendations")
    bullets(recommendations, "No recommendations returned.")

    section("Job Description")
    paragraph(job_description)

    footer_new_page()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def clear_semantic_state() -> None:
    for key in [
        "semantic_result",
        "semantic_filename",
        "semantic_job_description",
        "semantic_txt_report",
        "semantic_pdf_report",
    ]:
        st.session_state.pop(key, None)


def render_list_card(title: str, items: List[str], icon: str, green: bool = False) -> None:
    pill_class = "tm-pill tm-pill-green" if green else "tm-pill"
    if items:
        chips = "".join(f"<span class='{pill_class}'>{safe_html(item)}</span>" for item in items[:40])
    else:
        chips = "<div class='tm-muted'>No items returned.</div>"

    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div>{chips}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results(data: Dict[str, Any]) -> None:
    cv_filename = st.session_state.get("semantic_filename", "uploaded_cv.pdf")
    job_description = st.session_state.get("semantic_job_description", "")

    combined_score = get_score(data, "combined_score", "score", "match_score")
    semantic_score = get_score(data, "semantic_score")
    keyword_score = get_score(data, "keyword_score")
    verdict = get_verdict(combined_score, str(data.get("verdict") or ""))
    summary = str(data.get("summary") or data.get("recruiter_summary") or "Semantic match completed.")

    matched_themes = normalize_list(data.get("matched_themes") or data.get("strengths"))
    missing_themes = normalize_list(data.get("missing_themes") or data.get("weaknesses"))
    matched_keywords = normalize_list(data.get("matched_keywords"))
    missing_keywords = normalize_list(data.get("missing_keywords"))
    recommendations = normalize_list(data.get("recommendations"))

    st.success("Semantic match completed.")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Combined Score", f"{combined_score}/100", verdict)
    with col2:
        st.metric("Semantic Score", f"{semantic_score}/100")
    with col3:
        st.metric("Keyword Score", f"{keyword_score}/100")

    st.progress(combined_score)

    st.markdown('<div class="tm-section-title">Recruiter Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-muted">{safe_html(summary)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="tm-section-title">Semantic Coverage</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        render_list_card("Matched themes", matched_themes, "✅", green=True)
        render_list_card("Matched keywords", matched_keywords, "🔎", green=True)
    with right:
        render_list_card("Missing themes", missing_themes, "⚠️")
        render_list_card("Missing keywords", missing_keywords, "🎯")

    st.markdown('<div class="tm-section-title">Recommendations</div>', unsafe_allow_html=True)
    if recommendations:
        for index, item in enumerate(recommendations, start=1):
            st.markdown(
                f"""
                <div class="tm-card" style="margin-bottom:.75rem">
                    <div class="tm-kicker">Recommendation {index}</div>
                    <div class="tm-muted">{safe_html(item)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No recommendations returned.")

    if "semantic_txt_report" not in st.session_state:
        st.session_state["semantic_txt_report"] = build_text_report(data, cv_filename, job_description)

    st.markdown("---")
    st.markdown('<div class="tm-section-title">Download Report</div>', unsafe_allow_html=True)

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
            with st.spinner("Preparing PDF report..."):
                st.session_state["semantic_pdf_report"] = create_pdf_report(data, cv_filename, job_description)

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
    "Semantic Match",
    "Semantic Match",
    "Compare your CV with AI-powered semantic matching.",
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

st.markdown('<div class="tm-section-title">Run a new semantic match</div>', unsafe_allow_html=True)

left, right = st.columns([1, 1.25])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📄 CV upload</div>
            <div class="tm-muted">Upload one PDF CV. TalentMatch Pro compares meaning, role alignment and keyword fit.</div>
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
            <div class="tm-muted">Paste the full job ad for the most accurate semantic and keyword scoring.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    job_description = st.text_area("Job Description", value=DEFAULT_JOB_DESCRIPTION, height=330)

run_clicked = st.button(
    "🚀 Run Semantic Match",
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

    clear_semantic_state()

    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    data = {"job_description": job_description.strip()}

    with st.spinner("Running semantic match..."):
        raw_response = api_post("/semantic-match", data=data, files=files, timeout=180)

    response, call_error = normalize_response(raw_response)
    if call_error:
        st.error(f"Semantic Match failed: {call_error}")
        st.stop()

    payload, parse_error = response_to_json(response)
    if parse_error:
        st.error(parse_error)
        st.stop()

    if not payload:
        st.error("Semantic Match failed: empty backend response.")
        st.stop()

    st.session_state["semantic_result"] = payload
    st.session_state["semantic_filename"] = uploaded_file.name
    st.session_state["semantic_job_description"] = job_description.strip()

result = st.session_state.get("semantic_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
