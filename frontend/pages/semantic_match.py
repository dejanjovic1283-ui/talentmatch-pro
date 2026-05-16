import os

import requests
import streamlit as st

st.set_page_config(
    page_title="Semantic Match • TalentMatch Pro",
    page_icon="🧠",
    layout="wide",
)

BACKEND_URL = os.getenv(
    "BACKEND_URL",
    "https://talentmatch-backend-1283.onrender.com",
).rstrip("/")

DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

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

Nice to have:
- Experience with AI products, prompt design, and PDF/document processing
- Experience building MVPs from zero to first users
""".strip()


def get_auth_headers() -> dict[str, str]:
    user = st.session_state.get("user")

    if not isinstance(user, dict):
        return {}

    token = user.get("id_token") or user.get("idToken") or ""

    if not token:
        return {}

    return {"Authorization": f"Bearer {token}"}


def extract_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text[:1000]

    detail = payload.get("detail")

    if isinstance(detail, dict):
        return detail.get("message", str(detail))

    if isinstance(detail, str):
        return detail

    return str(payload)


def verdict_level(score: int) -> str:
    if score >= 80:
        return "success"
    if score >= 60:
        return "warning"
    return "error"


st.title("🧠 Semantic Matching")
st.caption(
    "Compare your CV and job description using OpenAI embeddings plus keyword overlap."
)

user = st.session_state.get("user")

if not isinstance(user, dict) or not user.get("id_token"):
    st.warning("Please login before using Semantic Matching.")
    st.stop()

uploaded_file = st.file_uploader(
    "Upload your CV as a PDF",
    type=["pdf"],
    accept_multiple_files=False,
)

job_description = st.text_area(
    "Paste the job description",
    value=DEFAULT_JOB_DESCRIPTION,
    height=320,
)

if uploaded_file is not None:
    file_size_kb = len(uploaded_file.getvalue()) / 1024
    st.info(f"Selected file: {uploaded_file.name} ({file_size_kb:.1f} KB)")

if st.button("Run Semantic Match", use_container_width=True):
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

    with st.spinner("Running semantic matching..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/semantic-match",
                headers=headers,
                data=data,
                files=files,
                timeout=180,
            )
        except requests.RequestException as exc:
            st.error(f"Backend request failed: {exc}")
            st.stop()

    if response.status_code != 200:
        st.error(extract_error_message(response))
        if response.status_code == 403:
            st.warning("🚀 Semantic Matching is a Pro feature.")
            st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="🚀")
        st.stop()

    st.session_state["semantic_result"] = response.json()
    st.success("Semantic match completed.")


result = st.session_state.get("semantic_result")

if isinstance(result, dict):
    st.divider()
    st.header("Semantic Match Result")

    combined_score = int(result.get("combined_score", 0) or 0)
    semantic_score = int(result.get("semantic_score", 0) or 0)
    keyword_score = int(result.get("keyword_score", 0) or 0)

    level = verdict_level(combined_score)
    verdict = result.get("verdict", "Semantic Match")

    if level == "success":
        st.success(f"🔥 {verdict} — {combined_score}/100")
    elif level == "warning":
        st.warning(f"✅ {verdict} — {combined_score}/100")
    else:
        st.error(f"⚠️ {verdict} — {combined_score}/100")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Combined Score", f"{combined_score}/100")

    with col2:
        st.metric("Semantic Score", f"{semantic_score}/100")

    with col3:
        st.metric("Keyword Score", f"{keyword_score}/100")

    st.progress(min(max(combined_score, 0), 100) / 100)

    st.markdown("## 📝 Recruiter Summary")
    st.write(result.get("summary", ""))

    left, right = st.columns(2)

    with left:
        st.markdown("## ✅ Matched Themes")
        for item in result.get("matched_themes", []):
            st.markdown(f"- {item}")

    with right:
        st.markdown("## ❌ Missing Themes")
        for item in result.get("missing_themes", []):
            st.markdown(f"- {item}")

    st.markdown("## 💡 Recommendations")
    for item in result.get("recommendations", []):
        st.markdown(f"- {item}")

    st.divider()

    kw_left, kw_right = st.columns(2)

    with kw_left:
        st.markdown("### Matched Keywords")
        matched = result.get("matched_keywords", [])

        if matched:
            st.write(", ".join(matched))
        else:
            st.caption("No matched keywords returned.")

    with kw_right:
        st.markdown("### Missing Keywords")
        missing = result.get("missing_keywords", [])

        if missing:
            st.write(", ".join(missing))
        else:
            st.caption("No missing keywords returned.")