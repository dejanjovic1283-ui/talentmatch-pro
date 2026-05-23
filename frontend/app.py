import os
import json
import requests
import streamlit as st

st.set_page_config(
    page_title="TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

DEFAULT_JOB_DESCRIPTION = """Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with Stripe
- Improve product reliability, UX, and deployment pipelines

What we are looking for:
- Strong Python backend fundamentals
- Experience with APIs, auth, databases, and SaaS integrations
- Product mindset and ability to ship independently
- Familiarity with cloud deployment and developer tooling

Nice to have:
- Experience with AI products, prompt design, and PDF/document processing
- Experience building MVPs from zero to first users
"""


def get_token():
    user = st.session_state.get("user")

    if isinstance(user, dict):
        for key in ["idToken", "id_token", "token", "accessToken", "access_token"]:
            value = user.get(key)
            if value:
                return str(value)

    for key in ["id_token", "idToken", "firebase_token", "token", "access_token"]:
        value = st.session_state.get(key)
        if value:
            return str(value)

    return ""


def get_headers():
    token = get_token()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def get_profile():
    headers = get_headers()

    if not headers:
        return None

    try:
        response = requests.get(
            f"{BACKEND_URL}/me",
            headers=headers,
            timeout=60,
        )

        if response.status_code == 200:
            return response.json()

        return None

    except Exception:
        return None


def analyze_cv(uploaded_file, job_description):
    headers = get_headers()

    if not headers:
        st.error("Please login before analyzing a CV.")
        return None

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

    try:
        response = requests.post(
            f"{BACKEND_URL}/analyze-resume",
            headers=headers,
            files=files,
            data=data,
            timeout=180,
        )

        if response.status_code != 200:
            st.error(response.text)
            return None

        return response.json()

    except Exception as exc:
        st.error(f"Analysis failed: {exc}")
        return None


def generate_pdf_report(result, job_description):
    headers = get_headers()

    if not headers:
        st.error("Please login first.")
        return None

    try:
        data = {
            "cv_filename": result.get("cv_filename", st.session_state.get("last_uploaded_name", "resume.pdf")),
            "score": int(result.get("score", 0)),
            "summary": result.get("summary", ""),
            "strengths_json": json.dumps(result.get("strengths", [])),
            "weaknesses_json": json.dumps(result.get("weaknesses", [])),
            "recommendations_json": json.dumps(result.get("recommendations", [])),
            "job_description": job_description,
        }

        response = requests.post(
            f"{BACKEND_URL}/reports/analysis-pdf",
            headers=headers,
            data=data,
            timeout=120,
        )

        if response.status_code != 200:
            st.error(response.text)
            return None

        return response.content

    except Exception as exc:
        st.error(f"PDF generation failed: {exc}")
        return None


def make_txt_report(result, job_description):
    strengths = result.get("strengths", [])
    weaknesses = result.get("weaknesses", [])
    recommendations = result.get("recommendations", [])

    lines = [
        "TalentMatch Pro CV Analysis Report",
        "=" * 40,
        "",
        f"Score: {result.get('score', 0)}/100",
        f"Verdict: {result.get('verdict', 'N/A')}",
        f"CV file: {result.get('cv_filename', st.session_state.get('last_uploaded_name', 'resume.pdf'))}",
        "",
        "Summary",
        "-" * 20,
        result.get("summary", ""),
        "",
        "Strengths",
        "-" * 20,
    ]

    for item in strengths:
        lines.append(f"- {item}")

    lines.extend(["", "Missing Skills", "-" * 20])

    for item in weaknesses:
        lines.append(f"- {item}")

    lines.extend(["", "Recommendations", "-" * 20])

    for item in recommendations:
        lines.append(f"- {item}")

    lines.extend(["", "Job Description", "-" * 20, job_description])

    return "\n".join(lines)


profile = get_profile()
is_logged_in = bool(get_headers())
is_pro = bool(profile and profile.get("is_pro"))
plan = profile.get("plan", "free") if profile else "free"
remaining = profile.get("remaining") if profile else None
used = profile.get("analyses_used") if profile else None
free_limit = profile.get("free_limit", 3) if profile else 3

st.markdown("# 🚀 TalentMatch Pro")
st.caption("AI-powered CV matching, ATS keyword analysis, and job application insights.")

if not is_logged_in:
    st.warning("Please login before analyzing a CV.")
else:
    if is_pro:
        st.success("🚀 Pro plan active — unlimited analyses and premium tools unlocked.")
    else:
        st.info(f"Free plan: {used or 0}/{free_limit} analyses used. Remaining: {remaining if remaining is not None else free_limit}")

        if remaining is not None:
            progress = min(max((used or 0) / free_limit, 0), 1)
            st.progress(progress)

st.divider()

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
)

if uploaded_file:
    st.session_state["last_uploaded_name"] = uploaded_file.name
    st.info(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

job_description = st.text_area(
    "Paste the job description",
    value=st.session_state.get("last_job_description", DEFAULT_JOB_DESCRIPTION),
    height=320,
)

st.session_state["last_job_description"] = job_description

analyze_disabled = not is_logged_in or uploaded_file is None or not job_description.strip()

if st.button(
    "Analyze CV",
    use_container_width=True,
    disabled=analyze_disabled,
):
    with st.spinner("Analyzing CV with AI..."):
        result = analyze_cv(uploaded_file, job_description)

    if result:
        result["cv_filename"] = uploaded_file.name
        st.session_state["analysis_result"] = result
        st.success("Analysis completed successfully.")
        st.rerun()

if not is_logged_in:
    st.info("Login first to run an analysis.")
elif uploaded_file is None:
    st.info("Upload a PDF CV to start.")
elif not job_description.strip():
    st.info("Paste a job description to continue.")

result = st.session_state.get("analysis_result")

if result:
    st.divider()
    st.markdown("## Analysis result")

    score = int(result.get("score", 0))
    verdict = result.get("verdict")

    if not verdict:
        if score >= 80:
            verdict = "Strong Match"
        elif score >= 60:
            verdict = "Good Match"
        else:
            verdict = "Weak Match"

    if score >= 80:
        st.success(f"🔥 {verdict} — {score}/100")
    elif score >= 60:
        st.warning(f"⚡ {verdict} — {score}/100")
    else:
        st.error(f"⚠️ {verdict} — {score}/100")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("Match Score", f"{score}/100")

    with c2:
        st.metric("Verdict", verdict)

    with c3:
        st.metric("CV file", result.get("cv_filename", st.session_state.get("last_uploaded_name", "resume.pdf")))

    st.progress(min(max(score / 100, 0), 1))

    txt_report = make_txt_report(result, job_description)

    d1, d2 = st.columns(2)

    with d1:
        st.download_button(
            "📥 Download TXT Report",
            data=txt_report,
            file_name="talentmatch_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with d2:
        if is_pro:
            if st.button("📄 Generate PDF Report", use_container_width=True):
                with st.spinner("Generating PDF report..."):
                    pdf_bytes = generate_pdf_report(result, job_description)

                if pdf_bytes:
                    st.session_state["pdf_report_bytes"] = pdf_bytes
                    st.success("PDF report generated.")

            if st.session_state.get("pdf_report_bytes"):
                st.download_button(
                    "Download PDF Report",
                    data=st.session_state["pdf_report_bytes"],
                    file_name="talentmatch_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.button(
                "📄 Generate PDF Report (Pro)",
                use_container_width=True,
                disabled=True,
            )
            st.caption("Upgrade to Pro to export PDF reports.")

    st.divider()

    st.markdown("## 📝 Summary")
    st.write(result.get("summary", "No summary available."))

    left, right = st.columns(2)

    with left:
        st.markdown("## ✅ Strengths")
        strengths = result.get("strengths", [])

        if strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        else:
            st.write("No strengths returned.")

    with right:
        st.markdown("## ❌ Missing Skills")
        weaknesses = result.get("weaknesses", [])

        if weaknesses:
            for item in weaknesses:
                st.markdown(f"- {item}")
        else:
            st.write("No missing skills returned.")

    st.markdown("## 💡 Recommendations")
    recommendations = result.get("recommendations", [])

    if recommendations:
        for item in recommendations:
            st.markdown(f"- {item}")
    else:
        st.write("No recommendations returned.")

    if st.query_params.get("debug") == "1":
        with st.expander("Debug analysis result"):
            st.json(result)