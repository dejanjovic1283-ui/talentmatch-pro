from __future__ import annotations

from typing import Any, Dict, List, Tuple, cast

import pandas as pd
import streamlit as st

from auth_utils import api_post, is_logged_in
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero, safe_html


st.set_page_config(page_title="Recruiter Mode • TalentMatch Pro", page_icon="🏆", layout="wide")
apply_global_styles()
render_sidebar()


DEFAULT_JOB_DESCRIPTION = """
Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with PayPal
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


UploadFileTuple = Tuple[str, Tuple[str, bytes, str]]


def normalize_response(raw: Any) -> Any:
    """Support api_post implementations that return response or (response, error)."""
    if isinstance(raw, tuple):
        if len(raw) >= 2 and raw[1]:
            raise RuntimeError(str(raw[1]))
        if len(raw) >= 1:
            return raw[0]
        raise RuntimeError("Empty response from backend.")
    return raw


def extract_error_message(response: Any) -> str:
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        number = int(float(value))
    except Exception:
        return default
    return max(0, min(number, 100))


def score_badge(score: int) -> str:
    if score >= 85:
        return "🔥"
    if score >= 75:
        return "✅"
    if score >= 60:
        return "🟡"
    return "⚠️"


def extract_list(data: Dict[str, Any], key: str) -> List[str]:
    value = data.get(key, [])
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return []


def render_chip_group(title: str, items: List[str], empty_text: str, icon: str, green: bool = False) -> None:
    pill_class = "tm-pill tm-pill-green" if green else "tm-pill"
    if items:
        content = "".join(f"<span class='{pill_class}'>{safe_html(item)}</span>" for item in items[:35])
    else:
        content = f"<div class='tm-muted'>{safe_html(empty_text)}</div>"

    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div>{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_candidate_details(candidate: Dict[str, Any], expanded: bool) -> None:
    rank = candidate.get("rank", "-")
    filename = str(candidate.get("filename") or "Candidate")
    score = safe_int(candidate.get("combined_score"))
    verdict = str(candidate.get("verdict") or "")

    with st.expander(f"#{rank} — {filename} — {score}/100 — {verdict}", expanded=expanded):
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        with metric_col1:
            st.metric("Combined Score", f"{score}/100")
        with metric_col2:
            st.metric("Semantic Score", f"{safe_int(candidate.get('semantic_score'))}/100")
        with metric_col3:
            st.metric("Keyword Score", f"{safe_int(candidate.get('keyword_score'))}/100")

        summary = str(candidate.get("summary") or "No recruiter summary returned.")
        st.markdown(
            f"""
            <div class="tm-card" style="margin-top:1rem;margin-bottom:1rem">
                <div class="tm-card-title">📝 Recruiter summary</div>
                <div class="tm-muted">{safe_html(summary)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        left, right = st.columns(2)
        with left:
            render_chip_group("Matched themes", extract_list(candidate, "matched_themes"), "No matched themes returned.", "✅", True)
        with right:
            render_chip_group("Missing themes", extract_list(candidate, "missing_themes"), "No missing themes returned.", "🎯", False)

        recommendations = extract_list(candidate, "recommendations")
        st.markdown("### 💡 Recommendations")
        if recommendations:
            for index, item in enumerate(recommendations, start=1):
                st.markdown(
                    f"""
                    <div class="tm-card" style="margin-bottom:.75rem">
                        <div class="tm-kicker">Recommendation {index}</div>
                        <div class="tm-muted">{safe_html(item)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No recommendations returned.")

        kw_left, kw_right = st.columns(2)
        with kw_left:
            render_chip_group("Matched keywords", extract_list(candidate, "matched_keywords"), "No matched keywords returned.", "✅", True)
        with kw_right:
            render_chip_group("Missing keywords", extract_list(candidate, "missing_keywords"), "No missing keywords returned.", "❌", False)


def render_results(result: Dict[str, Any]) -> None:
    total_candidates = int(result.get("total_candidates") or 0)
    average_score = safe_int(result.get("average_score"))
    top_candidate = result.get("top_candidate")
    candidates = result.get("candidates", [])

    st.success("Candidate ranking completed.")
    st.markdown('<div class="tm-section-title">Candidate ranking result</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Candidates", total_candidates)
    with col2:
        st.metric("Average Score", f"{average_score}/100")
    with col3:
        if isinstance(top_candidate, dict):
            st.metric("Top Candidate", str(top_candidate.get("filename", "-")))
        else:
            st.metric("Top Candidate", "-")

    if isinstance(top_candidate, dict):
        top_score = safe_int(top_candidate.get("combined_score"))
        st.markdown(
            f"""
            <div class="tm-card" style="margin:1rem 0">
                <div class="tm-kicker">Best match</div>
                <div class="tm-card-title">🏆 {safe_html(top_candidate.get('filename', '-'))} — {top_score}/100</div>
                <div class="tm-muted">{safe_html(top_candidate.get('verdict', 'Top ranked candidate'))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if not isinstance(candidates, list) or not candidates:
        st.info("No candidate results returned.")
        return

    table_rows: List[Dict[str, Any]] = []
    candidate_dicts: List[Dict[str, Any]] = []
    for candidate_raw in candidates:
        if not isinstance(candidate_raw, dict):
            continue
        candidate: Dict[str, Any] = candidate_raw
        candidate_dicts.append(candidate)
        score = safe_int(candidate.get("combined_score"))
        table_rows.append(
            {
                "Rank": candidate.get("rank"),
                "Candidate": candidate.get("filename"),
                "Score": f"{score_badge(score)} {score}/100",
                "Semantic": f"{safe_int(candidate.get('semantic_score'))}/100",
                "Keyword": f"{safe_int(candidate.get('keyword_score'))}/100",
                "Verdict": candidate.get("verdict"),
            }
        )

    st.markdown('<div class="tm-section-title">Leaderboard</div>', unsafe_allow_html=True)
    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Ranking CSV",
        data=csv_data,
        file_name="talentmatch_candidate_ranking.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown('<div class="tm-section-title">Candidate details</div>', unsafe_allow_html=True)
    for candidate in candidate_dicts:
        render_candidate_details(candidate, expanded=(candidate.get("rank") == 1))


render_hero(
    "Recruiter intelligence",
    "Recruiter Mode",
    "Upload up to 10 candidate CVs and rank them against one job description with semantic AI scoring and recruiter-ready summaries.",
    "🏆",
)

if not is_logged_in():
    st.warning("Please login before using Recruiter Mode.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

st.markdown('<div class="tm-section-title">Rank candidates</div>', unsafe_allow_html=True)
left, right = st.columns([1, 1.25])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📚 Candidate CVs</div>
            <div class="tm-muted">Upload multiple PDF CVs. Maximum allowed: 10 candidates per ranking run.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    uploaded_files = st.file_uploader(
        "Upload candidate CVs as PDFs",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if uploaded_files:
        st.success(f"Selected {len(uploaded_files)} CV file(s). Maximum allowed: 10.")

with right:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🧾 Job description</div>
            <div class="tm-muted">Paste the target job description once. Every uploaded candidate is ranked against this role.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    job_description = st.text_area("Paste the job description", value=DEFAULT_JOB_DESCRIPTION, height=330)

if st.button(
    "🚀 Rank Candidates",
    use_container_width=True,
    disabled=not uploaded_files or not job_description.strip(),
):
    if not uploaded_files:
        st.error("Please upload at least one candidate CV.")
        st.stop()

    if len(uploaded_files) > 10:
        st.error("Please upload maximum 10 CV files.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste a job description.")
        st.stop()

    files_payload: List[UploadFileTuple] = []
    for uploaded_file in uploaded_files:
        files_payload.append(("files", (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")))

    data = {"job_description": job_description.strip()}

    with st.spinner("Ranking candidates..."):
        try:
            raw_response = api_post(
                "/recruiter/rank-candidates",
                data=data,
                files=cast(Any, files_payload),
                timeout=300,
            )
            response = normalize_response(raw_response)
        except Exception as exc:
            st.error(f"Candidate ranking failed: {exc}")
            st.stop()

    status_code = getattr(response, "status_code", None)
    if status_code != 200:
        st.error(f"Candidate ranking failed: {extract_error_message(response)}")
        if status_code == 403:
            st.warning("🚀 Recruiter Mode is a Pro feature.")
            st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="🚀")
        st.stop()

    try:
        payload = response.json()
    except Exception:
        response_text = getattr(response, "text", "") or ""
        st.error(f"Backend returned invalid JSON: {response_text[:1000]}")
        st.stop()

    if not isinstance(payload, dict):
        st.error("Backend returned invalid response format.")
        st.json(payload)
        st.stop()

    st.session_state["recruiter_result"] = payload

result = st.session_state.get("recruiter_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
