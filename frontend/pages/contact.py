import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar


st.set_page_config(page_title="Contact Us", page_icon="📬", layout="wide")

render_sidebar()

st.title("📬 Contact Us")
st.caption("TalentMatch Pro support, billing, account assistance, and general inquiries")

st.markdown(
    """
# TalentMatch Pro – Contact Us

Need help with TalentMatch Pro?  
You can contact us for technical support, billing questions, refund requests, account issues, partnership opportunities, or general product questions.

---

## 📩 Support Email

**Email:** support@talentmatchcv.com

---

## 💳 Pro Plan & Billing

TalentMatch Pro is available for **$19/month** as a recurring **PayPal** subscription.

Use the Pricing page to review the plan, subscribe, or check your current Pro access. Existing subscriptions are managed through PayPal.
"""
)

st.page_link("pages/pricing.py", label="💳 Open Pricing & Billing")

st.markdown(
    """
---

## ⏱️ Response Time

We usually respond within:

- 24–48 business hours

Response time may be longer during weekends or holidays.

---

## 🏢 Business Information

**Project:** TalentMatch Pro  
**Owner:** Dejan Jovic  
**Country:** Serbia  
**Email:** support@talentmatchcv.com

---

## 🛠️ Topics We Can Help With

- Technical support
- Account issues
- Login or registration issues
- Billing questions
- Subscription status questions
- Refund requests
- CV analysis questions
- Report export questions
- Partnership opportunities
- General questions

---

## 🔐 Important Note

Please do not send sensitive personal information by email unless it is necessary for support.

For CV-related support, describe the issue clearly and include only the information needed to understand the problem.

---

Thank you for using TalentMatch Pro.
"""
)

render_footer()
