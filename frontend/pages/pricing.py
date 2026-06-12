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
    "Pro subscriptions are currently available via manual activation. Contact us to request Pro access."
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
            st.warning("To activate Pro, please submit a Pro Plan request.")

            subject = "TalentMatch Pro - Pro Plan Request"

            body = """
Hello,

I would like to request access to the TalentMatch Pro plan.

Name:
Email:

Thank you.

Kind regards,
"""

            mailto = (
                f"mailto:dejan.jovic1283@gmail.com"
                f"?subject={subject.replace(' ', '%20')}"
                f"&body={body.replace(' ', '%20').replace(chr(10), '%0D%0A')}"
            )

            st.link_button(
                "📬 Request Pro Access",
                mailto,
                use_container_width=True,
            )

st.divider()

st.markdown("## 📬 Contact")

st.markdown(
    """
**TalentMatch Pro**

📧 Email: dejan.jovic1283@gmail.com

🚀 Pro Plan Requests: Available

💬 Response Time: 24-48 Hours
"""
)