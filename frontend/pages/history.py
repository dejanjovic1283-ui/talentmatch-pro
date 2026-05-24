import streamlit as st
from auth_utils import api_get, is_logged_in

st.set_page_config(page_title="History • TalentMatch Pro", page_icon="📜", layout="wide")

st.title("📜 Analysis History")
st.caption("View your previous CV analyses and reports.")

if not is_logged_in():
    st.warning("Please login before viewing history.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

if st.button("Refresh history", use_container_width=True):
    st.session_state.pop("history_items", None)
    st.rerun()

if "history_items" not in st.session_state:
    with st.spinner("Loading history..."):
        try:
            resp = api_get("/history", timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    st.session_state["history_items"] = data
                else:
                    st.session_state["history_items"] = data.get("items", data.get("history", []))
            else:
                st.error(f"Failed to load history: {resp.status_code}")
                st.code(resp.text)
                st.stop()
        except Exception as exc:
            st.error(f"Failed to load history: {exc}")
            st.stop()

items = st.session_state.get("history_items", [])
if not items:
    st.info("No analyses yet.")
    st.page_link("app.py", label="🚀 Run your first CV analysis")
    st.stop()

for idx, item in enumerate(items, start=1):
    score = item.get("score") or item.get("match_score") or 0
    verdict = item.get("verdict") or "Analysis"
    cv_file = item.get("cv_file") or item.get("filename") or item.get("file_name") or "CV"
    created_at = item.get("created_at") or item.get("date") or ""
    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        col1.subheader(f"{idx}. {cv_file}")
        if created_at: col1.caption(created_at)
        col2.metric("Score", f"{score}/100")
        col3.metric("Verdict", verdict)

        summary = item.get("summary")
        if summary:
            st.markdown("**Summary**")
            st.write(summary)

        strengths = item.get("strengths") or []
        missing = item.get("missing_skills") or item.get("missing_keywords") or []
        recommendations = item.get("recommendations") or []

        c1, c2 = st.columns(2)
        with c1:
            if strengths:
                st.markdown("**✅ Strengths**")
                for s in strengths: st.markdown(f"- {s}")
        with c2:
            if missing:
                st.markdown("**❌ Missing**")
                for m in missing: st.markdown(f"- {m}")
        if recommendations:
            st.markdown("**💡 Recommendations**")
            for r in recommendations: st.markdown(f"- {r}")