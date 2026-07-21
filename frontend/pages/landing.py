from __future__ import annotations

import streamlit as st

from auth_utils import is_logged_in, is_pro_user, refresh_profile
from components.ui import (
    apply_global_styles,
    get_display_name,
    get_initials,
    render_card,
    render_kpi_card,
    render_page_intro,
    render_section_title,
    safe_html,
)

APP_URL = "https://talentmatchcv.com"
APP_DESCRIPTION = (
    "TalentMatch Pro is an AI-powered CV analysis platform for ATS optimization, "
    "semantic matching, CV rewrite suggestions, recruiter workflows, and professional reports."
)
PRO_MONTHLY_PRICE = "$19"


def _dashboard_css() -> None:
    st.markdown(
        """
        <style>
        .tm-dashboard-shell {display:flex;flex-direction:column;gap:1.25rem}
        .tm-command-strip,.tm-quick-grid {
            display:grid;grid-template-columns:repeat(4,minmax(0,1fr));
            gap:1rem;margin:.2rem 0 .45rem 0
        }
        .tm-command-card,.tm-quick-card,.tm-price-card,.tm-insight-panel {
            border:1px solid rgba(148,163,184,.22);
            background:rgba(255,255,255,.86);
            box-shadow:0 18px 48px rgba(15,23,42,.06)
        }
        .tm-command-card {
            min-height:176px;padding:1.25rem;border-radius:24px;
            position:relative;overflow:hidden
        }
        .tm-command-card:before {
            content:"";position:absolute;inset:0 0 auto 0;height:4px;
            background:linear-gradient(90deg,#2563eb,#10b981)
        }
        .tm-command-label {
            color:#2563eb;font-size:.74rem;font-weight:950;text-transform:uppercase;
            letter-spacing:.13em;margin-bottom:.7rem
        }
        .tm-command-value {
            color:#0f172a;font-size:2.05rem;font-weight:950;
            letter-spacing:-.055em;line-height:1;margin-bottom:.55rem
        }
        .tm-command-note,.tm-quick-copy,.tm-insight-copy {
            color:#64748b;line-height:1.5
        }
        .tm-quick-card {min-height:150px;padding:1.15rem;border-radius:22px}
        .tm-quick-icon {
            width:46px;height:46px;border-radius:16px;display:flex;
            align-items:center;justify-content:center;background:rgba(37,99,235,.10);
            font-size:1.3rem;margin-bottom:.8rem
        }
        .tm-quick-title,.tm-insight-title {
            color:#0f172a;font-weight:950;letter-spacing:-.025em
        }
        .tm-quick-title {font-size:1.05rem;margin-bottom:.35rem}
        .tm-insight-panel {
            padding:1.35rem;border-radius:26px;
            background:
                radial-gradient(circle at 10% 10%,rgba(37,99,235,.10),transparent 32%),
                radial-gradient(circle at 90% 90%,rgba(16,185,129,.10),transparent 32%),
                rgba(255,255,255,.88)
        }
        .tm-insight-title {font-size:1.18rem;margin-bottom:.5rem}
        .tm-price-card {padding:1.4rem;border-radius:26px;min-height:100%}
        .tm-price-card-pro {
            border-color:rgba(37,99,235,.32);
            background:
                radial-gradient(circle at top right,rgba(37,99,235,.12),transparent 38%),
                radial-gradient(circle at bottom left,rgba(16,185,129,.10),transparent 38%),
                rgba(255,255,255,.95);
            box-shadow:0 24px 64px rgba(37,99,235,.12)
        }
        .tm-price {
            color:#0f172a;font-size:2.2rem;font-weight:950;
            letter-spacing:-.06em;margin:.25rem 0 .45rem 0
        }
        .tm-price-unit {font-size:.95rem;color:#64748b;font-weight:800;letter-spacing:0}
        .tm-feature-line {
            display:flex;align-items:center;gap:.55rem;padding:.35rem 0;
            color:#334155;font-weight:760
        }
        .tm-feature-check {
            width:22px;height:22px;border-radius:999px;background:rgba(16,185,129,.13);
            color:#047857;display:inline-flex;align-items:center;justify-content:center;
            font-size:.78rem;font-weight:950;flex:0 0 auto
        }
        .tm-page-links [data-testid="stPageLink"] a {
            min-height:3.15rem;border-radius:16px;
            border:1px solid rgba(148,163,184,.24);
            background:rgba(255,255,255,.86);padding:.75rem 1rem;
            font-weight:900;box-shadow:0 12px 28px rgba(15,23,42,.05);
            transition:160ms ease
        }
        .tm-page-links [data-testid="stPageLink"] a:hover {
            transform:translateY(-1px);border-color:rgba(37,99,235,.35);
            box-shadow:0 16px 34px rgba(37,99,235,.10)
        }
        @media (max-width:1100px) {
            .tm-command-strip,.tm-quick-grid {grid-template-columns:repeat(2,minmax(0,1fr))}
        }
        @media (max-width:760px) {
            .tm-command-strip,.tm-quick-grid {grid-template-columns:1fr}
            .tm-command-card,.tm-quick-card {min-height:auto}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_meta_tags() -> None:
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


def _render_command_metrics(plan: str) -> None:
    values = (
        ("Workspace", plan, "PayPal-backed membership status"),
        ("AI tools", "6", "Analysis, ATS, Rewrite, Match, Recruiter, History"),
        ("Pro plan", PRO_MONTHLY_PRICE, "Monthly subscription via PayPal"),
        ("Reports", "PDF", "Professional exports with page numbers and footer"),
    )
    cards = "".join(
        f"""
        <div class="tm-command-card">
            <div class="tm-command-label">{safe_html(label)}</div>
            <div class="tm-command-value">{safe_html(value)}</div>
            <div class="tm-command-note">{safe_html(note)}</div>
        </div>
        """
        for label, value, note in values
    )
    st.markdown(f'<div class="tm-command-strip">{cards}</div>', unsafe_allow_html=True)


def _render_quick_actions() -> None:
    render_section_title("Quick actions", "Jump directly into the workflows you use most.")
    items = (
        ("📄", "Analyze CV", "Run a complete AI review against a target role."),
        ("📋", "Check ATS", "Measure keyword coverage and prioritize missing terms."),
        ("🧠", "Semantic match", "Compare meaning, context, and recruiter readiness."),
        ("👥", "Recruiter workspace", "Rank candidates and manage the Candidate Database."),
    )
    cards = "".join(
        f"""
        <div class="tm-quick-card">
            <div class="tm-quick-icon">{safe_html(icon)}</div>
            <div class="tm-quick-title">{safe_html(title)}</div>
            <div class="tm-quick-copy">{safe_html(copy)}</div>
        </div>
        """
        for icon, title, copy in items
    )
    st.markdown(f'<div class="tm-quick-grid">{cards}</div>', unsafe_allow_html=True)
    st.markdown('<div class="tm-page-links">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.page_link("pages/cv_analysis.py", label="📄 Open CV Analysis")
    with c2:
        st.page_link("pages/ats_checker.py", label="📋 Open ATS Checker")
    with c3:
        st.page_link("pages/semantic_match.py", label="🧠 Open Semantic Match")
    with c4:
        st.page_link("pages/recruiter_mode.py", label="👥 Open Recruiter Mode")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_core_features() -> None:
    render_section_title(
        "Core workspace",
        "Every tool follows one consistent premium workflow from upload to export.",
    )
    rows = (
        (
            ("AI CV Analysis", "Compare a CV against a real job description and receive a structured score, strengths, gaps, and practical recommendations.", "📄"),
            ("ATS Checker", "Identify matched and missing keywords so applications align more clearly with applicant tracking systems.", "📋"),
            ("CV Rewrite AI", "Improve headlines, summaries, and experience bullets while preserving truthful candidate information.", "✍"),
        ),
        (
            ("Semantic Match", "Compare meaning and context—not only exact keyword overlap—and evaluate recruiter readiness.", "🧠"),
            ("Recruiter Workspace", "Rank candidates, save results, manage status, favorites, notes, tags, and exports.", "👥"),
            ("Professional Reports", "Export consistent TXT, CSV, and PDF reports for reviews, applications, and recruiter workflows.", "📥"),
        ),
    )
    for row in rows:
        cols = st.columns(3)
        for col, (title, body, icon) in zip(cols, row):
            with col:
                render_card(title, body, icon, strong=True)


def _render_workflow() -> None:
    render_section_title(
        "How TalentMatch Pro works",
        "A focused three-step process from source CV to actionable decision support.",
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi_card("Step 1", "Upload CV", "1️⃣", "PDF intake and validation")
    with c2:
        render_kpi_card("Step 2", "Add target role", "2️⃣", "Use the exact job description")
    with c3:
        render_kpi_card("Step 3", "Get insights", "3️⃣", "Scores, gaps, rewrite, and reports")


def _render_pricing() -> None:
    render_section_title(
        "Plans",
        "Start free, then unlock the complete TalentMatch Pro workflow with PayPal.",
    )
    free_col, pro_col = st.columns(2)
    with free_col:
        st.markdown(
            """
            <div class="tm-price-card">
                <div class="tm-kicker">STARTER</div>
                <div class="tm-card-title">Free</div>
                <div class="tm-price">$0</div>
                <div class="tm-muted">Explore the core workflow before upgrading.</div>
                <div style="margin-top:1rem">
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>3 CV analyses</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>ATS Checker</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>TXT exports</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with pro_col:
        st.markdown(
            f"""
            <div class="tm-price-card tm-price-card-pro">
                <div class="tm-kicker">PREMIUM</div>
                <div class="tm-card-title">Pro</div>
                <div class="tm-price">{safe_html(PRO_MONTHLY_PRICE)}<span class="tm-price-unit">/month</span></div>
                <div class="tm-muted">Complete premium workflow for serious job search and recruiter use.</div>
                <div style="margin-top:1rem">
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Unlimited analyses</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Professional PDF reports</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Semantic Match</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Recruiter Mode</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Candidate Database</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.page_link("pages/pricing.py", label="💳 Upgrade or manage with PayPal")


def _render_value_statement() -> None:
    render_section_title("Why TalentMatch Pro?")
    st.markdown(
        """
        <div class="tm-insight-panel">
            <div class="tm-insight-title">One premium workspace for candidates and recruiters</div>
            <div class="tm-insight-copy">
                TalentMatch Pro combines AI CV analysis, ATS optimization, semantic matching,
                CV rewrite assistance, recruiter workflows, Candidate Database management,
                and downloadable reports in one consistent SaaS workspace. It helps users
                identify gaps, strengthen relevance, and make better application or hiring decisions.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_landing() -> None:
    apply_global_styles()
    _dashboard_css()
    _render_meta_tags()

    if is_logged_in() and not st.session_state.get("landing_profile_loaded"):
        refresh_profile()
        st.session_state["landing_profile_loaded"] = True

    name = get_display_name()
    plan = "PRO" if is_pro_user() else "FREE"
    title = f"Welcome back, {name}" if is_logged_in() else "Build a stronger CV with AI"
    subtitle = (
        "Your premium CV command center for AI analysis, ATS intelligence, semantic matching, "
        "CV rewrite workflows, recruiter tools, Candidate Database management, and professional reports."
    )

    render_page_intro(
        kicker="ENTERPRISE TALENT INTELLIGENCE",
        title=title,
        subtitle=subtitle,
        icon=get_initials(name),
        badge=f"{plan} WORKSPACE",
    )

    st.markdown('<div class="tm-dashboard-shell">', unsafe_allow_html=True)
    _render_command_metrics(plan)
    _render_quick_actions()
    _render_core_features()
    _render_workflow()
    _render_pricing()
    _render_value_statement()
    st.markdown("</div>", unsafe_allow_html=True)
