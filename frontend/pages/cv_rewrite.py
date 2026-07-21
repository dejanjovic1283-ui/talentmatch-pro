from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import streamlit as st

from auth_utils import api_post, is_logged_in
from components.sidebar import render_sidebar
from components.ui import (
    apply_global_styles,
    render_action_panel,
    render_list_cards,
    render_page_intro,
    render_report_panel,
    render_score_card,
    safe_html,
)


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


def render_content_panel(
    *,
    eyebrow: str,
    title: str,
    content: str,
    icon: str,
    empty_message: str,
) -> None:
    """Render one escaped long-form rewrite output panel."""
    normalized = str(content or "").strip()
    display_value = normalized or empty_message

    st.markdown(
        f"""
        <div class="tm-card" style="margin-bottom:1rem">
            <div class="tm-eyebrow">{safe_html(eyebrow)}</div>
            <div class="tm-card-title" style="margin-top:.35rem">
                {safe_html(icon)} {safe_html(title)}
            </div>
            <div class="tm-muted" style="white-space:pre-wrap; margin-top:.75rem">
                {safe_html(display_value)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_numbered_rewrite_cards(items: List[str]) -> None:
    """Render rewritten CV bullets as numbered, recruiter-readable cards."""
    normalized_items = [str(item).strip() for item in items if str(item).strip()]
    if not normalized_items:
        st.info("No rewritten bullet points were returned.")
        return

    for index, item in enumerate(normalized_items, start=1):
        st.markdown(
            f"""
            <div class="tm-card" style="margin-bottom:.85rem">
                <div style="display:flex; gap:1rem; align-items:flex-start">
                    <div style="
                        min-width:3rem;
                        width:3rem;
                        height:3rem;
                        border-radius:1rem;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        background:rgba(37,99,235,.10);
                        color:#2563eb;
                        font-weight:800;
                    ">
                        {index}
                    </div>
                    <div style="flex:1">
                        <div class="tm-eyebrow">REWRITTEN BULLET {index}</div>
                        <div class="tm-muted" style="margin-top:.45rem">
                            {safe_html(item)}
                        </div>
                    </div>
                </div>
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
    """Render a completed CV Rewrite response in the shared PROFI-EXTRA system."""
    fields = get_rewrite_fields(result)
    headline = str(fields["headline"] or "").strip()
    rewritten_summary = str(fields["rewritten_summary"] or "").strip()
    rewritten_bullets = list(fields["rewritten_bullets"])
    keywords = list(fields["keywords"])
    cautions = list(fields["cautions"])

    cv_filename = str(
        st.session_state.get("cv_rewrite_filename", "uploaded_cv.pdf")
    )
    job_description = str(
        st.session_state.get("cv_rewrite_job_description", "")
    )

    st.success("CV rewrite completed successfully and saved to History.")

    st.markdown("## Rewrite intelligence")
    st.caption(
        "A recruiter-ready overview of the rewritten positioning, ATS enrichment, "
        "and final quality checks."
    )

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    with metric_1:
        render_score_card(
            label="HEADLINE",
            value="READY" if headline else "MISSING",
            caption="Role-aligned positioning",
            tone="primary",
            suffix="",
        )
    with metric_2:
        render_score_card(
            label="BULLETS",
            value=len(rewritten_bullets),
            caption="Rewritten experience points",
            tone="success",
            suffix="",
        )
    with metric_3:
        render_score_card(
            label="ATS KEYWORDS",
            value=len(keywords),
            caption="Suggested additions",
            tone="primary",
            suffix="",
        )
    with metric_4:
        render_score_card(
            label="CAUTIONS",
            value=len(cautions),
            caption="Items requiring review",
            tone="warning",
            suffix="",
        )

    st.markdown("## Positioning upgrade")
    st.caption(
        "Use the suggested headline and summary as the primary narrative for the target role."
    )

    render_content_panel(
        eyebrow="TARGET POSITIONING",
        title="Suggested headline",
        content=headline,
        icon="🎯",
        empty_message="No suggested headline was returned.",
    )
    render_content_panel(
        eyebrow="PROFESSIONAL SUMMARY",
        title="Rewritten summary",
        content=rewritten_summary,
        icon="📝",
        empty_message="No rewritten summary was returned.",
    )

    st.markdown("## Rewritten experience")
    st.caption(
        "Review each bullet for factual accuracy before replacing content in the source CV."
    )
    render_numbered_rewrite_cards(rewritten_bullets)

    st.markdown("## ATS enrichment and review")
    st.caption(
        "Add only truthful keywords and resolve every caution before submitting the CV."
    )

    left, right = st.columns(2)
    with left:
        st.markdown("### ✅ ATS keywords to add")
        render_list_cards(
            keywords,
            kind="success",
            empty_message="No ATS keyword suggestions were returned.",
        )
    with right:
        st.markdown("### ⚠️ Cautions")
        render_list_cards(
            cautions,
            kind="warning",
            empty_message="No cautions were returned.",
        )

    if "cv_rewrite_txt_report" not in st.session_state:
        st.session_state["cv_rewrite_txt_report"] = build_text_report(
            result=result,
            cv_filename=cv_filename,
            job_description=job_description,
        )

    if "cv_rewrite_pdf_report" not in st.session_state:
        with st.spinner("Preparing PDF report..."):
            st.session_state["cv_rewrite_pdf_report"] = create_pdf_report(
                result=result,
                cv_filename=cv_filename,
                job_description=job_description,
            )

    st.divider()
    render_report_panel(
        title="CV Rewrite report center",
        description=(
            "Export the suggested headline, rewritten summary, experience bullets, "
            "ATS keyword additions, cautions, and the bounded Job Description appendix."
        ),
        icon="📥",
    )

    col_txt, col_pdf = st.columns(2)
    with col_txt:
        st.download_button(
            "⬇️ Export CV Rewrite Report (.txt)",
            data=st.session_state["cv_rewrite_txt_report"].encode("utf-8"),
            file_name="talentmatch_cv_rewrite.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_pdf:
        pdf_bytes = st.session_state.get("cv_rewrite_pdf_report")
        if pdf_bytes:
            st.download_button(
                "📄 Export CV Rewrite Report (.pdf)",
                data=pdf_bytes,
                file_name="talentmatch_cv_rewrite_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button(
                "📄 PDF report unavailable",
                disabled=True,
                use_container_width=True,
            )


# ------------------------------------------------------------
# Page
# ------------------------------------------------------------


render_page_intro(
    kicker="AI CV TRANSFORMATION",
    title="CV Rewrite AI",
    subtitle=(
        "Transform a source CV into a sharper, role-aligned version with a stronger "
        "headline, professional summary, experience bullets, and ATS keyword guidance."
    ),
    icon="✍️",
    badge="PRO WORKFLOW",
)

if not is_logged_in():
    st.warning("Please log in before using CV Rewrite AI.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

st.markdown("## Run a new CV rewrite")
st.caption(
    "Upload one PDF CV and paste the complete target role description to generate "
    "a focused, truthful rewrite."
)

render_action_panel(
    eyebrow="AI WORKFLOW",
    title="Prepare the rewrite",
    description=(
        "Use the complete source CV and exact job description. Better source material "
        "produces stronger positioning, more relevant bullets, and safer ATS suggestions."
    ),
    icon="🚀",
)

left, right = st.columns([1, 1.15])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📄 CV upload</div>
            <div class="tm-muted" style="margin-top:.55rem">
                Upload one PDF CV. TalentMatch Pro will preserve the source facts while
                improving role alignment and presentation.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Upload CV (PDF)",
        type=["pdf"],
        accept_multiple_files=False,
        key="cv_rewrite_upload",
    )

    if uploaded_file is not None:
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.success(
            f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)"
        )

with right:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🧾 Job description</div>
            <div class="tm-muted" style="margin-top:.55rem">
                Paste the complete job advertisement so the rewrite can mirror the
                correct role, skills, responsibilities, and professional language.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    job_description = st.text_area(
        "Job Description",
        value=DEFAULT_JOB_DESCRIPTION,
        height=330,
        key="cv_rewrite_job_description_input",
    )

can_submit = (
    uploaded_file is not None
    and bool(job_description.strip())
)

rewrite_clicked = st.button(
    "🚀 Rewrite CV",
    type="primary",
    use_container_width=True,
    disabled=not can_submit,
)

if rewrite_clicked:
    clear_cv_rewrite_state()

    if uploaded_file is None:
        st.error("Please upload a PDF CV.")
        st.stop()

    normalized_job_description = job_description.strip()
    if not normalized_job_description:
        st.error("Please paste a job description.")
        st.stop()

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf",
        )
    }
    data = {"job_description": normalized_job_description}

    with st.spinner("Rewriting CV content..."):
        response = api_post(
            "/rewrite-cv",
            data=data,
            files=files,
            timeout=180,
        )

    if getattr(response, "status_code", None) != 200:
        st.error(f"CV rewrite failed: {extract_error_message(response)}")
        if getattr(response, "status_code", None) == 403:
            st.warning("CV Rewrite AI is a Pro feature.")
            st.page_link(
                "pages/pricing.py",
                label="Upgrade to Pro",
                icon="🚀",
            )
        st.stop()

    try:
        payload = response.json()
    except Exception:
        st.error(
            "Backend returned invalid JSON: "
            f"{getattr(response, 'text', '')[:1000]}"
        )
        st.stop()

    if not isinstance(payload, dict):
        st.error("Backend returned an invalid response format.")
        st.json(payload)
        st.stop()

    st.session_state["rewrite_result"] = payload
    st.session_state["cv_rewrite_filename"] = uploaded_file.name
    st.session_state["cv_rewrite_job_description"] = normalized_job_description
    st.session_state.pop("cv_rewrite_txt_report", None)
    st.session_state.pop("cv_rewrite_pdf_report", None)

result = st.session_state.get("rewrite_result")
if isinstance(result, dict):
    st.divider()
    render_rewrite_result(result)
