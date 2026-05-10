import requests
import streamlit as st

from app import get_auth_headers, load_config

st.set_page_config(
    page_title="ATS Checker",
    page_icon="🎯",
    layout="wide",
)

config = load_config()

DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with Lemon Squeezy
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


def get_verdict(coverage: int) -> tuple[str, str, str]:
    if coverage >= 80:
        return "ATS Strong", "🔥", "success"
    if coverage >= 60:
        return "ATS Good", "✅", "warning"
    return "ATS Weak", "⚠️", "error"


def render_keyword_tags(keywords: list[str], empty_message: str) -> None:
    if not keywords:
        st.caption(empty_message)
        return

    html = "<div style='display:flex; flex-wrap:wrap; gap:8px; margin-top:8px;'>"

    for keyword in keywords:
        safe_keyword = (
            str(keyword)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

        html += (
            "<span style='"
            "padding:6px 10px;"
            "border-radius:999px;"
            "background:#eef2ff;"
            "border:1px solid #c7d2fe;"
            "font-size:14px;"
            "line-height:1.4;"
            "'>"
            f"{safe_keyword}"
            "</span>"
        )

    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_recommendations(recommendations: list[str]) -> None:
    if not recommendations:
        st.info("No recommendations available.")
        return

    for recommendation in recommendations:
        st.markdown(f"- {recommendation}")


st.title("🎯 ATS Keyword Checker")
st.caption(
    "Compare your CV against a job description and see which ATS keywords are missing."
)

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
    accept_multiple_files=False,
)

job_description = st.text_area(
    "Paste the job description",
    value=DEFAULT_JOB_DESCRIPTION,
    height=300,
)

if uploaded_file is not None:
    file_size_kb = len(uploaded_file.getvalue()) / 1024
    st.info(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

run_clicked = st.button("Run ATS Check", use_container_width=True)

if run_clicked:
    if uploaded_file is None:
        st.error("Please upload a PDF CV.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            "application/pdf",
        )
    }

    data = {
        "job_description": job_description,
    }

    response: requests.Response | None = None

    with st.spinner("Checking ATS keyword coverage..."):
        try:
            response = requests.post(
                f"{config.backend_url}/ats-test",
                headers=get_auth_headers(),
                data=data,
                files=files,
                timeout=120,
            )
        except requests.RequestException as exc:
            st.error(f"Backend request failed: {exc}")
            st.stop()

    if response is None:
        st.error("Backend did not return a response.")
        st.stop()

    if response.status_code != 200:
        st.error(response.text)
        st.stop()

    st.session_state["ats_result"] = response.json()
    st.session_state["ats_file_name"] = uploaded_file.name


result = st.session_state.get("ats_result")

if isinstance(result, dict):
    st.divider()

    coverage = int(result.get("coverage", 0) or 0)
    verdict, icon, level = get_verdict(coverage)

    st.header("ATS Result")

    if level == "success":
        st.success(f"{icon} {verdict} — {coverage}% keyword coverage")
    elif level == "warning":
        st.warning(f"{icon} {verdict} — {coverage}% keyword coverage")
    else:
        st.error(f"{icon} {verdict} — {coverage}% keyword coverage")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Keyword Coverage", f"{coverage}%")

    with col2:
        st.metric("Total Keywords", result.get("total_keywords", 0))

    with col3:
        st.metric("CV File", st.session_state.get("ats_file_name", "resume.pdf"))

    st.progress(min(max(coverage, 0), 100) / 100)

    matched = result.get("matched_keywords", [])
    missing = result.get("missing_keywords", [])
    recommendations = result.get("recommendations", [])

    st.subheader("Keyword Breakdown")

    left, right = st.columns(2)

    with left:
        with st.container(border=True):
            st.markdown("### ✅ Matched Keywords")
            st.caption("These terms were found in your CV.")
            render_keyword_tags(matched, "No matched keywords found.")

    with right:
        with st.container(border=True):
            st.markdown("### ❌ Missing Keywords")
            st.caption("Add these only if they truthfully match your experience.")
            render_keyword_tags(missing, "No missing keywords found.")

    st.subheader("💡 Recommendations")

    with st.container(border=True):
        render_recommendations(recommendations)

    st.info(
        "ATS optimization works best when you naturally mirror the job description. "
        "Do not add fake skills — only make real experience easier to find."
    )

    st.markdown("---")
    st.markdown(
        "🚀 Want deeper recruiter insights, rewrite suggestions, and interview prep? "
        "**Upgrade to TalentMatch Pro** from the pricing page."
    )