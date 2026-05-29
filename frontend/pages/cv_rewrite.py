import streamlit as st

from auth_utils import api_post, is_logged_in


st.set_page_config(
    page_title="CV Rewrite AI",
    page_icon="✍️",
    layout="wide",
)


DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with Paddle
- Improve product reliability, UX, and deployment pipelines

What we are looking for:
- Strong Python backend fundamentals
- Experience with APIs, auth, databases, and SaaS integrations
- Product mindset and ability to ship independently
- Familiarity with cloud deployment and developer tooling
""".strip()


def extract_error_message(response) -> str:
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


st.title("✍️ CV Rewrite AI")
st.caption("Rewrite your CV summary and bullet points for a specific job description.")

if not is_logged_in():
    st.warning("Please login before using CV Rewrite AI.")
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
    height=300,
)

if uploaded_file is not None:
    file_size_kb = len(uploaded_file.getvalue()) / 1024
    st.info(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

if st.button("Rewrite CV", use_container_width=True):
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

    with st.spinner("Rewriting CV content..."):
        response = api_post(
            "/rewrite-cv",
            data=data,
            files=files,
            timeout=180,
        )

    if response.status_code != 200:
        st.error(f"CV rewrite failed: {extract_error_message(response)}")

        if response.status_code == 403:
            st.warning("🚀 CV Rewrite AI is a Pro feature.")
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

    st.session_state["rewrite_result"] = payload
    st.success("CV rewrite completed.")


result = st.session_state.get("rewrite_result")

if isinstance(result, dict):
    st.divider()
    st.header("Rewrite Result")

    st.subheader("🎯 Suggested Headline")
    headline = result.get("headline", "")
    if headline:
        st.success(headline)
    else:
        st.info("No headline returned.")

    st.subheader("📝 Rewritten Summary")
    rewritten_summary = result.get("rewritten_summary", "")
    if rewritten_summary:
        st.write(rewritten_summary)
    else:
        st.info("No rewritten summary returned.")

    st.subheader("✅ Rewritten Bullet Points")
    rewritten_bullets = result.get("rewritten_bullets", [])
    if rewritten_bullets:
        for bullet in rewritten_bullets:
            st.markdown(f"- {bullet}")
    else:
        st.info("No rewritten bullet points returned.")

    left, right = st.columns(2)

    with left:
        st.subheader("🔎 ATS Keywords to Add")
        keywords = result.get("ats_keywords_to_add", [])

        if keywords:
            for keyword in keywords:
                st.info(keyword)
        else:
            st.caption("No keyword suggestions returned.")

    with right:
        st.subheader("⚠️ Cautions")
        cautions = result.get("cautions", [])

        if cautions:
            for caution in cautions:
                st.warning(caution)
        else:
            st.caption("No cautions returned.")

    report = "\n".join(
        [
            "TalentMatch Pro - CV Rewrite",
            "=" * 32,
            "",
            "Suggested Headline:",
            result.get("headline", ""),
            "",
            "Rewritten Summary:",
            result.get("rewritten_summary", ""),
            "",
            "Rewritten Bullet Points:",
            *[f"- {b}" for b in result.get("rewritten_bullets", [])],
            "",
            "ATS Keywords to Add:",
            *[f"- {k}" for k in result.get("ats_keywords_to_add", [])],
            "",
            "Cautions:",
            *[f"- {c}" for c in result.get("cautions", [])],
        ]
    )

    st.download_button(
        "📥 Download Rewrite",
        data=report,
        file_name="talentmatch_cv_rewrite.txt",
        mime="text/plain",
        use_container_width=True,
    )