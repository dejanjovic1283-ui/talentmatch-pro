import streamlit as st

from auth_utils import clear_auth, is_logged_in, is_pro_user, refresh_profile


def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎯 TalentMatch Pro")
        st.caption("AI-powered CV analysis and ATS optimization")

        st.divider()

        st.page_link("app.py", label="🏠 Dashboard")
        st.page_link("pages/cv_analysis.py", label="📄 CV Analysis")
        st.page_link("pages/ats_checker.py", label="📋 ATS Checker")
        st.page_link("pages/cv_rewrite.py", label="✍ CV Rewrite")

        if is_pro_user():
            st.page_link("pages/semantic_match.py", label="🧠 Semantic Match")
            st.page_link("pages/recruiter_mode.py", label="👥 Recruiter Mode")
        else:
            st.page_link("pages/pricing.py", label="🧠 Semantic Match 🔒")
            st.page_link("pages/pricing.py", label="👥 Recruiter Mode 🔒")

        st.page_link("pages/history.py", label="📜 History")
        st.page_link("pages/pricing.py", label="💳 Pricing")
        st.page_link("pages/account.py", label="⚙ Account")

        st.divider()

        st.page_link("pages/terms.py", label="📃 Terms")
        st.page_link("pages/privacy.py", label="🔒 Privacy")
        st.page_link("pages/refund.py", label="💸 Refund")

        st.divider()

        st.markdown("### Company")
        st.page_link("pages/about.py", label="ℹ About Us")
        st.page_link("pages/contact.py", label="📬 Contact Us")

        st.divider()

        if is_logged_in():
            email = (
                st.session_state.get("email")
                or st.session_state.get("user_email")
                or st.session_state.get("user", {}).get("email", "")
            )

            st.success(f"Signed in as\n\n{email}")

            if st.button("🔄 Refresh profile", use_container_width=True):
                refresh_profile()
                st.rerun()

            if st.button("🚪 Logout", use_container_width=True):
                clear_auth()
                st.rerun()
        else:
            st.info("Not signed in")
            st.page_link("pages/login.py", label="🔐 Login")
            st.page_link("pages/register.py", label="📝 Register")