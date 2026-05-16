import os

import pandas as pd
import requests
import streamlit as st

st.set_page_config(
    page_title="Recruiter Mode • TalentMatch Pro",
    page_icon="🏆",
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


def score_badge(score: int) -> str:
    if score >= 85:
        return "🔥"
    if score >= 75:
        return "✅"
    if score >= 60:
        return "🟡"
    return "⚠️"


st.title("🏆 Recruiter Mode")
st.caption(
    "Upload multiple CVs and rank candidates against one job description using semantic AI matching."
)

user = st.session_state.get("user")

if not isinstance(user, dict) or not user.get("id_token"):
    st.warning("Please login before using Recruiter Mode.")
    st.stop()

uploaded_files = st.file_uploader(
    "Upload candidate CVs as PDFs",
    type=["pdf"],
    accept_multiple_files=True,
)

job_description = st.text_area(
    "Paste the job description",
    value=DEFAULT_JOB_DESCRIPTION,
    height=320,
)

if uploaded_files:
    st.info(f"Selected {len(uploaded_files)} CV file(s). Maximum allowed: 10.")

if st.button("Rank Candidates", use_container_width=True):
    if not uploaded_files:
        st.error("Please upload at least one candidate CV.")
        st.stop()

    if len(uploaded_files) > 10:
        st.error("Please upload maximum 10 CV files.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    headers = get_auth_headers()

    if not headers:
        st.error("Missing auth token. Please login again.")
        st.stop()

    files = []

    for uploaded_file in uploaded_files:
        files.append(
            (
                "files",
                (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                ),
            )
        )

    data = {
        "job_description": job_description,
    }

    with st.spinner("Ranking candidates..."):
        try:
            response = requests.post(
                f"{BACKEND_URL}/recruiter/rank-candidates",
                headers=headers,
                data=data,
                files=files,
                timeout=300,
            )
        except requests.RequestException as exc:
            st.error(f"Backend request failed: {exc}")
            st.stop()

    if response.status_code != 200:
        st.error(extract_error_message(response))

        if response.status_code == 403:
            st.warning("🚀 Recruiter Mode is a Pro feature.")
            st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="🚀")

        st.stop()

    st.session_state["recruiter_result"] = response.json()
    st.success("Candidate ranking completed.")


result = st.session_state.get("recruiter_result")

if isinstance(result, dict):
    st.divider()
    st.header("Candidate Ranking")

    total_candidates = int(result.get("total_candidates", 0) or 0)
    average_score = int(result.get("average_score", 0) or 0)
    top_candidate = result.get("top_candidate")
    candidates = result.get("candidates", [])

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Candidates", total_candidates)

    with col2:
        st.metric("Average Score", f"{average_score}/100")

    with col3:
        if isinstance(top_candidate, dict):
            st.metric("Top Candidate", top_candidate.get("filename", "-"))
        else:
            st.metric("Top Candidate", "-")

    if isinstance(top_candidate, dict):
        st.success(
            f"🏆 Top candidate: {top_candidate.get('filename')} "
            f"— {top_candidate.get('combined_score')}/100 "
            f"({top_candidate.get('verdict')})"
        )

    if candidates:
        table_rows = []

        for candidate in candidates:
            score = int(candidate.get("combined_score", 0) or 0)

            table_rows.append(
                {
                    "Rank": candidate.get("rank"),
                    "Candidate": candidate.get("filename"),
                    "Score": f"{score_badge(score)} {score}/100",
                    "Semantic": candidate.get("semantic_score"),
                    "Keyword": candidate.get("keyword_score"),
                    "Verdict": candidate.get("verdict"),
                }
            )

        df = pd.DataFrame(table_rows)

        st.markdown("## Leaderboard")
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        csv_data = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "📥 Download Ranking CSV",
            data=csv_data,
            file_name="talentmatch_candidate_ranking.csv",
            mime="text/csv",
            use_container_width=True,
        )

        st.markdown("## Candidate Details")

        for candidate in candidates:
            rank = candidate.get("rank")
            filename = candidate.get("filename")
            score = int(candidate.get("combined_score", 0) or 0)
            verdict = candidate.get("verdict", "")

            with st.expander(
                f"#{rank} — {filename} — {score}/100 — {verdict}",
                expanded=(rank == 1),
            ):
                metric_col1, metric_col2, metric_col3 = st.columns(3)

                with metric_col1:
                    st.metric("Combined Score", f"{score}/100")

                with metric_col2:
                    st.metric(
                        "Semantic Score",
                        f"{candidate.get('semantic_score', 0)}/100",
                    )

                with metric_col3:
                    st.metric(
                        "Keyword Score",
                        f"{candidate.get('keyword_score', 0)}/100",
                    )

                st.markdown("### Recruiter Summary")
                st.write(candidate.get("summary", ""))

                left, right = st.columns(2)

                with left:
                    st.markdown("### ✅ Matched Themes")
                    for item in candidate.get("matched_themes", []):
                        st.markdown(f"- {item}")

                with right:
                    st.markdown("### ❌ Missing Themes")
                    for item in candidate.get("missing_themes", []):
                        st.markdown(f"- {item}")

                st.markdown("### 💡 Recommendations")
                for item in candidate.get("recommendations", []):
                    st.markdown(f"- {item}")

                kw_left, kw_right = st.columns(2)

                with kw_left:
                    st.markdown("### Matched Keywords")
                    matched = candidate.get("matched_keywords", [])

                    if matched:
                        st.write(", ".join(matched[:30]))
                    else:
                        st.caption("No matched keywords returned.")

                with kw_right:
                    st.markdown("### Missing Keywords")
                    missing = candidate.get("missing_keywords", [])

                    if missing:
                        st.write(", ".join(missing[:30]))
                    else:
                        st.caption("No missing keywords returned.")