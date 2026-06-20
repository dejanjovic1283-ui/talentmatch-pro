import streamlit as st

from auth_utils import api_get, is_logged_in


st.set_page_config(page_title="History • TalentMatch Pro", page_icon="📜", layout="wide")

st.title("📜 Analysis History")
st.caption("View your previous CV analyses and reports.")


TYPE_LABELS = {
    "cv_analysis": "CV Analysis",
    "ats_checker": "ATS Checker",
    "ats": "ATS Checker",
    "semantic_match": "Semantic Match",
    "recruiter_mode": "Recruiter Mode",
}


def history_label(item: dict) -> str:
    analysis_type = str(item.get("analysis_type") or "cv_analysis").strip().lower()
    return TYPE_LABELS.get(analysis_type, analysis_type.replace("_", " ").title())


def parse_history_response(response):
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "")

    if status_code != 200:
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("error") or payload
            return None, f"Failed to load history: {status_code} - {detail}"
        except Exception:
            return None, f"Failed to load history: {status_code} - {text[:1000]}"

    if content_type and "application/json" not in content_type:
        return None, f"Backend returned non-JSON response: {text[:1000]}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    if isinstance(payload, list):
        return payload, None

    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("history") or payload.get("data") or []
        if isinstance(items, list):
            return items, None

    return None, "Backend returned invalid history format."


if not is_logged_in():
    st.warning("Please login before viewing history.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

if st.button("Refresh history", use_container_width=True):
    st.session_state.pop("history_items", None)
    st.rerun()

if "history_items" not in st.session_state:
    with st.spinner("Loading history..."):
        resp = api_get("/history", timeout=90)
        items, error = parse_history_response(resp)

        if error:
            st.error(error)
            st.stop()

        st.session_state["history_items"] = items


items = st.session_state.get("history_items", [])

if not items:
    st.info("No analyses yet.")
    st.page_link("app.py", label="🚀 Run your first CV analysis")
    st.stop()


for idx, item in enumerate(items, start=1):
    if not isinstance(item, dict):
        continue

    score = item.get("score") or item.get("match_score") or 0
    verdict = history_label(item)

    cv_file = (
        item.get("cv_filename")
        or item.get("cv_file")
        or item.get("filename")
        or item.get("file_name")
        or "CV"
    )

    created_at = item.get("created_at") or item.get("date") or ""

    strengths = (
        item.get("matched_skills")
        or item.get("strengths")
        or item.get("matched_keywords")
        or []
    )

    missing = (
        item.get("missing_skills")
        or item.get("missing_keywords")
        or item.get("weaknesses")
        or []
    )

    recommendations = item.get("recommendations") or []
    summary = item.get("summary") or ""

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])

        col1.subheader(f"{idx}. {cv_file}")

        if created_at:
            col1.caption(str(created_at))

        col2.metric("Score", f"{score}/100")
        col3.metric("Verdict", verdict)

        if summary:
            st.markdown("**Summary**")
            st.write(summary)

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**✅ Strengths / Matched Skills**")
            if strengths:
                for s in strengths:
                    st.markdown(f"- {s}")
            else:
                st.caption("No matched skills returned.")

        with c2:
            st.markdown("**❌ Missing Skills**")
            if missing:
                for m in missing:
                    st.markdown(f"- {m}")
            else:
                st.caption("No missing skills returned.")

        if recommendations:
            st.markdown("**💡 Recommendations**")
            for r in recommendations:
                st.markdown(f"- {r}")