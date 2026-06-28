from __future__ import annotations

from typing import Any, Dict, List

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


def get_list(payload: Dict[str, Any], key: str) -> List[str]:
    value = payload.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


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


def bullet_card(title: str, items: List[str], empty_text: str, icon: str = "✅", green: bool = False) -> None:
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


def render_rewrite_result(result: Dict[str, Any]) -> None:
    headline = str(result.get("headline", "") or "")
    rewritten_summary = str(result.get("rewritten_summary", "") or "")
    rewritten_bullets = get_list(result, "rewritten_bullets")
    keywords = get_list(result, "ats_keywords_to_add")
    cautions = get_list(result, "cautions")

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

    report = "\n".join(
        [
            "TalentMatch Pro - CV Rewrite",
            "=" * 32,
            "",
            "Suggested Headline:",
            headline,
            "",
            "Rewritten Summary:",
            rewritten_summary,
            "",
            "Rewritten Bullet Points:",
            *[f"- {b}" for b in rewritten_bullets],
            "",
            "ATS Keywords to Add:",
            *[f"- {k}" for k in keywords],
            "",
            "Cautions:",
            *[f"- {c}" for c in cautions],
        ]
    )

    st.download_button(
        "📥 Download Rewrite",
        data=report,
        file_name="talentmatch_cv_rewrite.txt",
        mime="text/plain",
        use_container_width=True,
    )


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
        "Upload your CV as a PDF",
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
        "Paste the job description",
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

result = st.session_state.get("rewrite_result")
if isinstance(result, dict):
    st.divider()
    render_rewrite_result(result)
