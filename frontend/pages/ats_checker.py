import streamlit as st

from auth_utils import api_post, is_logged_in


st.set_page_config(page_title="ATS Checker", page_icon="🎯", layout="wide")

st.title("🎯 ATS Keyword Checker")
st.caption("Check which job-description keywords your CV already covers and which ones are missing.")

if not is_logged_in():
    st.warning("Please login before using ATS Checker.")
    st.stop()

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
    accept_multiple_files=False,
)

job_description = st.text_area(
    "Paste the job description",
    height=300,
    value="""Founding Full-Stack AI SaaS Engineer

What we are looking for:
- Python
- FastAPI
- PostgreSQL
- Docker
- Firebase
- Stripe or Lemon Squeezy
- Render deployment
- SaaS products""",
)

if st.button("Run ATS Checker", use_container_width=True):
    if uploaded_file is None:
        st.warning("Please upload your CV PDF first.")
        st.stop()

    if not job_description.strip():
        st.warning("Please paste the job description first.")
        st.stop()

    with st.spinner("Running ATS keyword check..."):
        response = api_post(
            "/ats-check",
            files={"file": uploaded_file},
            data={"job_description": job_description},
        )

    if not response.ok:
        st.error(f"ATS check failed: {response.status_code}")
        try:
            st.json(response.json())
        except Exception:
            st.code(response.text)
        st.stop()

    try:
        result = response.json()
    except Exception:
        st.error("ATS check failed: backend returned invalid JSON.")
        st.code(response.text)
        st.stop()

    score = result.get("score", result.get("ats_score", 0))
    matched_keywords = result.get("matched_keywords", result.get("matched", []))
    missing_keywords = result.get("missing_keywords", result.get("missing", []))
    recommendations = result.get("recommendations", result.get("tips", []))

    st.success("ATS check completed.")

    st.metric("ATS Keyword Score", f"{score}%")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("✅ Matched Keywords")
        if matched_keywords:
            for keyword in matched_keywords:
                st.markdown(f"- {keyword}")
        else:
            st.info("No matched keywords returned.")

    with col2:
        st.subheader("❌ Missing Keywords")
        if missing_keywords:
            for keyword in missing_keywords:
                st.markdown(f"- {keyword}")
        else:
            st.success("No missing keywords found.")

    st.subheader("💡 Recommendations")
    if recommendations:
        for item in recommendations:
            st.markdown(f"- {item}")
    else:
        st.info("No recommendations returned.")