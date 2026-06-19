import streamlit as st

from components.footer import render_footer
from components.sidebar import render_sidebar

st.set_page_config(page_title="Contact Us", page_icon="📬", layout="wide")

render_sidebar()

st.title("📬 Contact Us")
st.caption("TalentMatch Pro support, billing, Pro plan requests, and general inquiries")

st.markdown("""
# TalentMatch Pro – Contact Us

Need help with TalentMatch Pro?  
You can contact us for support, billing questions, refund requests, account issues, partnership opportunities, or Pro plan access.

---

## 📩 Support Email

**Email:** support@talentmatchcv.com

---

## 🚀 Pro Plan Requests

If you want access to the TalentMatch Pro plan, please send an email with the following subject:

**Subject:** TalentMatch Pro - Pro Plan Request

Suggested message:

```text
Hello,

I would like to request access to the TalentMatch Pro plan.

Name:
Email:

Thank you.

Kind regards,
```

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
- Pro plan access
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
""")

render_footer()