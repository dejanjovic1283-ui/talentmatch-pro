import streamlit as st

st.set_page_config(
    page_title="TalentMatch Pro • AI CV Matching",
    page_icon="🚀",
    layout="wide",
)

APP_URL = "https://talentmatch-frontend-dejan.onrender.com"

st.markdown(
    """
    <div style="padding: 42px 0 24px 0;">
        <h1 style="font-size:56px; margin-bottom:10px;">
            🚀 TalentMatch Pro
        </h1>
        <p style="font-size:22px; color:#6b7280; max-width:900px;">
            AI-powered CV analysis, ATS keyword matching, and CV rewrite suggestions
            for job seekers who want to apply smarter.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns([1.2, 1])

with col1:
    st.markdown("## Match your CV to real job descriptions")
    st.write(
        "Upload your CV, paste a job description, and get an AI-powered match score, "
        "missing skills, ATS keywords, and practical improvement recommendations."
    )

    cta1, cta2 = st.columns(2)

    with cta1:
        st.page_link("app.py", label="Start CV Analysis", icon="📄")

    with cta2:
        st.page_link("pages/ats_checker.py", label="Run ATS Checker", icon="🎯")

with col2:
    st.container(border=True).markdown(
        """
        ### What users get

        ✅ Match score  
        ✅ Strengths and gaps  
        ✅ ATS keyword coverage  
        ✅ CV rewrite suggestions  
        ✅ Downloadable reports  
        ✅ Application strategy insights  
        """
    )

st.markdown("---")

st.markdown("## Core Features")

feature1, feature2, feature3 = st.columns(3)

with feature1:
    st.container(border=True).markdown(
        """
        ### 📄 AI CV Analysis

        Compare your CV against a real job description and get a clear match score,
        summary, strengths, missing skills, and recommendations.
        """
    )

with feature2:
    st.container(border=True).markdown(
        """
        ### 🎯 ATS Keyword Checker

        See which important job-description keywords your CV already covers
        and which keywords are missing.
        """
    )

with feature3:
    st.container(border=True).markdown(
        """
        ### ✍️ CV Rewrite AI

        Get rewritten CV summary and bullet point suggestions tailored to a specific role,
        without inventing fake experience.
        """
    )

feature4, feature5, feature6 = st.columns(3)

with feature4:
    st.container(border=True).markdown(
        """
        ### 📥 Download Reports

        Export a clean analysis report that includes score, summary,
        gaps, recommendations, and job description context.
        """
    )

with feature5:
    st.container(border=True).markdown(
        """
        ### 📊 Admin Analytics

        Demo SaaS dashboard for product metrics, usage insights,
        conversion tracking, and keyword trends.
        """
    )

with feature6:
    st.container(border=True).markdown(
        """
        ### 🔐 Firebase Auth

        Secure email/password authentication powered by Firebase
        with protected backend routes.
        """
    )

st.markdown("---")

st.markdown("## How it works")

step1, step2, step3 = st.columns(3)

with step1:
    st.info("1️⃣ Upload your PDF CV")

with step2:
    st.info("2️⃣ Paste a job description")

with step3:
    st.info("3️⃣ Get AI-powered insights")

st.markdown("---")

st.markdown("## Pricing Preview")

free_col, pro_col = st.columns(2)

with free_col:
    st.container(border=True).markdown(
        """
        ### Free

        - 3 demo CV analyses
        - AI match score
        - Basic recommendations
        - ATS keyword preview

        **$0**
        """
    )

with pro_col:
    st.container(border=True).markdown(
        """
        ### Pro

        - Unlimited analyses
        - Advanced ATS insights
        - CV Rewrite AI
        - PDF reports
        - Saved history
        - Recruiter insights

        **$9/month**
        """
    )

st.markdown("---")

st.markdown("## Built with a modern SaaS stack")

stack1, stack2, stack3, stack4 = st.columns(4)

with stack1:
    st.success("FastAPI backend")

with stack2:
    st.success("Streamlit frontend")

with stack3:
    st.success("OpenAI API")

with stack4:
    st.success("Firebase Auth")

stack5, stack6, stack7, stack8 = st.columns(4)

with stack5:
    st.success("Firebase Storage")

with stack6:
    st.success("Render deploy")

with stack7:
    st.success("SQLite/PostgreSQL ready")

with stack8:
    st.success("Lemon Squeezy ready")

st.markdown("---")

st.markdown("## Try TalentMatch Pro")

cta_col1, cta_col2, cta_col3 = st.columns(3)

with cta_col1:
    st.page_link("pages/register.py", label="Create Account", icon="🚀")

with cta_col2:
    st.page_link("pages/login.py", label="Login", icon="🔐")

with cta_col3:
    st.page_link("pages/ats_checker.py", label="ATS Checker", icon="🎯")

st.caption(
    "TalentMatch Pro is an AI SaaS MVP built for CV analysis, ATS optimization, "
    "and job application strategy."
)