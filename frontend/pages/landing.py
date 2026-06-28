"""Landing / Dashboard page for TalentMatch Pro.

This page is intentionally frontend-only. It does not change auth, billing,
Firebase, PayPal, or backend API behavior.
"""

from __future__ import annotations

import streamlit as st

from auth_utils import is_logged_in, is_pro_user
from components.ui import (
    apply_global_styles,
    get_display_name,
    get_initials,
    render_hero,
    safe_html,
)


APP_URL = "https://talentmatchcv.com"
APP_DESCRIPTION = (
    "TalentMatch Pro is an AI-powered CV analysis platform for ATS optimization, "
    "semantic matching, CV rewrite suggestions, recruiter workflows, and PDF reports."
)


def _html_card(title: str, body: str, icon: str = "✨", extra: str = "") -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="min-height:100%;{extra}">
            <div class="tm-card-title">{safe_html(icon)} {safe_html(title)}</div>
            <div class="tm-muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(label: str, value: str, note: str, icon: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card" style="min-height:136px">
            <div class="tm-kicker">{safe_html(icon)} {safe_html(label)}</div>
            <div class="tm-value">{safe_html(value)}</div>
            <div class="tm-muted">{safe_html(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _action_card(title: str, description: str, icon: str, page: str, label: str) -> None:
    _html_card(title, description, icon, "margin-bottom:.75rem")
    st.page_link(page, label=label)


def _feature_chip(text: str, green: bool = False) -> str:
    class_name = "tm-pill tm-pill-green" if green else "tm-pill"
    return f'<span class="{class_name}">{safe_html(text)}</span>'


def _status_row(label: str, value: str, icon: str = "✅") -> str:
    return f"""
        <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.72rem 0;border-bottom:1px solid rgba(148,163,184,.18)">
            <div style="font-weight:850;color:#0f172a">{safe_html(icon)} {safe_html(label)}</div>
            <div class="tm-muted">{safe_html(value)}</div>
        </div>
    """


def _render_seo_tags() -> None:
    st.markdown(
        f"""
        <meta name="description" content="{safe_html(APP_DESCRIPTION)}">
        <meta name="keywords" content="AI CV analysis, ATS checker, CV optimization, semantic matching, recruiter mode, resume analysis">
        <meta name="author" content="TalentMatch Pro">
        <link rel="canonical" href="{safe_html(APP_URL)}">
        <meta property="og:title" content="TalentMatch Pro - AI CV Analysis & ATS Optimization">
        <meta property="og:description" content="{safe_html(APP_DESCRIPTION)}">
        <meta property="og:type" content="website">
        <meta property="og:url" content="{safe_html(APP_URL)}">
        <meta property="og:image" content="{safe_html(APP_URL)}/app/static/logo.png">
        <meta property="og:site_name" content="TalentMatch Pro">
        """,
        unsafe_allow_html=True,
    )


def _render_dashboard_header() -> None:
    name = get_display_name()
    plan = "PRO Member" if is_pro_user() else "Free Workspace"

    if is_logged_in():
        title = f"Welcome back, {name}"
        subtitle = (
            f"TalentMatch Pro • {plan}. Your AI command center for ATS checks, "
            "CV rewrites, semantic matching, recruiter ranking and premium PDF reports."
        )
    else:
        title = "Build a job-winning CV with AI"
        subtitle = (
            "Analyze your CV, compare it with real job descriptions, find missing ATS keywords, "
            "rewrite key sections and export polished reports."
        )

    render_hero("Enterprise SaaS Dashboard", title, subtitle, get_initials(name))


def _render_kpis() -> None:
    plan_value = "PRO" if is_pro_user() else "FREE"
    pdf_note = "Branded PDF export enabled" if is_pro_user() else "Upgrade to unlock premium PDF"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        _kpi_card("Workspace", plan_value, "PayPal-ready subscription status", "💼")
    with k2:
        _kpi_card("AI tools", "6", "Analysis, ATS, rewrite, match, recruiter, history", "🤖")
    with k3:
        _kpi_card("Pro plan", "$9/mo", "Monthly subscription via PayPal", "💎")
    with k4:
        _kpi_card("Reports", "PDF", pdf_note, "📄")


def _render_quick_actions() -> None:
    st.markdown('<div class="tm-section-title">Quick actions</div>', unsafe_allow_html=True)

    q1, q2, q3, q4 = st.columns(4)
    with q1:
        _action_card(
            "ATS Checker",
            "Upload a CV and compare keyword coverage against a job description.",
            "🎯",
            "pages/ats_checker.py",
            "🚀 Start ATS Checker",
        )
    with q2:
        _action_card(
            "CV Rewrite",
            "Improve your headline, summary and bullet points for a specific role.",
            "✍️",
            "pages/cv_rewrite.py",
            "✍ Rewrite CV",
        )
    with q3:
        _action_card(
            "Semantic Match",
            "Compare meaning, context and keyword alignment, not only exact terms.",
            "🧠",
            "pages/semantic_match.py",
            "🧠 Run Semantic Match",
        )
    with q4:
        _action_card(
            "History",
            "Open saved analyses and export TXT or premium PDF reports.",
            "📜",
            "pages/history.py",
            "📜 View History",
        )


def _render_ai_command_center() -> None:
    st.markdown('<div class="tm-section-title">AI command center</div>', unsafe_allow_html=True)

    left, right = st.columns([1.35, 1])

    with left:
        chips = "".join(
            [
                _feature_chip("ATS optimization", True),
                _feature_chip("Keyword gaps", True),
                _feature_chip("Semantic score", True),
                _feature_chip("Recruiter ranking"),
                _feature_chip("CV rewrite"),
                _feature_chip("PDF reports"),
            ]
        )
        st.markdown(
            f"""
            <div class="tm-card" style="min-height:320px">
                <div class="tm-kicker">🧭 Recommended workflow</div>
                <div class="tm-card-title" style="font-size:1.65rem">From raw CV to stronger application</div>
                <div class="tm-muted" style="margin-bottom:1rem">
                    Use the tools in order: first check ATS keywords, then run semantic matching,
                    rewrite weak sections and export a polished report for review.
                </div>
                <div>{chips}</div>
                <br>
                {_status_row("Step 1", "Upload CV as PDF", "1️⃣")}
                {_status_row("Step 2", "Paste exact job description", "2️⃣")}
                {_status_row("Step 3", "Review score, gaps and recommendations", "3️⃣")}
                {_status_row("Step 4", "Rewrite and export report", "4️⃣")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:
        status = "Premium tools unlocked" if is_pro_user() else "Free plan active"
        cta_text = "Manage subscription" if is_pro_user() else "Upgrade to Pro"
        cta_page = "pages/account.py" if is_pro_user() else "pages/pricing.py"

        st.markdown(
            f"""
            <div class="tm-card" style="min-height:320px">
                <div class="tm-kicker">💎 Membership</div>
                <div class="tm-card-title" style="font-size:1.55rem">{safe_html(status)}</div>
                <div class="tm-muted">
                    Free is perfect for testing. Pro unlocks premium PDF reports, semantic matching,
                    recruiter workflows and a stronger job-search operating system.
                </div>
                <br>
                {_status_row("Billing", "PayPal", "💳")}
                {_status_row("PDF reports", "Available in Pro", "📄")}
                {_status_row("Recruiter Mode", "Available in Pro", "👥")}
                {_status_row("Semantic Match", "Available in Pro", "🧠")}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link(cta_page, label=f"💳 {cta_text}")


def _render_core_features() -> None:
    st.markdown('<div class="tm-section-title">Core features</div>', unsafe_allow_html=True)

    f1, f2, f3 = st.columns(3)
    with f1:
        _html_card(
            "AI CV Analysis",
            "Compare your CV against a real job description and get a clear score, strengths, weaknesses and practical next steps.",
            "📄",
        )
    with f2:
        _html_card(
            "ATS Keyword Checker",
            "Find covered and missing keywords so your CV is easier for applicant tracking systems to understand.",
            "🎯",
        )
    with f3:
        _html_card(
            "CV Rewrite AI",
            "Improve summaries and bullet points while keeping the CV truthful, professional and aligned with the role.",
            "✍️",
        )

    f4, f5, f6 = st.columns(3)
    with f4:
        _html_card(
            "Semantic Match",
            "Compare meaning and role fit between your CV and job description, not only exact keyword overlap.",
            "🧠",
        )
    with f5:
        _html_card(
            "Recruiter Mode",
            "Rank multiple candidates, compare profiles and support recruiter-style workflows for hiring teams.",
            "👥",
        )
    with f6:
        _html_card(
            "Premium PDF Reports",
            "Export branded reports with score, analysis, recommendations, footer and page numbering.",
            "📥",
        )


def _render_product_quality() -> None:
    st.markdown('<div class="tm-section-title">Product quality</div>', unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)
    with p1:
        st.markdown(
            f"""
            <div class="tm-card">
                <div class="tm-card-title">🛡 Production stack</div>
                {_status_row("Frontend", "Streamlit on Render", "✅")}
                {_status_row("Backend", "FastAPI", "✅")}
                {_status_row("Auth", "Firebase Authentication", "✅")}
                {_status_row("Billing", "PayPal subscriptions", "✅")}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            f"""
            <div class="tm-card">
                <div class="tm-card-title">📈 User value</div>
                {_status_row("ATS clarity", "Keyword match and gaps", "🎯")}
                {_status_row("Role alignment", "Semantic AI matching", "🧠")}
                {_status_row("Better wording", "CV rewrite suggestions", "✍️")}
                {_status_row("Export", "TXT and PDF reports", "📄")}
            </div>
            """,
            unsafe_allow_html=True,
        )
    with p3:
        st.markdown(
            f"""
            <div class="tm-card">
                <div class="tm-card-title">🚀 Launch readiness</div>
                {_status_row("Custom domain", "talentmatchcv.com", "🌐")}
                {_status_row("SEO", "Sitemap and robots ready", "🔎")}
                {_status_row("HTTPS", "Enabled", "🔒")}
                {_status_row("Version", "v1.0 polish sprint", "🏁")}
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_pricing_preview() -> None:
    st.markdown('<div class="tm-section-title">Pricing preview</div>', unsafe_allow_html=True)

    free_col, pro_col = st.columns(2)

    with free_col:
        st.markdown(
            f"""
            <div class="tm-card">
                <div class="tm-kicker">Starter</div>
                <div class="tm-card-title">Free</div>
                <div class="tm-value">$0</div>
                <div class="tm-muted">Starter access for testing the product and validating the workflow.</div><br>
                {_feature_chip("3 CV analyses")}
                {_feature_chip("ATS Checker")}
                {_feature_chip("TXT Export")}
                {_feature_chip("Basic history")}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with pro_col:
        st.markdown(
            f"""
            <div class="tm-card" style="border-color:rgba(16,185,129,.34);box-shadow:0 24px 70px rgba(16,185,129,.12)">
                <div class="tm-kicker">Most popular</div>
                <div class="tm-card-title">Pro</div>
                <div class="tm-value">$9/mo</div>
                <div class="tm-muted">Full premium workflow for serious job search, CV optimization and recruiter-style review.</div><br>
                {_feature_chip("Premium PDF reports", True)}
                {_feature_chip("Semantic Match", True)}
                {_feature_chip("Recruiter Mode", True)}
                {_feature_chip("Advanced history", True)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/pricing.py", label="💳 Upgrade with PayPal")


def _render_why() -> None:
    st.markdown('<div class="tm-section-title">Why TalentMatch Pro?</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">✨ One workspace for better applications</div>
            <div class="tm-muted">
                TalentMatch Pro combines AI resume analysis, ATS optimization, semantic matching,
                CV rewrite assistance, recruiter workflows and downloadable reports into one clean SaaS workspace.
                It helps users identify missing keywords, improve structure, align experience with job descriptions
                and prepare stronger applications with less guesswork.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_landing() -> None:
    apply_global_styles()
    _render_seo_tags()
    _render_dashboard_header()
    _render_kpis()
    _render_quick_actions()
    _render_ai_command_center()
    _render_core_features()
    _render_product_quality()
    _render_pricing_preview()
    _render_why()
