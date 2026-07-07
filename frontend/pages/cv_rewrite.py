from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import streamlit as st

from auth_utils import api_post, is_logged_in
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(page_title="CV Rewrite AI • TalentMatch Pro", page_icon="✍️", layout="wide")
apply_global_styles()
render_sidebar()


DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with PayPal
- Improve product reliability, UX, and deployment pipelines

What we are looking for:
- Strong Python backend fundamentals
- Experience with APIs, auth, databases, and SaaS integrations
- Product mindset and ability to ship independently
- Familiarity with cloud deployment and developer tooling
""".strip()


# ------------------------------------------------------------
# Backend / response helpers
# ------------------------------------------------------------


def extract_error_message(response: Any) -> str:
    """Return a readable backend error message."""
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""

    try:
        payload = response.json()
    except Exception:
        if status_code:
            return f"{status_code}: {text[:1000]}"
        return text[:1000] or "Unknown backend error."

    detail = payload.get("detail") if isinstance(payload, dict) else None
    error = payload.get("error") if isinstance(payload, dict) else None

    if isinstance(detail, dict):
        message = detail.get("message") or str(detail)
    elif detail:
        message = str(detail)
    elif error:
        message = str(error)
    else:
        message = str(payload)

    if status_code:
        return f"{status_code}: {message}"
    return message


# ------------------------------------------------------------
# Data normalization helpers
# ------------------------------------------------------------


def get_list(payload: Dict[str, Any], key: str) -> List[str]:
    value = payload.get(key, [])

    if isinstance(value, list):
        return [str(item) for item in value if item]

    if isinstance(value, str) and value.strip():
        parts = [part.strip() for part in value.replace("\n", ",").split(",")]
        return [part for part in parts if part]

    if value:
        return [str(value)]

    return []


def get_rewrite_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize rewrite result keys into one stable structure."""
    headline = str(
        result.get("headline")
        or result.get("suggested_headline")
        or result.get("new_headline")
        or ""
    )

    rewritten_summary = str(
        result.get("rewritten_summary")
        or result.get("summary")
        or result.get("new_summary")
        or ""
    )

    rewritten_bullets = (
        get_list(result, "rewritten_bullets")
        or get_list(result, "bullet_points")
        or get_list(result, "rewritten_bullet_points")
    )

    keywords = (
        get_list(result, "ats_keywords_to_add")
        or get_list(result, "ats_keywords")
        or get_list(result, "keywords")
        or get_list(result, "keywords_to_add")
    )

    cautions = (
        get_list(result, "cautions")
        or get_list(result, "warnings")
        or get_list(result, "gaps")
    )

    return {
        "headline": headline,
        "rewritten_summary": rewritten_summary,
        "rewritten_bullets": rewritten_bullets,
        "keywords": keywords,
        "cautions": cautions,
    }


# ------------------------------------------------------------
# UI helpers
# ------------------------------------------------------------


def result_card(title: str, content: str, icon: str = "✨") -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="margin-bottom:1rem">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted" style="white-space:pre-wrap">{safe_html(content) if content else 'No content returned.'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def bullet_card(
    title: str,
    items: List[str],
    empty_text: str,
    icon: str = "✅",
    green: bool = False,
) -> None:
    if items:
        pill_class = "tm-pill tm-pill-green" if green else "tm-pill"
        html_items = "".join(f"<span class='{pill_class}'>{safe_html(item)}</span>" for item in items[:80])
    else:
        html_items = f"<div class='tm-muted'>{safe_html(empty_text)}</div>"

    st.markdown(
        f"""
        <div class="tm-card" style="margin-bottom:1rem">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div>{html_items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------
# Export helpers
# ------------------------------------------------------------


def build_text_report(
    result: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> str:
    fields = get_rewrite_fields(result)
    headline = fields["headline"]
    rewritten_summary = fields["rewritten_summary"]
    rewritten_bullets = fields["rewritten_bullets"]
    keywords = fields["keywords"]
    cautions = fields["cautions"]

    report = [
        "TalentMatch Pro - CV Rewrite Report",
        "=" * 42,
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"CV file: {cv_filename}",
        "",
        "Suggested Headline",
        "-" * 20,
        headline or "No headline returned.",
        "",
        "Rewritten Summary",
        "-" * 20,
        rewritten_summary or "No summary returned.",
        "",
        "Rewritten Bullet Points",
        "-" * 20,
    ]

    report.extend([f"- {item}" for item in rewritten_bullets] or ["- No rewritten bullet points returned."])
    report.extend(["", "ATS Keywords to Add", "-" * 20])
    report.extend([f"- {item}" for item in keywords] or ["- No ATS keywords returned."])
    report.extend(["", "Cautions", "-" * 20])
    report.extend([f"- {item}" for item in cautions] or ["- No cautions returned."])
    report.extend(["", "Target Job Description", "-" * 20, job_description])

    return "\n".join(report)


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


def create_pdf_report(
    result: Dict[str, Any],
    cv_filename: str,
    job_description: str,
) -> Optional[bytes]:
    """Create a professional CV Rewrite PDF report locally without re-running backend analysis."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except Exception:
        st.error("PDF export requires ReportLab. Add `reportlab` to frontend requirements.")
        return None

    fields = get_rewrite_fields(result)
    headline = fields["headline"]
    rewritten_summary = fields["rewritten_summary"]
    rewritten_bullets = fields["rewritten_bullets"]
    keywords = fields["keywords"]
    cautions = fields["cautions"]

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

    def paragraph(text: str, fallback: str = "No content returned.") -> None:
        nonlocal y
        ensure_space(25 * mm)
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#1E293B"))
        y = draw_wrapped_lines(
            canvas_obj=pdf,
            text=text or fallback,
            x=x,
            y=y,
            max_width=width - 2 * margin,
            line_height=5.4 * mm,
            font_name="Helvetica",
            font_size=10,
        )
        y -= 2 * mm

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

    # Header
    pdf.setFillColor(colors.HexColor("#2563EB"))
    pdf.roundRect(x, y - 10 * mm, 5 * mm, 5 * mm, 1 * mm, fill=1, stroke=0)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x + 8 * mm, y - 8 * mm, "TalentMatch Pro")

    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - margin, y - 8 * mm, "CV Rewrite AI")

    y -= 24 * mm

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(x, y, "CV Rewrite Report")
    y -= 10 * mm

    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 12)
    y = draw_wrapped_lines(
        canvas_obj=pdf,
        text="AI-generated CV rewrite output with role-aligned headline, summary, bullet points and ATS keyword suggestions.",
        x=x,
        y=y,
        max_width=width - 2 * margin,
        line_height=6 * mm,
        font_name="Helvetica",
        font_size=12,
    )

    y -= 8 * mm

    # Summary card
    card_h = 34 * mm
    pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.roundRect(x, y - card_h, width - 2 * margin, card_h, 4 * mm, fill=1, stroke=1)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(x + 8 * mm, y - 13 * mm, "Rewrite Ready" if headline or rewritten_summary else "Rewrite Output")

    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.drawString(x + 8 * mm, y - 22 * mm, f"CV file: {cv_filename}")
    pdf.drawString(x + 8 * mm, y - 30 * mm, f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    pdf.drawRightString(width - margin - 8 * mm, y - 13 * mm, f"Bullet points: {len(rewritten_bullets)}")
    pdf.drawRightString(width - margin - 8 * mm, y - 22 * mm, f"ATS keywords: {len(keywords)}")
    pdf.drawRightString(width - margin - 8 * mm, y - 31 * mm, f"Cautions: {len(cautions)}")

    y -= card_h + 14 * mm

    section_title("Suggested Headline")
    paragraph(headline, "No headline returned.")

    y -= 2 * mm
    section_title("Rewritten Summary")
    paragraph(rewritten_summary, "No rewritten summary returned.")

    y -= 2 * mm
    section_title("Rewritten Bullet Points")
    bullet_list(rewritten_bullets, "No rewritten bullet points returned.")

    y -= 2 * mm
    section_title("ATS Keywords to Add")
    bullet_list(keywords, "No ATS keywords returned.")

    y -= 2 * mm
    section_title("Cautions")
    bullet_list(cautions, "No cautions returned.")

    y -= 2 * mm
    section_title("Target Job Description")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#1E293B"))

    for line in str(job_description).splitlines():
        ensure_space(25 * mm)
        if not line.strip():
            y -= 4 * mm
            continue

        y = draw_wrapped_lines(
            canvas_obj=pdf,
            text=line,
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


# ------------------------------------------------------------
# Session state helpers
# ------------------------------------------------------------


def clear_cv_rewrite_state() -> None:
    for key in [
        "rewrite_result",
        "cv_rewrite_filename",
        "cv_rewrite_job_description",
        "cv_rewrite_txt_report",
        "cv_rewrite_pdf_report",
    ]:
        st.session_state.pop(key, None)


# ------------------------------------------------------------
# Result renderer
# ------------------------------------------------------------


def render_rewrite_result(result: Dict[str, Any]) -> None:
    fields = get_rewrite_fields(result)
    headline = fields["headline"]
    rewritten_summary = fields["rewritten_summary"]
    rewritten_bullets = fields["rewritten_bullets"]
    keywords = fields["keywords"]
    cautions = fields["cautions"]

    cv_filename = st.session_state.get("cv_rewrite_filename", "uploaded_cv.pdf")
    job_description = st.session_state.get("cv_rewrite_job_description", "")

    st.success("CV rewrite completed.")

    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("Headline", "Ready" if headline else "Missing")
    with k2:
        st.metric("Bullet points", len(rewritten_bullets))
    with k3:
        st.metric("ATS keywords", len(keywords))

    st.markdown('<div class="tm-section-title">Rewrite output</div>', unsafe_allow_html=True)
    result_card("Suggested headline", headline, "🎯")
    result_card("Rewritten summary", rewritten_summary, "📝")

    if rewritten_bullets:
        bullet_html = "".join(
            f"<li style='margin-bottom:.55rem'>{safe_html(item)}</li>" for item in rewritten_bullets
        )
        st.markdown(
            f"""
            <div class="tm-card" style="margin-bottom:1rem">
                <div class="tm-card-title">✅ Rewritten bullet points</div>
                <ul class="tm-muted" style="padding-left:1.2rem">{bullet_html}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No rewritten bullet points returned.")

    left, right = st.columns(2)
    with left:
        bullet_card("ATS keywords to add", keywords, "No keyword suggestions returned.", "🔎", green=True)
    with right:
        bullet_card("Cautions", cautions, "No cautions returned.", "⚠️", green=False)

    if "cv_rewrite_txt_report" not in st.session_state:
        st.session_state["cv_rewrite_txt_report"] = build_text_report(
            result=result,
            cv_filename=cv_filename,
            job_description=job_description,
        )

    st.markdown("---")
    st.markdown('<div class="tm-section-title">Download Report</div>', unsafe_allow_html=True)

    col_txt, col_pdf = st.columns(2)

    with col_txt:
        st.download_button(
            "📥 Export Rewrite (.txt)",
            data=st.session_state["cv_rewrite_txt_report"].encode("utf-8"),
            file_name="talentmatch_cv_rewrite.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_pdf:
        if "cv_rewrite_pdf_report" not in st.session_state:
            with st.spinner("Preparing PDF report..."):
                st.session_state["cv_rewrite_pdf_report"] = create_pdf_report(
                    result=result,
                    cv_filename=cv_filename,
                    job_description=job_description,
                )

        pdf_bytes = st.session_state.get("cv_rewrite_pdf_report")
        if pdf_bytes:
            st.download_button(
                "📄 Export Rewrite (.pdf)",
                data=pdf_bytes,
                file_name="talentmatch_cv_rewrite_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


# ------------------------------------------------------------
# Page
# ------------------------------------------------------------


render_hero(
    "AI CV rewriting",
    "CV Rewrite AI",
    "Turn your CV into a sharper, role-aligned version with stronger summary, bullet points and ATS keyword suggestions.",
    "✍️",
)

if not is_logged_in():
    st.warning("Please login before using CV Rewrite AI.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

st.markdown('<div class="tm-section-title">Create a tailored rewrite</div>', unsafe_allow_html=True)
left, right = st.columns([1, 1.25])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📄 CV upload</div>
            <div class="tm-muted">Upload your PDF CV. The AI will rewrite your positioning for the target job.</div>
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
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.success(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

with right:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🧾 Target job description</div>
            <div class="tm-muted">Paste the job ad so the rewrite can match the exact role, skills and language.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    job_description = st.text_area(
        "Job Description",
        value=DEFAULT_JOB_DESCRIPTION,
        height=330,
    )

if st.button("🚀 Rewrite CV", use_container_width=True):
    if uploaded_file is None:
        st.error("Please upload a PDF CV.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    clear_cv_rewrite_state()

    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    data = {"job_description": job_description.strip()}

    with st.spinner("Rewriting CV content..."):
        response = api_post("/rewrite-cv", data=data, files=files, timeout=180)

    if getattr(response, "status_code", None) != 200:
        st.error(f"CV rewrite failed: {extract_error_message(response)}")
        if getattr(response, "status_code", None) == 403:
            st.warning("🚀 CV Rewrite AI is a Pro feature.")
            st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="🚀")
        st.stop()

    try:
        payload = response.json()
    except Exception:
        st.error(f"Backend returned invalid JSON: {getattr(response, 'text', '')[:1000]}")
        st.stop()

    if not isinstance(payload, dict):
        st.error("Backend returned invalid response format.")
        st.json(payload)
        st.stop()

    st.session_state["rewrite_result"] = payload
    st.session_state["cv_rewrite_filename"] = uploaded_file.name
    st.session_state["cv_rewrite_job_description"] = job_description.strip()

result = st.session_state.get("rewrite_result")
if isinstance(result, dict):
    st.divider()
    render_rewrite_result(result)
