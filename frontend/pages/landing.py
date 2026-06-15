import streamlit as st

APP_URL = "https://talentmatch-frontend-dejan.onrender.com"
APP_DESCRIPTION = (
    "TalentMatch Pro is an AI-powered CV analysis platform for ATS optimization, "
    "semantic matching, CV rewrite suggestions, recruiter workflows, and PDF reports."
)

st.set_page_config(
    page_title="TalentMatch Pro - AI CV Analysis & ATS Optimization",
    page_icon="🎯",
    layout="wide",
)

st.markdown(
    f"""
    <meta name="description" content="{APP_DESCRIPTION}">
    <meta name="keywords" content="AI CV analysis, ATS checker, CV optimization, semantic matching, recruiter mode, resume analysis">
    <meta name="author" content="TalentMatch Pro">
    <link rel="canonical" href="{APP_URL}">

    <meta property="og:title" content="TalentMatch Pro - AI CV Analysis & ATS Optimization">
    <meta property="og:description" content="{APP_DESCRIPTION}">
    <meta property="og:type" content="website">
    <meta property="og:url" content="{APP_URL}">
    <meta property="og:image" content="{APP_URL}/app/static/logo.png">
    <meta property="og:site_name" content="TalentMatch Pro">

    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="TalentMatch Pro - AI CV Analysis & ATS Optimization">
    <meta name="twitter:description" content="{APP_DESCRIPTION}">
    <meta name="twitter:image" content="{APP_URL}/app/static/logo.png">
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div style="padding: 42px 0 24px 0;">
        <h1 style="font-size:56px; margin-bottom:10px;">
            🎯 TalentMatch Pro
        </h1>
        <p style="font-size:22px; color:#6b7280; max-width:900px;">
            AI-powered CV analysis, ATS keyword matching, semantic matching,
            CV rewrite suggestions, and recruiter workflows for smarter job applications.
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
        "missing skills, ATS keywords, semantic insights, and practical improvement recommendations."
    )

    cta1, cta2, cta3 = st.columns(3)

    with cta1:
        st.page_link("app.py", label="Start CV Analysis", icon="📄")

    with cta2:
        st.page_link("pages/ats_checker.py", label="Run ATS Checker", icon="🎯")

    with cta3:
        st.page_link("pages/pricing.py", label="Upgrade to Pro", icon="💳")

with col2:
    st.container(border=True).markdown(
        """
        ### What users get

        ✅ Match score  
        ✅ Strengths and gaps  
        ✅ ATS keyword coverage  
        ✅ Semantic matching  
        ✅ CV rewrite suggestions  
        ✅ Downloadable reports  
        ✅ Recruiter workflow insights  
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
        ### 📥 PDF Reports

        Export a clean analysis report that includes score, summary,
        gaps, recommendations, and job description context.
        """
    )

with feature5:
    st.container(border=True).markdown(
        """
        ### 🧠 Semantic Match

        Compare meaning and context between your CV and job description using AI embeddings
        plus keyword overlap.
        """
    )

with feature6:
    st.container(border=True).markdown(
        """
        ### 👥 Recruiter Mode

        Rank multiple candidates, compare profiles, and support recruiter-style workflows.
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

        - 3 CV analyses
        - AI match score
        - Basic recommendations
        - ATS keyword checker

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
        - Semantic matching
        - Recruiter insights

        **$9/month**
        """
    )

    st.page_link("pages/pricing.py", label="💳 Upgrade with PayPal")

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
    st.success("PostgreSQL")

with stack8:
    st.success("PayPal Billing")

st.markdown("---")

st.markdown("## Try TalentMatch Pro")

cta_col1, cta_col2, cta_col3, cta_col4 = st.columns(4)

with cta_col1:
    st.page_link("pages/register.py", label="Create Account", icon="🚀")

with cta_col2:
    st.page_link("pages/login.py", label="Login", icon="🔐")

with cta_col3:
    st.page_link("pages/ats_checker.py", label="ATS Checker", icon="🎯")

with cta_col4:
    st.page_link("pages/pricing.py", label="Pricing", icon="💳")

st.caption(
    "TalentMatch Pro is an AI SaaS MVP built for CV analysis, ATS optimization, "
    "semantic matching, recruiter workflows, and PayPal-powered subscriptions."
)