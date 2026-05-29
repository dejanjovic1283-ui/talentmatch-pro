import pandas as pd
import streamlit as st

from auth_utils import api_post, is_logged_in


st.set_page_config(
    page_title="Recruiter Mode • TalentMatch Pro",
    page_icon="🏆",
    layout="wide",
)


DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with Paddle
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

if not is_logged_in():
    st.warning("Please login before using Recruiter Mode.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
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
        "job_description": job_description.strip(),
    }

    with st.spinner("Ranking candidates..."):
        response = api_post(
            "/recruiter/rank-candidates",
            data=data,
            files=files,
            timeout=300,
        )

    if response.status_code != 200:
        st.error(f"Candidate ranking failed: {extract_error_message(response)}")

        if response.status_code == 403:
            st.warning("🚀 Recruiter Mode is a Pro feature.")
            st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="🚀")

        st.stop()

    try:
        payload = response.json()
    except Exception:
        st.error(f"Backend returned invalid JSON: {response.text[:1000]}")
        st.stop()

    if not isinstance(payload, dict):
        st.error("Backend returned invalid response format.")
        st.json(payload)
        st.stop()

    st.session_state["recruiter_result"] = payload
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
                    matched_themes = candidate.get("matched_themes", [])

                    if matched_themes:
                        for item in matched_themes:
                            st.markdown(f"- {item}")
                    else:
                        st.caption("No matched themes returned.")

                with right:
                    st.markdown("### ❌ Missing Themes")
                    missing_themes = candidate.get("missing_themes", [])

                    if missing_themes:
                        for item in missing_themes:
                            st.markdown(f"- {item}")
                    else:
                        st.caption("No missing themes returned.")

                st.markdown("### 💡 Recommendations")
                recommendations = candidate.get("recommendations", [])

                if recommendations:
                    for item in recommendations:
                        st.markdown(f"- {item}")
                else:
                    st.caption("No recommendations returned.")

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