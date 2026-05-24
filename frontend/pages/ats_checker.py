import streamlit as st
from auth_utils import api_post, is_logged_in

st.set_page_config(page_title="ATS Checker • TalentMatch Pro", page_icon="🎯", layout="wide")

st.title("🎯 ATS Keyword Checker")
st.caption("Check which job-description keywords your CV already covers and which ones are missing.")

if not is_logged_in():
    st.warning("Please login before using ATS Checker.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

uploaded_file = st.file_uploader("Upload your CV as a PDF", type=["pdf"])
job_description = st.text_area(
    "Paste the job description",
    placeholder=(
        "Paste the job description here...\n\n"
        "Example:\n"
        "Senior Backend Engineer\n\n"
        "Requirements:\n"
        "- Python\n"
        "- FastAPI\n"
        "- PostgreSQL\n"
        "- Docker\n"
        "- Cloud deployment"
    ),
    height=260,
)

can_run = uploaded_file and job_description.strip()

if uploaded_file:
    st.info(f"Selected file: {uploaded_file.name} ({uploaded_file.size/1024:.1f} KB)")

if st.button("Run ATS Checker", use_container_width=True, disabled=not can_run):
    if not uploaded_file:
        st.error("No CV file uploaded. Please upload a PDF file before running the ATS check.")
    else:
        with st.spinner("Checking ATS keywords..."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                data = {"job_description": job_description}
                resp = api_post("/ats-checker", data=data, files=files, timeout=120)
                if resp.status_code == 200:
                    st.session_state["ats_result"] = resp.json()
                    st.success("ATS check completed successfully.")
                else:
                    st.error(f"ATS check failed: {resp.status_code}")
                    st.code(resp.text)
            except Exception as exc:
                st.error(f"ATS check failed: {exc}")

result = st.session_state.get("ats_result")
if result:
    st.divider()
    st.header("ATS Result")

    score = result.get("score") or result.get("ats_score") or 0
    st.success(f"ATS Score: {score}/100")
    st.progress(min(int(score)/100, 1.0) if score else 0)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("✅ Covered Keywords")
        for kw in result.get("covered_keywords") or result.get("matched_keywords") or []:
            st.markdown(f"- {kw}")
        if not result.get("covered_keywords"): st.write("No covered keywords returned.")
    with col2:
        st.subheader("❌ Missing Keywords")
        missing = result.get("missing_keywords") or []
        for kw in missing: st.markdown(f"- {kw}")
        if not missing: st.success("No major missing keywords found.")

    st.subheader("💡 Recommendations")
    recs = result.get("recommendations") or []
    for r in recs: st.markdown(f"- {r}")
    if not recs: st.info("No recommendations returned.")