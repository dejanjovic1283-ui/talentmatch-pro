import streamlit as st

from auth_utils import is_logged_in, is_pro_user
from components.ui import apply_global_styles, card, get_display_name, get_initials, render_hero, safe_html


APP_URL = "https://talentmatchcv.com"
APP_DESCRIPTION = (
    "TalentMatch Pro is an AI-powered CV analysis platform for ATS optimization, "
    "semantic matching, CV rewrite suggestions, recruiter workflows, and PDF reports."
)


def _metric_value(label: str, value: str, note: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-muted">{safe_html(label)}</div>
            <div class="tm-value">{safe_html(value)}</div>
            <div class="tm-muted">{safe_html(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_landing():
    apply_global_styles()

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
        """,
        unsafe_allow_html=True,
    )

    name = get_display_name()
    plan = "PRO" if is_pro_user() else "FREE"
    title = f"Welcome: {name}" if is_logged_in() else "Build a job-winning CV with AI"
    subtitle = (
        "Your premium CV command center: ATS analysis, keyword coverage, semantic matching, "
        "CV rewrite suggestions, recruiter workflow and polished PDF reports."
    )
    render_hero("Enterprise SaaS Dashboard", title, subtitle, get_initials(name))

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        _metric_value("Current workspace", plan, "PayPal-ready subscription status")
    with m2:
        _metric_value("Core tools", "6", "ATS, Rewrite, Match, Recruiter, History, PDF")
    with m3:
        _metric_value("Pro plan", "$9", "Monthly subscription via PayPal")
    with m4:
        _metric_value("Reports", "PDF", "Branded export with footer and pages")

    st.markdown('<div class="tm-section-title">Quick actions</div>', unsafe_allow_html=True)
    q1, q2, q3, q4 = st.columns(4)
    with q1:
        st.page_link("pages/ats_checker.py", label="📋 Start ATS Checker")
    with q2:
        st.page_link("pages/cv_rewrite.py", label="✍ Rewrite CV")
    with q3:
        st.page_link("pages/history.py", label="📜 View History")
    with q4:
        st.page_link("pages/pricing.py", label="💳 Upgrade / Manage")

    st.markdown('<div class="tm-section-title">Core features</div>', unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    with f1:
        card("AI CV Analysis", "Compare your CV against a real job description and get a clear score, strengths, weaknesses and practical recommendations.", "📄")
    with f2:
        card("ATS Keyword Checker", "Find covered and missing keywords so your CV is easier for applicant tracking systems to understand.", "📋")
    with f3:
        card("CV Rewrite AI", "Improve summaries and bullet points while keeping the CV truthful and professional.", "✍")

    f4, f5, f6 = st.columns(3)
    with f4:
        card("Semantic Match", "Compare meaning and context between your CV and job description, not only exact keywords.", "🧠")
    with f5:
        card("Recruiter Mode", "Rank candidates, compare profiles and support recruiter-style workflows for hiring teams.", "👥")
    with f6:
        card("Premium PDF Reports", "Export branded reports with score, analysis, recommendations, footer and page numbering.", "📥")

    st.markdown('<div class="tm-section-title">How it works</div>', unsafe_allow_html=True)
    s1, s2, s3 = st.columns(3)
    with s1:
        card("1. Upload CV", "Upload a PDF CV or use your saved analysis workflow.", "1️⃣")
    with s2:
        card("2. Add job description", "Paste the exact role requirements to create a targeted comparison.", "2️⃣")
    with s3:
        card("3. Get insights", "Receive score, gaps, keywords, rewrite suggestions and reports.", "3️⃣")

    st.markdown('<div class="tm-section-title">Pricing preview</div>', unsafe_allow_html=True)
    free_col, pro_col = st.columns(2)
    with free_col:
        st.markdown(
            """
            <div class="tm-card">
                <div class="tm-card-title">Free</div>
                <div class="tm-value">$0</div>
                <div class="tm-muted">Starter access for testing the product.</div><br>
                <span class="tm-pill">3 CV analyses</span>
                <span class="tm-pill">ATS Checker</span>
                <span class="tm-pill">TXT Export</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pro_col:
        st.markdown(
            """
            <div class="tm-card">
                <div class="tm-card-title">Pro</div>
                <div class="tm-value">$9/mo</div>
                <div class="tm-muted">Full premium workflow for serious job search and recruiter use.</div><br>
                <span class="tm-pill tm-pill-green">Unlimited analyses</span>
                <span class="tm-pill tm-pill-green">PDF Reports</span>
                <span class="tm-pill tm-pill-green">Semantic Match</span>
                <span class="tm-pill tm-pill-green">Recruiter Mode</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/pricing.py", label="💳 Upgrade with PayPal")

    st.markdown('<div class="tm-section-title">Why TalentMatch Pro?</div>', unsafe_allow_html=True)
    st.write(
        "TalentMatch Pro combines AI resume analysis, ATS optimization, semantic matching, CV rewrite assistance, "
        "recruiter workflows and downloadable reports into one clean SaaS workspace. It helps users identify missing "
        "keywords, improve structure, align experience with job descriptions and prepare stronger applications."
    )
