import streamlit as st

st.set_page_config(page_title="Pricing", page_icon="💳")

st.title("💳 Pricing")

st.markdown("## Choose your plan")

# --- FREE PLAN ---
st.markdown("### 🟢 Free Plan")

st.markdown("""
- ✔ 3 CV analyses
- ✔ AI match score
- ✔ Basic recommendations
- ❌ No history
- ❌ No advanced insights
""")

st.button("Current plan", disabled=True)

st.markdown("---")

# --- PRO PLAN ---
st.markdown("### 🚀 Pro Plan")

st.markdown("""
- ✔ Unlimited CV analyses
- ✔ AI match score
- ✔ Advanced recommendations
- ✔ Full history
- ✔ Priority processing
""")

st.markdown("### 💰 $9 / month")

# 👉 OVDE ubaci svoj Lemon Squeezy link
LEMON_CHECKOUT_URL = "https://your-checkout-link.lemonsqueezy.com"

st.markdown(
    f"""
    <a href="{LEMON_CHECKOUT_URL}" target="_blank">
        <button style="
            background-color:#FF4B4B;
            color:white;
            padding:10px 20px;
            border:none;
            border-radius:5px;
            font-size:16px;
            cursor:pointer;">
            Upgrade to Pro 🚀
        </button>
    </a>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# --- FAQ ---
st.markdown("## ❓ FAQ")

st.markdown("""
**How does billing work?**  
You are charged monthly and can cancel anytime.

**What happens if I reach the free limit?**  
You will need to upgrade to continue using the service.

**Can I cancel anytime?**  
Yes, no contracts, cancel whenever you want.
""")