import streamlit as st

from auth_utils import (
    is_logged_in,
    is_pro_user,
    refresh_profile,
)

st.set_page_config(
    page_title="Pricing • TalentMatch Pro",
    page_icon="🚀",
    layout="wide",
)

if is_logged_in():
    refresh_profile()

is_pro = is_pro_user()

st.markdown("# 🚀 TalentMatch Pro Pricing")

st.info(
    "Online payments are temporarily unavailable while we migrate to a new billing provider."
)

free_col, pro_col = st.columns(2)

with free_col:
    with st.container(border=True):
        st.markdown("## Free")
        st.markdown("### $0/month")

        st.markdown(
            """
✅ 3 CV analyses

✅ ATS Checker

✅ TXT Export

❌ PDF Reports

❌ CV Rewrite AI

❌ Semantic Match

❌ Recruiter Mode

❌ Unlimited Analyses
"""
        )

with pro_col:
    with st.container(border=True):
        st.markdown("## Pro")
        st.markdown("### $9/month")

        st.markdown(
            """
✅ Unlimited CV Analyses

✅ PDF Reports

✅ CV Rewrite AI

✅ Semantic Match

✅ Recruiter Mode

✅ Candidate Ranking

✅ Saved History

✅ Recruiter Reports
"""
        )

        if is_pro:
            st.success("🚀 You already have Pro.")
        else:
            st.warning(
                "Automatic payments are temporarily unavailable."
            )

            st.link_button(
                "📬 Contact for Pro Access",
                "mailto:dejan.jovic1283@gmail.com?subject=TalentMatch%20Pro%20Access",
                use_container_width=True,
            )

st.divider()

st.markdown("## 📬 Contact")

st.markdown(
    """
**TalentMatch Pro**

Email: dejan.jovic1283@gmail.com

Billing Provider Migration: In Progress
"""
)