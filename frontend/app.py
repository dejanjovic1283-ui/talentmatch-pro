import json
import time

import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar

from auth_utils import (
    api_post,
    clear_auth,
    get_profile,
    is_logged_in,
    is_pro_user,
    refresh_profile,
)


st.set_page_config(
    page_title="TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

render_sidebar()


def maybe_refresh_profile(force: bool = False) -> dict:
    if not is_logged_in():
        return {}

    now = time.time()
    last_refresh = float(st.session_state.get("profile_last_refresh", 0) or 0)

    if force or now - last_refresh > 60 or not st.session_state.get("profile"):
        profile = refresh_profile() or {}
        st.session_state["profile_last_refresh"] = now
        return profile

    return get_profile() or {}


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


def analyze_cv(uploaded_file, job_description):
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

    response = api_post(
        "/analyze-resume",
        data=data,
        files=files,
        timeout=180,
    )

    if response.status_code != 200:
        st.error(f"Analysis failed: {extract_error_message(response)}")

        if response.status_code == 403:
            st.warning("Free plan limit reached or Pro access required.")
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

        if response.status_code == 429:
            st.warning("OpenAI rate limit or quota exceeded. Please try again later.")

        return None

    try:
        payload = response.json()
    except Exception:
        st.error(f"Backend returned invalid JSON: {response.text[:1000]}")
        return None

    if not isinstance(payload, dict):
        st.error("Backend returned invalid response format.")
        st.json(payload)
        return None

    return payload


def generate_pdf_report(result: dict, job_description: str):
    data = {
        "cv_filename": result.get("cv_filename", "resume.pdf"),
        "score": str(int(result.get("score") or result.get("match_score") or 0)),
        "summary": result.get("summary", ""),
        "strengths_json": json.dumps(result.get("strengths", [])),
        "weaknesses_json": json.dumps(result.get("weaknesses") or result.get("missing_skills") or []),
        "recommendations_json": json.dumps(result.get("recommendations", [])),
        "job_description": job_description or "",
    }

    response = api_post(
        "/reports/analysis-pdf",
        data=data,
        timeout=120,
    )

    if response.status_code != 200:
        st.error(f"PDF report failed: {extract_error_message(response)}")

        if response.status_code == 403:
            st.warning("PDF reports are a Pro feature.")
            st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")

        return None

    return getattr(response, "content", None)


profile = maybe_refresh_profile()
is_pro = is_pro_user()




st.markdown("# 🚀 TalentMatch Pro")
st.markdown("### AI-powered CV analysis for modern job seekers")
st.write("Optimize your CV, identify missing skills, improve ATS performance, and increase interview chances.")

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
elif not is_pro:
    used = int(profile.get("analyses_used", 0) or 0)
    limit = int(profile.get("free_limit", 3) or 3)
    remaining = max(limit - used, 0)

    st.info(f"Free plan: {used}/{limit} analyses used. Remaining: {remaining}")

    if limit:
        st.progress(min(used / limit, 1))

    if remaining == 0:
        st.warning("Free limit reached. Upgrade to Pro to continue.")
        st.page_link("pages/pricing.py", label="🚀 Upgrade to Pro")


uploaded_file = st.file_uploader("Upload your CV as a PDF", type=["pdf"])

if uploaded_file:
    st.session_state["last_uploaded_name"] = uploaded_file.name
    st.success(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

job_description = st.text_area(
    "Paste the job description",
    value=st.session_state.get("last_job_description", ""),
    placeholder=(
        "Paste the job description here...\n\n"
        "Example:\n"
        "Senior Backend Engineer\n\n"
        "Requirements:\n"
        "• Python\n"
        "• FastAPI\n"
        "• PostgreSQL\n"
        "• Docker\n"
        "Responsibilities:\n"
        "• Build APIs\n"
        "• Improve reliability\n"
        "• Deploy cloud services"
    ),
    height=220,
)

st.session_state["last_job_description"] = job_description

job_description_filled = bool(job_description and job_description.strip())

if st.button(
    "Analyze CV",
    use_container_width=True,
    disabled=not (is_logged_in() and uploaded_file and job_description_filled),
):
    with st.spinner("Analyzing CV with AI..."):
        result = analyze_cv(uploaded_file, job_description)

    if result:
        result["cv_filename"] = (
            uploaded_file.name
            if uploaded_file
            else st.session_state.get("last_uploaded_name", "resume.pdf")
        )

        st.session_state["analysis_result"] = result
        maybe_refresh_profile(force=True)
        st.success("Analysis completed successfully.")
        st.rerun()


if not is_logged_in():
    st.info("Login first to run an analysis.")
elif not uploaded_file:
    st.info("Upload a PDF CV to start.")
elif not job_description_filled:
    st.info("Paste a job description to continue.")


result = st.session_state.get("analysis_result")

if result:
    st.divider()
    st.markdown("## Analysis result")

    score = int(result.get("score") or result.get("match_score") or 0)
    verdict = result.get("verdict") or (
        "Strong Match" if score >= 80 else "Good Match" if score >= 60 else "Weak Match"
    )

    if score >= 80:
        st.success(f"🔥 {verdict} — {score}/100")
    elif score >= 60:
        st.warning(f"⚡ {verdict} — {score}/100")
    else:
        st.error(f"⚠️ {verdict} — {score}/100")

    metrics = st.columns(3)
    metrics[0].metric("Match Score", f"{score}/100")
    metrics[1].metric("Verdict", verdict)
    metrics[2].metric(
        "CV file",
        result.get("cv_filename", st.session_state.get("last_uploaded_name", "resume.pdf")),
    )

    st.progress(min(score / 100, 1.0))

    strengths = result.get("strengths", [])
    weaknesses = result.get("weaknesses") or result.get("missing_skills") or []
    recommendations = result.get("recommendations", [])

    txt_lines = [
        "TalentMatch Pro CV Analysis Report",
        "=" * 40,
        "",
        f"Score: {score}/100",
        f"Verdict: {verdict}",
        "",
        "Summary",
        "-" * 20,
        result.get("summary", ""),
        "",
        "Strengths",
        "-" * 20,
    ]

    txt_lines += [f"- {s}" for s in strengths] or ["No strengths returned."]
    txt_lines += ["", "Missing Skills", "-" * 20]
    txt_lines += [f"- {w}" for w in weaknesses] or ["No missing skills returned."]
    txt_lines += ["", "Recommendations", "-" * 20]
    txt_lines += [f"- {r}" for r in recommendations] or ["No recommendations returned."]
    txt_lines += ["", "Job Description", "-" * 20, job_description]

    txt_report = "\n".join(txt_lines)

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
        if is_pro:
            pdf_bytes = generate_pdf_report(result, job_description or "")

            if pdf_bytes:
                st.download_button(
                    "📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name="talentmatch_report.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
        else:
            st.button("📄 Download PDF Report (Pro)", use_container_width=True, disabled=True)
            st.caption("Upgrade to Pro to export PDF reports.")

    st.divider()

    st.markdown("## 📝 Summary")
    st.write(result.get("summary", "No summary available."))

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("## ✅ Strengths")
        if strengths:
            for item in strengths:
                st.markdown(f"- {item}")
        else:
            st.write("No strengths returned.")

    with col2:
        st.markdown("## ❌ Missing Skills")
        if weaknesses:
            for item in weaknesses:
                st.markdown(f"- {item}")
        else:
            st.write("No missing skills returned.")

    st.markdown("## 💡 Recommendations")

    if recommendations:
        for item in recommendations:
            st.markdown(f"- {item}")
    else:
        st.write("No recommendations returned.")

render_footer()