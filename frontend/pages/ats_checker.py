import streamlit as st

from auth_utils import api_post, is_logged_in

st.set_page_config(page_title="ATS Keyword Checker", page_icon="🎯", layout="wide")

st.title("🎯 ATS Keyword Checker")
st.caption("Check which job-description keywords your CV already covers and which ones are missing.")

if not is_logged_in():
    st.warning("Please login before using the ATS checker.")
    st.page_link("pages/login.py", label="Login", icon="🔐")
    st.stop()

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
    key="ats_pdf_upload",
)

job_description = st.text_area(
    "Paste the job description",
    height=320,
)

if uploaded_file is not None:
    st.info(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

run_button = st.button(
    "Run ATS Checker",
    use_container_width=True,
    disabled=uploaded_file is None or not job_description.strip(),
)

if run_button:
    file_payload = None

    if uploaded_file is not None:
        file_payload = {
            "file": (
                uploaded_file.name or "cv.pdf",
                uploaded_file.getvalue(),
                "application/pdf",
            )
        }

    with st.spinner("Checking ATS keyword coverage..."):
        result, error = api_post(
            "/ats-test",
            data={"job_description": job_description},
            files=file_payload,
        )

    if error:
        st.error(f"ATS check failed: {error}")
        if result:
            st.code(str(result))
        st.stop()

    if not isinstance(result, dict):
        st.error("ATS check failed: invalid backend response.")
        st.code(str(result))
        st.stop()

    coverage = int(result.get("coverage", 0) or 0)
    verdict = str(result.get("verdict", "ATS Result"))

    matched_keywords = result.get("matched_keywords", []) or []
    missing_keywords = result.get("missing_keywords", []) or []
    recommendations = result.get("recommendations", []) or []

    st.success(f"{verdict} — {coverage}% keyword coverage")
    st.progress(min(max(coverage, 0), 100) / 100)

    col1, col2, col3 = st.columns(3)
    col1.metric("Coverage", f"{coverage}%")
    col2.metric("Matched", len(matched_keywords))
    col3.metric("Missing", len(missing_keywords))

    left, right = st.columns(2)

    with left:
        st.subheader("✅ Matched Keywords")
        if matched_keywords:
            for keyword in matched_keywords:
                st.markdown(f"- {keyword}")
        else:
            st.info("No matched keywords found.")

    with right:
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