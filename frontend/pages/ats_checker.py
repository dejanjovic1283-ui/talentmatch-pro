from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from auth_utils import api_post, is_logged_in


st.set_page_config(page_title="ATS Checker", page_icon="🎯", layout="wide")


def normalize_response(raw: Any) -> Tuple[Optional[Any], Optional[str]]:
    """Normalize different api_post return formats into response and error."""
    if isinstance(raw, tuple):
        if len(raw) >= 2:
            return raw[0], raw[1]
        if len(raw) == 1:
            return raw[0], None
        return None, "Empty response from backend."

    return raw, None


def response_to_json(response: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Convert backend response into a JSON dictionary with clear error messages."""
    if response is None:
        return None, "No response from backend."

    if isinstance(response, dict):
        return response, None

    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "")

    if status_code is not None and status_code >= 400:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail") or payload.get("error") or payload
            else:
                detail = payload
            return None, f"ATS check failed: {status_code} - {detail}"
        except Exception:
            return None, f"ATS check failed: {status_code} - {text[:1000]}"

    if content_type and "application/json" not in content_type:
        return None, f"Backend returned non-JSON response: {text[:1000]}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    if not isinstance(payload, dict):
        return None, "Backend response is not a JSON object."

    if payload.get("error") or payload.get("detail"):
        return None, str(payload.get("error") or payload.get("detail"))

    return payload, None


def extract_list(data: Dict[str, Any], *keys: str) -> List[str]:
    """Extract a string list from the first existing key."""
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [str(item) for item in value if item]
    return []


def render_results(data: Dict[str, Any]) -> None:
    """Render ATS checker results."""
    matched_keywords = extract_list(
        data,
        "matched_keywords",
        "matched",
        "found_keywords",
        "strengths",
    )

    missing_keywords = extract_list(
        data,
        "missing_keywords",
        "missing",
        "missing_skills",
    )

    recommendations = extract_list(
        data,
        "recommendations",
        "tips",
        "suggestions",
    )

    score = data.get("score") or data.get("match_score") or data.get("ats_score")

    st.success("ATS check completed.")

    if score is not None:
        st.metric("ATS Score", f"{score}%")

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


st.title("🎯 ATS Keyword Checker")
st.caption(
    "Check which job-description keywords your CV already covers and which ones are missing."
)

if not is_logged_in():
    st.warning("Please login before using ATS Checker.")
    st.stop()

uploaded_file = st.file_uploader("Upload your CV as a PDF", type=["pdf"])

job_description = st.text_area(
    "Paste the job description",
    height=260,
    placeholder=(
        "Example:\n"
        "Founding Full-Stack AI SaaS Engineer\n\n"
        "What we are looking for:\n"
        "- Python\n"
        "- FastAPI\n"
        "- PostgreSQL\n"
        "- Docker\n"
        "- Firebase\n"
        "- PayPal\n"
        "- Render deployment"
    ),
)

if uploaded_file is not None:
    st.info(f"Selected file: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

run_clicked = st.button(
    "Run ATS Checker",
    use_container_width=True,
    disabled=uploaded_file is None or not job_description.strip(),
)

if run_clicked:
    cv_file = uploaded_file

    if cv_file is None:
        st.error("Please upload your CV as a PDF.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste the job description.")
        st.stop()

    files = {
        "file": (
            cv_file.name,
            cv_file.getvalue(),
            "application/pdf",
        )
    }

    data = {
        "job_description": job_description.strip(),
    }

    with st.spinner("Running ATS keyword check..."):
        raw_response = api_post(
            "/ats-test",
            data=data,
            files=files,
        )

    response, call_error = normalize_response(raw_response)

    if call_error:
        st.error(f"ATS check failed: {call_error}")
        st.stop()

    payload, parse_error = response_to_json(response)

    if parse_error:
        st.error(parse_error)
        st.stop()

    if not payload:
        st.error("ATS check failed: empty backend response.")
        st.stop()

    render_results(payload)
