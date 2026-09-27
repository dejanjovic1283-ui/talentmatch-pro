import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar


st.set_page_config(page_title="Contact Us", page_icon="📬", layout="wide")

render_sidebar()

st.title("📬 Contact Us")
st.caption("TalentMatch Pro support, billing, account assistance, and general inquiries")

st.markdown(
    """
## How Can We Help?

**Last Updated: September 2026**

Contact TalentMatch Pro for technical support, billing questions, refund requests, account issues, partnership opportunities, or general product questions.

---

## 📩 Support Email

**Email:** [support@talentmatchcv.com](mailto:support@talentmatchcv.com)

Please include enough information to understand the issue, but do not send passwords, payment card details, or unnecessary sensitive personal information.

---

## 💳 Pro Plan and Billing

The Pro plan is currently available for **$19 USD per month** as a recurring subscription billed and managed through **PayPal**.

Use the Pricing page to review the plan and check the current subscription options. Existing recurring subscriptions are managed through PayPal.
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

**Project:** TalentMatch Pro<br>
**Owner:** Dejan Jović<br>
**Country:** Serbia<br>
**Email:** [support@talentmatchcv.com](mailto:support@talentmatchcv.com)

---

## 🛠️ Topics We Can Help With

- Technical support
- Account, login, or registration issues
- Billing and subscription status questions
- Refund requests
- CV analysis and report export questions
- Partnership opportunities
- General product questions

---

Thank you for using TalentMatch Pro.
"""
)

render_footer()
