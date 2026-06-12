import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile
from components.sidebar import render_sidebar


st.set_page_config(
    page_title="Account • TalentMatch Pro",
    page_icon="⚙",
    layout="wide",
)

render_sidebar()

if is_logged_in():
    refresh_profile()

email = (
    st.session_state.get("email")
    or st.session_state.get("user_email")
    or st.session_state.get("user", {}).get("email", "")
)

user_id = (
    st.session_state.get("user_id")
    or st.session_state.get("id")
    or st.session_state.get("profile", {}).get("id", "")
)

is_pro = is_pro_user()
plan_name = "PRO" if is_pro else "FREE"

st.markdown("# ⚙ Account")
st.caption("Manage your TalentMatch Pro account, subscription, and session.")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.caption("Plan")
    st.markdown(f"## {plan_name}")

with col2:
    st.caption("Status")
    st.markdown("## Signed in" if is_logged_in() else "## Not signed in")

with col3:
    st.caption("Access")
    st.markdown("## Pro enabled" if is_pro else "## Free access")

st.markdown("## Profile")

if is_logged_in():
    st.write(f"**Email:** {email or 'Unknown'}")

    if user_id:
        st.write(f"**User ID:** {user_id}")

    st.markdown("## Subscription")

    if is_pro:
        st.success("🚀 You are currently on the Pro plan.")
    else:
        st.info("You are currently on the Free plan.")
        st.page_link("pages/pricing.py", label="🚀 Upgrade / Request Pro Access")

    st.divider()

    col_a, col_b = st.columns(2)

    with col_a:
        if st.button("🔄 Refresh profile", use_container_width=True):
            refresh_profile()
            st.rerun()

    with col_b:
        if st.button("🚪 Logout", use_container_width=True):
            clear_auth()
            st.rerun()

else:
    st.warning("You are not signed in.")
    st.page_link("pages/login.py", label="🔐 Login")
    st.page_link("pages/register.py", label="📝 Register")
