import streamlit as st

from auth_utils import api_post, is_logged_in


st.set_page_config(page_title="ATS Checker", page_icon="🎯", layout="wide")

st.title("🎯 ATS Keyword Checker")
st.caption("Check which job-description keywords your CV already covers and which ones are missing.")

if not is_logged_in():
    st.warning("Please login before using ATS Checker.")
    st.stop()

uploaded_file = st.file_uploader("Upload your CV as a PDF", type=["pdf"])

job_description = st.text_area(
    "Paste the job description",
    height=260,
    value=(
        "Founding Full-Stack AI SaaS Engineer\n\n"
        "What we are looking for:\n"
        "- Python\n"
        "- FastAPI\n"
        "- PostgreSQL\n"
        "- Docker\n"
        "- Firebase\n"
        "- Stripe or Lemon Squeezy\n"
        "- Render deployment\n"
        "- SaaS products"
    ),
)

if st.button("Run ATS Checker", use_container_width=True):
    if uploaded_file is None:
        st.warning("Please upload a PDF first.")
        st.stop()

    if not job_description.strip():
        st.warning("Please paste a job description first.")
        st.stop()

    with st.spinner("Running ATS keyword check..."):
        response = api_post(
            "/ats-test",
            files={
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                )
            },
            data={"job_description": job_description},
        )

    # Supports both old and new api_post return styles.
    if isinstance(response, tuple):
        if len(response) == 3:
            ok, result, error = response
        elif len(response) == 2:
            result, error = response
            ok = error is None
        else:
            ok, result, error = False, None, "Unexpected API response format."
    else:
        ok = True
        result = response
        error = None

    if not ok or error:
        st.error(f"ATS check failed: {error}")
        st.stop()

    if not isinstance(result, dict):
        st.error("ATS check failed: backend returned an invalid response.")
        st.code(str(result))
        st.stop()

    st.success("ATS check completed.")

    score = result.get("score")
    if score is not None:
        st.metric("ATS Match Score", f"{score}%")

    matched_keywords = (
        result.get("matched_keywords")
        or result.get("covered_keywords")
        or result.get("matches")
        or []
    )

    missing_keywords = (
        result.get("missing_keywords")
        or result.get("missing_skills")
        or result.get("missing")
        or []
    )

    recommendations = (
        result.get("recommendations")
        or result.get("suggestions")
        or []
    )

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

    with st.expander("Raw backend response"):
        st.json(result)