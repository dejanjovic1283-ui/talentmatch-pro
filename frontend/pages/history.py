import requests
import streamlit as st # pyright: ignore[reportMissingImports]

from app import HISTORY_ENDPOINT, get_auth_headers, load_config

st.set_page_config(
    page_title="Analysis History",
    page_icon="📜",
    layout="wide",
)

config = load_config()

st.title("📜 Analysis History")

user = st.session_state.get("user")
if not isinstance(user, dict) or not user.get("id_token"):
    st.warning("Please sign in first.")
    st.stop()

history = []

try:
    response = requests.get(
        f"{config.backend_url}{HISTORY_ENDPOINT}",
        headers=get_auth_headers(),
        timeout=30,
    )

    if response.status_code != 200:
        st.error(response.text)
        st.stop()

    history = response.json()

except requests.RequestException as exc:
    st.error(f"Backend request failed: {exc}")
    st.stop()

for item in history:
    score = int(item.get("score", 0) or 0)

    if score >= 80:
        badge = "🔥 Strong Match"
    elif score >= 60:
        badge = "✅ Good Match"
    else:
        badge = "⚠️ Weak Match"

    with st.container(border=True):
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.subheader(item.get("cv_filename", "Unknown CV"))

        with col2:
            st.metric("Score", f"{score}/100")

        with col3:
            st.markdown(f"### {badge}")

        st.markdown("#### Summary")
        st.write(item.get("summary", ""))

        st.markdown("#### Strengths")
        for strength in item.get("matched_skills", []):
            st.write(f"✅ {strength}")

        st.markdown("#### Missing Skills")
        for skill in item.get("missing_skills", []):
            st.write(f"❌ {skill}")

        st.markdown("#### Recommendations")
        for rec in item.get("recommendations", []):
            st.write(f"💡 {rec}")

        st.caption(f"Created at: {item.get('created_at', '')}")