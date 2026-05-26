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
    placeholder=(
        "Paste the job description here...\n\n"
        "Example:\n"
        "- Python\n"
        "- FastAPI\n"
        "- PostgreSQL\n"
        "- Docker"
    ),
)

if uploaded_file:
    st.success(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

run_clicked = st.button("Run ATS Checker", use_container_width=True)

if run_clicked:
    if not uploaded_file:
        st.warning("Please upload your CV PDF first.")
        st.stop()

    if not job_description.strip():
        st.warning("Please paste the job description first.")
        st.stop()

    with st.spinner("Running ATS keyword check..."):
        response = api_post(
            "/ats-test",
            data={"job_description": job_description},
            files={
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                )
            },
        )

    result = None
    error = None

    # New auth_utils usually returns a requests.Response.
    if hasattr(response, "status_code"):
        if response.status_code != 200:
            error = f"ATS check failed: {response.status_code}"
            try:
                st.code(response.text)
            except Exception:
                pass
        else:
            try:
                result = response.json()
            except Exception:
                error = "ATS check failed: backend returned an invalid JSON response."
                try:
                    st.code(response.text)
                except Exception:
                    pass

    # Backward compatibility if api_post returns (result, error).
    elif isinstance(response, tuple) and len(response) == 2:
        result, error = response

    # Backward compatibility if api_post returns a dict directly.
    elif isinstance(response, dict):
        result = response

    else:
        error = "ATS check failed: backend returned an invalid response."
        st.code(str(response))

    if error:
        st.error(error)
        st.stop()

    if not isinstance(result, dict):
        st.error("ATS check failed: backend response is not a JSON object.")
        st.code(str(result))
        st.stop()

    score = result.get("score")
    matched_keywords = (
        result.get("matched_keywords")
        or result.get("matched")
        or result.get("found_keywords")
        or []
    )
    missing_keywords = (
        result.get("missing_keywords")
        or result.get("missing")
        or []
    )
    recommendations = result.get("recommendations") or []

    st.success("ATS check completed.")

    if score is not None:
        try:
            st.metric("ATS Match Score", f"{float(score):.0f}%")
            st.progress(max(0, min(100, int(float(score)))) / 100)
        except Exception:
            st.metric("ATS Match Score", str(score))

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