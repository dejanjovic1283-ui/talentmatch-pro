import streamlit as st

from auth_utils import api_post, is_logged_in


st.set_page_config(
    page_title="Semantic Match • TalentMatch Pro",
    page_icon="🧠",
    layout="wide",
)


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


def extract_error_message(response) -> str:
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


def verdict_level(score: int) -> str:
    if score >= 80:
        return "success"
    if score >= 60:
        return "warning"
    return "error"


st.title("🧠 Semantic Matching")
st.caption(
    "Compare your CV and job description using OpenAI embeddings plus keyword overlap."
)

if not is_logged_in():
    st.warning("Please login before using Semantic Matching.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
    accept_multiple_files=False,
)

job_description = st.text_area(
    "Paste the job description",
    value=DEFAULT_JOB_DESCRIPTION,
    height=320,
)

if uploaded_file is not None:
    file_size_kb = len(uploaded_file.getvalue()) / 1024
    st.info(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

if st.button("Run Semantic Match", use_container_width=True):
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
        "job_description": job_description.strip(),
    }

    with st.spinner("Running semantic matching..."):
        response = api_post(
            "/semantic-match",
            data=data,
            files=files,
            timeout=180,
        )

    if response.status_code != 200:
        st.error(f"Semantic match failed: {extract_error_message(response)}")

        if response.status_code == 403:
            st.warning("🚀 Semantic Matching is a Pro feature.")
            st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="🚀")

        st.stop()

    try:
        payload = response.json()
    except Exception:
        st.error(f"Backend returned invalid JSON: {response.text[:1000]}")
        st.stop()

    if not isinstance(payload, dict):
        st.error("Backend returned invalid response format.")
        st.json(payload)
        st.stop()

    st.session_state["semantic_result"] = payload
    st.success("Semantic match completed.")


result = st.session_state.get("semantic_result")

if isinstance(result, dict):
    st.divider()
    st.header("Semantic Match Result")

    combined_score = int(result.get("combined_score", 0) or 0)
    semantic_score = int(result.get("semantic_score", 0) or 0)
    keyword_score = int(result.get("keyword_score", 0) or 0)

    level = verdict_level(combined_score)
    verdict = result.get("verdict", "Semantic Match")

    if level == "success":
        st.success(f"🔥 {verdict} — {combined_score}/100")
    elif level == "warning":
        st.warning(f"✅ {verdict} — {combined_score}/100")
    else:
        st.error(f"⚠️ {verdict} — {combined_score}/100")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Combined Score", f"{combined_score}/100")

    with col2:
        st.metric("Semantic Score", f"{semantic_score}/100")

    with col3:
        st.metric("Keyword Score", f"{keyword_score}/100")

    st.progress(min(max(combined_score, 0), 100) / 100)

    st.markdown("## 📝 Recruiter Summary")
    summary = result.get("summary", "")

    if summary:
        st.write(summary)
    else:
        st.info("No summary returned.")

    left, right = st.columns(2)

    with left:
        st.markdown("## ✅ Matched Themes")
        matched_themes = result.get("matched_themes", [])

        if matched_themes:
            for item in matched_themes:
                st.markdown(f"- {item}")
        else:
            st.caption("No matched themes returned.")

    with right:
        st.markdown("## ❌ Missing Themes")
        missing_themes = result.get("missing_themes", [])

        if missing_themes:
            for item in missing_themes:
                st.markdown(f"- {item}")
        else:
            st.caption("No missing themes returned.")

    st.markdown("## 💡 Recommendations")
    recommendations = result.get("recommendations", [])

    if recommendations:
        for item in recommendations:
            st.markdown(f"- {item}")
    else:
        st.caption("No recommendations returned.")

    st.divider()

    kw_left, kw_right = st.columns(2)

    with kw_left:
        st.markdown("### Matched Keywords")
        matched = result.get("matched_keywords", [])

        if matched:
            st.write(", ".join(matched))
        else:
            st.caption("No matched keywords returned.")

    with kw_right:
        st.markdown("### Missing Keywords")
        missing = result.get("missing_keywords", [])

        if missing:
            st.write(", ".join(missing))
        else:
            st.caption("No missing keywords returned.")