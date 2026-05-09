import requests
import streamlit as st # pyright: ignore[reportMissingImports]

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


def get_verdict_style(coverage: int) -> tuple[str, str]:
    if coverage >= 80:
        return "🔥 ATS Strong", "success"
    if coverage >= 60:
        return "✅ ATS Good", "warning"
    return "⚠️ ATS Weak", "error"


st.title("🎯 ATS Keyword Checker")
st.caption("Check how well your CV matches important keywords from the job description.")

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
    accept_multiple_files=False,
)

job_description = st.text_area(
    "Paste the job description",
    value=DEFAULT_JOB_DESCRIPTION,
    height=280,
)

if uploaded_file is not None:
    file_size_kb = len(uploaded_file.getvalue()) / 1024
    st.info(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

if st.button("Run ATS Check", use_container_width=True):
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
    st.header("ATS Result")

    coverage = int(result.get("coverage", 0) or 0)
    verdict, level = get_verdict_style(coverage)

    if level == "success":
        st.success(f"{verdict} — {coverage}% keyword coverage")
    elif level == "warning":
        st.warning(f"{verdict} — {coverage}% keyword coverage")
    else:
        st.error(f"{verdict} — {coverage}% keyword coverage")

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

    left, right = st.columns(2)

    with left:
        st.subheader("✅ Matched ATS Keywords")
        if matched:
            st.write(", ".join(matched))
        else:
            st.caption("No matched keywords found.")

    with right:
        st.subheader("❌ Missing ATS Keywords")
        if missing:
            st.write(", ".join(missing))
        else:
            st.caption("No missing keywords found.")

    st.subheader("💡 Recommendations")
    for recommendation in recommendations:
        st.markdown(f"- {recommendation}")

    st.info(
        "Tip: Add missing keywords only where they truthfully match your experience. "
        "ATS optimization should improve clarity, not fake skills."
    )

    with st.expander("Raw ATS JSON response"):
        st.json(result)