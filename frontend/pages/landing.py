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
        .tm-dashboard-shell {
            display:flex;
            flex-direction:column;
            gap:2.5rem;
            width:100%;
        }
        .tm-dashboard-section {
            display:flex;
            flex-direction:column;
            gap:1rem;
        }
        .tm-command-strip,
        .tm-quick-grid,
        .tm-capability-grid {
            display:grid;
            gap:1rem;
            width:100%;
        }
        .tm-command-strip,
        .tm-quick-grid {
            grid-template-columns:repeat(4,minmax(0,1fr));
        }
        .tm-capability-grid {
            grid-template-columns:repeat(3,minmax(0,1fr));
        }
        .tm-command-card,
        .tm-quick-card,
        .tm-price-card,
        .tm-insight-panel,
        .tm-capability-card {
            border:1px solid rgba(148,163,184,.22);
            background:rgba(255,255,255,.90);
            box-shadow:0 18px 48px rgba(15,23,42,.06);
            backdrop-filter:blur(14px);
        }
        .tm-command-card {
            min-height:176px;
            padding:1.3rem;
            border-radius:24px;
            position:relative;
            overflow:hidden;
        }
        .tm-command-card:before {
            content:"";
            position:absolute;
            inset:0 0 auto 0;
            height:4px;
            background:linear-gradient(90deg,#2563eb,#10b981);
        }
        .tm-command-label {
            color:#2563eb;
            font-size:.74rem;
            font-weight:950;
            text-transform:uppercase;
            letter-spacing:.13em;
            margin-bottom:.7rem;
        }
        .tm-command-value {
            color:#0f172a;
            font-size:2.05rem;
            font-weight:950;
            letter-spacing:-.055em;
            line-height:1;
            margin-bottom:.55rem;
        }
        .tm-command-note,
        .tm-quick-copy,
        .tm-insight-copy,
        .tm-capability-copy {
            color:#64748b;
            line-height:1.58;
        }
        .tm-quick-card,
        .tm-capability-card {
            min-height:168px;
            padding:1.2rem;
            border-radius:22px;
        }

        .tm-quick-link {
            display:block;
            color:inherit !important;
            text-decoration:none !important;
            border-radius:22px;
            transition:transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
        }

        .tm-quick-link:hover {
            transform:translateY(-2px);
            text-decoration:none !important;
        }

        .tm-quick-link:hover .tm-quick-card {
            border-color:rgba(37,99,235,.38);
            box-shadow:0 22px 54px rgba(37,99,235,.12);
        }
        .tm-quick-icon,
        .tm-capability-icon {
            width:48px;
            height:48px;
            border-radius:16px;
            display:flex;
            align-items:center;
            justify-content:center;
            background:rgba(37,99,235,.10);
            font-size:1.3rem;
            margin-bottom:.85rem;
        }
        .tm-quick-title,
        .tm-capability-title,
        .tm-insight-title {
            color:#0f172a;
            font-weight:950;
            letter-spacing:-.025em;
        }
        .tm-quick-title,
        .tm-capability-title {
            font-size:1.05rem;
            margin-bottom:.35rem;
        }
        .tm-insight-panel {
            padding:1.55rem;
            border-radius:26px;
            background:
                radial-gradient(circle at 10% 10%,rgba(37,99,235,.10),transparent 32%),
                radial-gradient(circle at 90% 90%,rgba(16,185,129,.10),transparent 32%),
                rgba(255,255,255,.92);
        }
        .tm-insight-title {
            font-size:1.22rem;
            margin-bottom:.55rem;
        }
        .tm-price-grid {
            display:grid;
            grid-template-columns:repeat(2,minmax(0,1fr));
            gap:1rem;
        }
        .tm-price-card {
            padding:1.5rem;
            border-radius:26px;
            min-height:100%;
        }
        .tm-price-card-pro {
            border-color:rgba(37,99,235,.32);
            background:
                radial-gradient(circle at top right,rgba(37,99,235,.12),transparent 38%),
                radial-gradient(circle at bottom left,rgba(16,185,129,.10),transparent 38%),
                rgba(255,255,255,.96);
            box-shadow:0 24px 64px rgba(37,99,235,.12);
        }
        .tm-price {
            color:#0f172a;
            font-size:2.2rem;
            font-weight:950;
            letter-spacing:-.06em;
            margin:.25rem 0 .45rem 0;
        }
        .tm-price-unit {
            font-size:.95rem;
            color:#64748b;
            font-weight:800;
            letter-spacing:0;
        }
        .tm-feature-list {
            margin-top:1rem;
            display:flex;
            flex-direction:column;
            gap:.45rem;
        }
        .tm-feature-line {
            display:flex;
            align-items:center;
            gap:.55rem;
            color:#334155;
            font-weight:760;
        }
        .tm-feature-check {
            width:22px;
            height:22px;
            border-radius:999px;
            background:rgba(16,185,129,.13);
            color:#047857;
            display:inline-flex;
            align-items:center;
            justify-content:center;
            font-size:.78rem;
            font-weight:950;
            flex:0 0 auto;
        }
        .tm-dashboard-cta [data-testid="stPageLink"] a {
            min-height:3.35rem;
            border-radius:16px;
            font-weight:950;
        }
        @media (max-width:1100px) {
            .tm-command-strip,
            .tm-quick-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
            .tm-capability-grid {grid-template-columns:repeat(2,minmax(0,1fr));}
        }
        @media (max-width:760px) {
            .tm-dashboard-shell {gap:2rem;}
            .tm-command-strip,
            .tm-quick-grid,
            .tm-capability-grid,
            .tm-price-grid {grid-template-columns:1fr;}
            .tm-command-card,
            .tm-quick-card,
            .tm-capability-card {min-height:auto;}
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
        ("Pro plan", PRO_MONTHLY_PRICE, "Monthly subscription through PayPal"),
        ("Reports", "PDF", "Professional exports with page numbers and footer"),
    )
    cards = "".join(
        (
            '<div class="tm-command-card">'
            f'<div class="tm-command-label">{safe_html(label)}</div>'
            f'<div class="tm-command-value">{safe_html(value)}</div>'
            f'<div class="tm-command-note">{safe_html(note)}</div>'
            "</div>"
        )
        for label, value, note in values
    )
    st.markdown(f'<div class="tm-command-strip">{cards}</div>', unsafe_allow_html=True)


def _render_quick_actions() -> None:
    render_section_title("Quick actions", "Jump directly into the workflows you use most.")
    items = (
        ("📄", "Analyze CV", "Run a complete AI review against a target role.", "/cv_analysis"),
        ("📋", "Check ATS", "Measure keyword coverage and prioritize missing terms.", "/ats_checker"),
        ("🧠", "Semantic match", "Compare meaning, context, and recruiter readiness.", "/semantic_match"),
        ("👥", "Recruiter workspace", "Rank candidates and manage the Candidate Database.", "/recruiter_mode"),
    )
    cards = "".join(
        (
            f'<a class="tm-quick-link" href="{safe_html(route)}" target="_self" '
            f'aria-label="Open {safe_html(title)}">'
            '<div class="tm-quick-card">'
            f'<div class="tm-quick-icon">{safe_html(icon)}</div>'
            f'<div class="tm-quick-title">{safe_html(title)}</div>'
            f'<div class="tm-quick-copy">{safe_html(copy)}</div>'
            "</div>"
            "</a>"
        )
        for icon, title, copy, route in items
    )
    st.markdown(f'<div class="tm-quick-grid">{cards}</div>', unsafe_allow_html=True)


def _render_core_features() -> None:
    render_section_title(
        "Core workspace",
        "Every tool follows one consistent premium workflow from upload to export.",
    )
    items = (
        ("AI CV Analysis", "Compare a CV against a real job description and receive a structured score, strengths, gaps, and practical recommendations.", "📄"),
        ("ATS Checker", "Identify matched and missing keywords so applications align more clearly with applicant tracking systems.", "📋"),
        ("CV Rewrite AI", "Improve headlines, summaries, and experience bullets while preserving truthful candidate information.", "✍"),
        ("Semantic Match", "Compare meaning and context—not only exact keyword overlap—and evaluate recruiter readiness.", "🧠"),
        ("Recruiter Workspace", "Rank candidates, save results, manage status, favorites, notes, tags, and exports.", "👥"),
        ("Professional Reports", "Export consistent TXT, CSV, and PDF reports for reviews, applications, and recruiter workflows.", "📥"),
    )
    cards = "".join(
        (
            '<div class="tm-capability-card">'
            f'<div class="tm-capability-icon">{safe_html(icon)}</div>'
            f'<div class="tm-capability-title">{safe_html(title)}</div>'
            f'<div class="tm-capability-copy">{safe_html(body)}</div>'
            "</div>"
        )
        for title, body, icon in items
    )
    st.markdown(f'<div class="tm-capability-grid">{cards}</div>', unsafe_allow_html=True)


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
    st.markdown(
        f"""
        <div class="tm-price-grid">
            <div class="tm-price-card">
                <div class="tm-kicker">STARTER</div>
                <div class="tm-card-title">Free</div>
                <div class="tm-price">$0</div>
                <div class="tm-muted">Explore the core workflow before upgrading.</div>
                <div class="tm-feature-list">
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>3 CV analyses</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>ATS Checker</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>TXT exports</div>
                </div>
            </div>
            <div class="tm-price-card tm-price-card-pro">
                <div class="tm-kicker">PREMIUM</div>
                <div class="tm-card-title">Pro</div>
                <div class="tm-price">{safe_html(PRO_MONTHLY_PRICE)}<span class="tm-price-unit">/month</span></div>
                <div class="tm-muted">Complete premium workflow for serious job search and recruiter use.</div>
                <div class="tm-feature-list">
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Unlimited analyses</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Professional PDF reports</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Semantic Match</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Recruiter Mode</div>
                    <div class="tm-feature-line"><span class="tm-feature-check">✓</span>Candidate Database</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="tm-dashboard-cta">', unsafe_allow_html=True)
    st.page_link("pages/pricing.py", label="💳 View plans or manage PayPal subscription")
    st.markdown("</div>", unsafe_allow_html=True)


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
