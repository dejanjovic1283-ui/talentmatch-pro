from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from auth_utils import api_post, is_logged_in
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(page_title="Semantic Match • TalentMatch Pro", page_icon="🧠", layout="wide")
apply_global_styles()
render_sidebar()


DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

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

Nice to have:
- Experience with AI products, prompt design, and PDF/document processing
- Experience building MVPs from zero to first users
""".strip()


def normalize_response(raw: Any) -> Any:
    """Support api_post implementations that return response or (response, error)."""
    if isinstance(raw, tuple):
        if len(raw) >= 2 and raw[1]:
            raise RuntimeError(str(raw[1]))
        if len(raw) >= 1:
            return raw[0]
        raise RuntimeError("Empty response from backend.")
    return raw


def extract_error_message(response: Any) -> str:
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""

    try:
        payload = response.json()
    except Exception:
        if status_code:
            return f"{status_code}: {text[:1000]}"
        return text[:1000] or "Unknown backend error."

    if not isinstance(payload, dict):
        return str(payload)

    detail = payload.get("detail")
    error = payload.get("error")

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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        number = int(float(value))
    except Exception:
        return default
    return max(0, min(number, 100))


def extract_list(data: Dict[str, Any], key: str) -> List[str]:
    value = data.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def verdict_level(score: int) -> tuple[str, str, str]:
    if score >= 80:
        return "Excellent fit", "Strong semantic alignment with this role.", "🔥"
    if score >= 60:
        return "Good fit", "Solid match, but some themes should be improved.", "✅"
    return "Needs improvement", "Rewrite targeted sections before applying.", "⚠️"


def render_chip_group(title: str, items: List[str], empty_text: str, icon: str, green: bool = False) -> None:
    pill_class = "tm-pill tm-pill-green" if green else "tm-pill"
    if items:
        content = "".join(f"<span class='{pill_class}'>{safe_html(item)}</span>" for item in items[:40])
    else:
        content = f"<div class='tm-muted'>{safe_html(empty_text)}</div>"

    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div>{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_text_card(title: str, body: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted">{safe_html(body) if body else 'No content returned.'}</div>
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


def render_results(result: Dict[str, Any]) -> None:
    combined_score = safe_int(result.get("combined_score"))
    semantic_score = safe_int(result.get("semantic_score"))
    keyword_score = safe_int(result.get("keyword_score"))
    verdict = str(result.get("verdict") or "Semantic Match")
    label, message, icon = verdict_level(combined_score)

    st.success("Semantic match completed.")
    st.markdown('<div class="tm-section-title">Semantic match result</div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <div class="tm-card" style="margin-bottom:1rem">
            <div class="tm-kicker">AI Verdict</div>
            <div class="tm-card-title">{safe_html(icon)} {safe_html(verdict)} — {combined_score}/100</div>
            <div class="tm-muted"><strong>{safe_html(label)}</strong> · {safe_html(message)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Combined Score", f"{combined_score}/100")
    with c2:
        st.metric("Semantic Score", f"{semantic_score}/100")
    with c3:
        st.metric("Keyword Score", f"{keyword_score}/100")

    st.progress(combined_score)

    summary = str(result.get("summary") or "")
    render_text_card("Recruiter summary", summary, "📝")

    st.markdown('<div class="tm-section-title">Theme coverage</div>', unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        render_chip_group("Matched themes", extract_list(result, "matched_themes"), "No matched themes returned.", "✅", True)
    with right:
        render_chip_group("Missing themes", extract_list(result, "missing_themes"), "No missing themes returned.", "🎯", False)

    st.markdown('<div class="tm-section-title">AI recommendations</div>', unsafe_allow_html=True)
    render_recommendations(extract_list(result, "recommendations"))

    st.markdown('<div class="tm-section-title">Keyword details</div>', unsafe_allow_html=True)
    kw_left, kw_right = st.columns(2)
    with kw_left:
        render_chip_group("Matched keywords", extract_list(result, "matched_keywords"), "No matched keywords returned.", "✅", True)
    with kw_right:
        render_chip_group("Missing keywords", extract_list(result, "missing_keywords"), "No missing keywords returned.", "❌", False)

    report_lines = [
        "TalentMatch Pro - Semantic Match",
        "=" * 34,
        "",
        f"Combined Score: {combined_score}/100",
        f"Semantic Score: {semantic_score}/100",
        f"Keyword Score: {keyword_score}/100",
        f"Verdict: {verdict}",
        "",
        "Recruiter Summary:",
        summary,
        "",
        "Matched Themes:",
        *[f"- {item}" for item in extract_list(result, "matched_themes")],
        "",
        "Missing Themes:",
        *[f"- {item}" for item in extract_list(result, "missing_themes")],
        "",
        "Recommendations:",
        *[f"- {item}" for item in extract_list(result, "recommendations")],
    ]
    st.download_button(
        "📥 Download Semantic Match Summary",
        data="\n".join(report_lines),
        file_name="talentmatch_semantic_match_summary.txt",
        mime="text/plain",
        use_container_width=True,
    )


render_hero(
    "AI semantic intelligence",
    "Semantic Match",
    "Compare your CV with a job description using semantic AI matching, keyword coverage and recruiter-style recommendations.",
    "🧠",
)

if not is_logged_in():
    st.warning("Please login before using Semantic Match.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
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
    uploaded_file = st.file_uploader("Upload your CV as a PDF", type=["pdf"], accept_multiple_files=False)
    if uploaded_file is not None:
        file_size_kb = len(uploaded_file.getvalue()) / 1024
        st.success(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

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
    job_description = st.text_area("Paste the job description", value=DEFAULT_JOB_DESCRIPTION, height=330)

if st.button(
    "🚀 Run Semantic Match",
    use_container_width=True,
    disabled=uploaded_file is None or not job_description.strip(),
):
    if uploaded_file is None:
        st.error("Please upload a PDF CV.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
    data = {"job_description": job_description.strip()}

    with st.spinner("Running semantic matching..."):
        try:
            raw_response = api_post("/semantic-match", data=data, files=files, timeout=180)
            response = normalize_response(raw_response)
        except Exception as exc:
            st.error(f"Semantic match failed: {exc}")
            st.stop()

    status_code = getattr(response, "status_code", None)
    if status_code != 200:
        st.error(f"Semantic match failed: {extract_error_message(response)}")
        if status_code == 403:
            st.warning("🚀 Semantic Match is a Pro feature.")
            st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="🚀")
        st.stop()

    try:
        payload = response.json()
    except Exception:
        response_text = getattr(response, "text", "") or ""
        st.error(f"Backend returned invalid JSON: {response_text[:1000]}")
        st.stop()

    if not isinstance(payload, dict):
        st.error("Backend returned invalid response format.")
        st.json(payload)
        st.stop()

    st.session_state["semantic_result"] = payload

result = st.session_state.get("semantic_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
