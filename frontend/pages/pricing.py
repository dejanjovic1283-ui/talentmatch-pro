import streamlit as st  # type: ignore

# Configure the pricing page as a standalone Streamlit page.
st.set_page_config(
    page_title="TalentMatch Pro Pricing",
    page_icon="💳",
    layout="wide",
)

st.title("💳 TalentMatch Pro Pricing")
st.caption("Simple pricing for early users.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Free")
    st.write("- Up to 3 CV analyses")
    st.write("- Basic AI score")
    st.write("- Great for testing")

with col2:
    st.subheader("Pro")
    st.write("- Unlimited analyses")
    st.write("- Full recommendation set")
    st.write("- Stored history")
    st.write("- SaaS billing flow")
