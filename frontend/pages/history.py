import streamlit as st

from auth_utils import api_get, is_logged_in, restore_auth

st.set_page_config(page_title="History • TalentMatch Pro", page_icon="📜", layout="wide")

restore_auth()

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
            response = api_get("/history")

            if response.status_code == 200:
                data = response.json()

                if isinstance(data, list):
                    st.session_state["history_items"] = data
                else:
                    st.session_state["history_items"] = data.get("items", data.get("history", []))

            else:
                st.error(f"Failed to load history: {response.status_code}")
                st.code(response.text)
                st.stop()

        except Exception as exc:
            st.error(f"Failed to load history: {exc}")
            st.stop()

items = st.session_state.get("history_items", [])

if not items:
    st.info("No analyses yet.")
    st.page_link("app.py", label="🚀 Run your first CV analysis")
    st.stop()

for index, item in enumerate(items, start=1):
    score = item.get("score") or item.get("match_score") or 0
    verdict = item.get("verdict") or "Analysis"
    cv_file = item.get("cv_file") or item.get("filename") or item.get("file_name") or "CV"
    created_at = item.get("created_at") or item.get("date") or ""

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.subheader(f"{index}. {cv_file}")
            if created_at:
                st.caption(created_at)

        with col2:
            st.metric("Score", f"{score}/100")

        with col3:
            st.metric("Verdict", verdict)

        summary = item.get("summary")
        if summary:
            st.markdown("**Summary**")
            st.write(summary)

        strengths = item.get("strengths") or []
        missing = item.get("missing_skills") or item.get("missing_keywords") or []
        recommendations = item.get("recommendations") or []

        col1, col2 = st.columns(2)

        with col1:
            if strengths:
                st.markdown("**✅ Strengths**")
                for strength in strengths:
                    st.markdown(f"- {strength}")

        with col2:
            if missing:
                st.markdown("**❌ Missing**")
                for gap in missing:
                    st.markdown(f"- {gap}")

        if recommendations:
            st.markdown("**💡 Recommendations**")
            for rec in recommendations:
                st.markdown(f"- {rec}")