import streamlit as st

st.set_page_config(
    page_title="Admin Analytics",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Admin Analytics")
st.caption("Demo SaaS analytics dashboard for TalentMatch Pro.")

# Demo analytics data.
# Later this can be connected to a real backend admin endpoint.
analytics = {
    "total_analyses": 128,
    "active_users": 42,
    "free_users": 34,
    "pro_users": 8,
    "avg_score": 74,
    "strong_matches": 39,
    "good_matches": 61,
    "weak_matches": 28,
    "conversion_rate": 19,
    "monthly_revenue": 72,
    "top_missing_keywords": [
        "Docker",
        "FastAPI",
        "OpenAI",
        "Firebase",
        "SQL",
        "Deployment",
        "Billing",
        "SaaS",
    ],
}

st.markdown("## Business KPIs")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Analyses", analytics["total_analyses"], "+18 this week")

with col2:
    st.metric("Active Users", analytics["active_users"], "+7 this week")

with col3:
    st.metric("Pro Users", analytics["pro_users"], "+2 this week")

with col4:
    st.metric("MRR", f"${analytics['monthly_revenue']}", "+$18")


st.markdown("---")
st.markdown("## Product Quality")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Average Score", f"{analytics['avg_score']}/100")

with col2:
    st.metric("Strong Matches", analytics["strong_matches"])

with col3:
    st.metric("Good Matches", analytics["good_matches"])

with col4:
    st.metric("Weak Matches", analytics["weak_matches"])


st.markdown("---")
st.markdown("## User Segments")

segment_col1, segment_col2 = st.columns(2)

with segment_col1:
    st.markdown("### Plan Split")
    st.write(f"🟢 Free users: **{analytics['free_users']}**")
    st.write(f"🚀 Pro users: **{analytics['pro_users']}**")
    st.progress(analytics["conversion_rate"] / 100)
    st.caption(f"Conversion rate: {analytics['conversion_rate']}%")

with segment_col2:
    st.markdown("### Match Quality Split")
    total = (
        analytics["strong_matches"]
        + analytics["good_matches"]
        + analytics["weak_matches"]
    )

    strong_pct = round((analytics["strong_matches"] / total) * 100)
    good_pct = round((analytics["good_matches"] / total) * 100)
    weak_pct = round((analytics["weak_matches"] / total) * 100)

    st.write(f"🔥 Strong: **{strong_pct}%**")
    st.progress(strong_pct / 100)

    st.write(f"✅ Good: **{good_pct}%**")
    st.progress(good_pct / 100)

    st.write(f"⚠️ Weak: **{weak_pct}%**")
    st.progress(weak_pct / 100)


st.markdown("---")
st.markdown("## Top Missing Keywords")

st.caption(
    "These are the most common missing keywords across analyzed CVs. "
    "This can later power recruiter insights and CV rewrite suggestions."
)

keyword_cols = st.columns(4)

for index, keyword in enumerate(analytics["top_missing_keywords"]):
    with keyword_cols[index % 4]:
        st.info(f"❌ {keyword}")


st.markdown("---")
st.markdown("## Admin Notes")

st.success(
    "This dashboard is currently demo-mode. "
    "The next step is to connect it to a protected backend admin endpoint."
)

st.markdown(
    """
    Planned backend metrics:
    - Total users
    - Total analyses
    - Average match score
    - Most common missing skills
    - Free-to-Pro conversion
    - Revenue by month
    - Most analyzed job roles
    """
)