import json
import os

import requests
import streamlit as st

from auth_utils import (
    clear_auth,
    get_auth_headers,
    get_profile,
    is_logged_in,
    is_pro_user,
    load_profile,
    refresh_profile,
    restore_auth,
)

st.set_page_config(
    page_title="TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")


def load_config():
    return {
        "backend_url": BACKEND_URL,
    }


def api_post(path, data=None, files=None, timeout=180):
    return requests.post(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        data=data,
        files=files,
        timeout=timeout,
    )


def analyze_cv(uploaded_file, job_description):
    if not is_logged_in():
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
        response = api_post(
            "/analyze-resume",
            data=data,
            files=files,
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
    if not is_logged_in():
        st.error("Please login first.")
        return None

    try:
        data = {
            "cv_filename": result.get(
                "cv_filename",
                st.session_state.get("last_uploaded_name", "resume.pdf"),
            ),
            "score": int(result.get("score", 0)),
            "summary": result.get("summary", ""),
            "strengths_json": json.dumps(result.get("strengths", [])),
            "weaknesses_json": json.dumps(
                result.get("weaknesses")
                or result.get("missing_skills")
                or []
            ),
            "recommendations_json": json.dumps(result.get("recommendations", [])),
            "job_description": job_description,
        }

        response = api_post(
            "/reports/analysis-pdf",
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
    weaknesses = result.get("weaknesses") or result.get("missing_skills") or []
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


restore_auth()

if is_logged_in():
    refresh_profile()

profile = get_profile()
is_pro = is_pro_user()

used = int(profile.get("analyses_used", 0) or profile.get("usage", 0) or 0)
free_limit = int(profile.get("free_limit", 3) or 3)
remaining = int(profile.get("remaining", max(free_limit - used, 0)) or 0)

with st.sidebar:
    st.divider()
    st.markdown("### Authentication")

    user = st.session_state.get("user")

    if is_logged_in() and isinstance(user, dict):
        st.success("Signed in as")
        st.write(user.get("email", ""))

        if st.button("Sign out", use_container_width=True):
            clear_auth()
            st.rerun()
    else:
        st.warning("Not signed in")

        if st.button("Login", use_container_width=True):
            st.switch_page("pages/login.py")

st.markdown(
    """
# 🚀 TalentMatch Pro

### AI-powered CV analysis for modern job seekers

Optimize your CV, identify missing skills, improve ATS performance, and increase interview chances.
"""
)

st.caption("Plan: ⭐ PRO" if is_pro else "Plan: FREE")
st.caption("AI-powered CV matching, ATS keyword analysis, and job application insights.")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("AI CV Match", "GPT Powered")

with col2:
    st.metric("ATS Scanner", "Built In")

with col3:
    st.metric("Semantic Match", "Enabled" if is_pro else "Upgrade")

with col4:
    st.metric("Recruiter Mode", "Enabled" if is_pro else "Upgrade")

st.divider()

if not is_logged_in():
    st.warning("Please login before analyzing a CV.")
else:
    if is_pro:
        st.success("🚀 Pro plan active — unlimited analyses and premium tools unlocked.")
    else:
        st.info(
            f"Free plan: {used}/{free_limit} analyses used. Remaining: {remaining}"
        )
        st.progress(min(used / free_limit, 1) if free_limit else 0)

        if remaining == 0:
            st.warning("Free limit reached. Upgrade to Pro to continue.")
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
)

if uploaded_file:
    st.session_state["last_uploaded_name"] = uploaded_file.name
    st.info(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

job_description = st.text_area(
    "Paste the job description",
    value=st.session_state.get("last_job_description", ""),
    placeholder="""Paste the job description here...

Example:

Senior Backend Engineer

Requirements:
• Python
• FastAPI
• PostgreSQL
• Docker

Responsibilities:
• Build APIs
• Improve reliability
• Deploy cloud services
""",
    height=220,
)

st.session_state["last_job_description"] = job_description

analyze_disabled = (
    not is_logged_in()
    or uploaded_file is None
    or not job_description.strip()
)

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
        st.session_state.pop("pdf_report_bytes", None)
        refresh_profile()
        st.success("Analysis completed successfully.")
        st.rerun()

if not is_logged_in():
    st.info("Login first to run an analysis.")
elif uploaded_file is None:
    st.info("Upload a PDF CV to start.")
elif not job_description.strip():
    st.info("Paste a job description to continue.")

result = st.session_state.get("analysis_result")

if result:
    st.divider()
    st.markdown("## Analysis result")

    score = int(result.get("score", result.get("match_score", 0)) or 0)
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

    metric_col1, metric_col2, metric_col3 = st.columns(3)

    with metric_col1:
        st.metric("Match Score", f"{score}/100")

    with metric_col2:
        st.metric("Verdict", verdict)

    with metric_col3:
        st.metric(
            "CV file",
            result.get(
                "cv_filename",
                st.session_state.get("last_uploaded_name", "resume.pdf"),
            ),
        )

    st.progress(min(max(score / 100, 0), 1))

    txt_report = make_txt_report(result, job_description)

    download_col1, download_col2 = st.columns(2)

    with download_col1:
        st.download_button(
            "📥 Download TXT Report",
            data=txt_report,
            file_name="talentmatch_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with download_col2:
        if is_pro_user():
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

    result_col1, result_col2 = st.columns(2)

    with result_col1:
        st.markdown("## ✅ Strengths")
        strengths = result.get("strengths", [])

        if strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        else:
            st.write("No strengths returned.")

    with result_col2:
        st.markdown("## ❌ Missing Skills")
        weaknesses = result.get("weaknesses") or result.get("missing_skills") or []

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
    with st.expander("Debug app state"):
        st.json(
            {
                "backend_url": BACKEND_URL,
                "logged_in": is_logged_in(),
                "is_pro": is_pro_user(),
                "profile": get_profile(),
                "session_state_keys": list(st.session_state.keys()),
            }
        )