import os

import requests
import streamlit as st

st.set_page_config(
    page_title="CV Rewrite AI",
    page_icon="✍️",
    layout="wide",
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

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
""".strip()


def get_auth_headers() -> dict[str, str]:
    user = st.session_state.get("user")

    if not isinstance(user, dict):
        return {}

    token = user.get("id_token", "")

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


st.title("✍️ CV Rewrite AI")
st.caption("Rewrite your CV summary and bullet points for a specific job description.")

user = st.session_state.get("user")

if not isinstance(user, dict) or not user.get("id_token"):
    st.warning("Please login before using CV Rewrite AI.")
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

    headers = get_auth_headers()

    if not headers:
        st.error("Missing auth token. Please login again.")
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

    with st.spinner("Rewriting CV content..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/rewrite-cv",
                headers=headers,
                data=data,
                files=files,
                timeout=180,
            )
        except requests.RequestException as exc:
            st.error(f"Backend request failed: {exc}")
            st.stop()

    if response.status_code != 200:
        st.error(response.text)
        st.stop()

    st.session_state["rewrite_result"] = response.json()
    st.success("CV rewrite completed.")


result = st.session_state.get("rewrite_result")

if isinstance(result, dict):
    st.divider()
    st.header("Rewrite Result")

    st.subheader("🎯 Suggested Headline")
    st.success(result.get("headline", ""))

    st.subheader("📝 Rewritten Summary")
    st.write(result.get("rewritten_summary", ""))

    st.subheader("✅ Rewritten Bullet Points")
    for bullet in result.get("rewritten_bullets", []):
        st.markdown(f"- {bullet}")

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