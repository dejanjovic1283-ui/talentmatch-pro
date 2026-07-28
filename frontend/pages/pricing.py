from __future__ import annotations

import time

import streamlit as st

from auth_utils import api_post, is_logged_in, is_pro_user, refresh_profile
from components.footer import render_footer
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero


PRO_PRICE_USD = 19
PROFILE_SYNC_ATTEMPTS = 5
PROFILE_SYNC_DELAY_SECONDS = 2


st.set_page_config(
    page_title="Pricing • TalentMatch Pro",
    page_icon="💳",
    layout="wide",
)
apply_global_styles()
render_sidebar()


if is_logged_in() and not st.session_state.get("pricing_profile_loaded"):
    refresh_profile()
    st.session_state["pricing_profile_loaded"] = True

is_pro = is_pro_user()
paypal_success = st.query_params.get("paypal_success") == "1"
paypal_cancel = st.query_params.get("paypal_cancel") == "1"


if paypal_success:
    st.success("✅ PayPal subscription approved. We are syncing your Pro access now.")
    if is_logged_in():
        with st.spinner("Refreshing your account status..."):
            for _ in range(PROFILE_SYNC_ATTEMPTS):
                time.sleep(PROFILE_SYNC_DELAY_SECONDS)
                profile = refresh_profile() or {}
                if (
                    profile.get("is_pro")
                    or profile.get("plan") == "pro"
                    or profile.get("subscription_status") == "active"
                    or profile.get("paypal_subscription_status") == "active"
                ):
                    st.success("🚀 Pro plan is active.")
                    st.balloons()
                    st.rerun()
        st.warning(
            "Payment was approved, but Pro access is still syncing. "
            "Please refresh this page in a few moments."
        )
    else:
        st.info("Please log in to verify your Pro status.")

if paypal_cancel:
    st.warning("PayPal checkout was cancelled. You can upgrade at any time.")


st.markdown(
    """
    <style>
    .tm-pricing-shell {
        position: relative;
        overflow: hidden;
        padding: 1.2rem 0 0.4rem 0;
        border-radius: 34px;
        filter:
            drop-shadow(0 22px 34px rgba(15, 23, 42, 0.08))
            drop-shadow(0 8px 16px rgba(37, 99, 235, 0.05));
        transition: filter 220ms ease, transform 220ms ease;
    }

    .tm-pricing-shell:hover {
        filter:
            drop-shadow(0 28px 44px rgba(15, 23, 42, 0.10))
            drop-shadow(0 10px 20px rgba(37, 99, 235, 0.07));
    }

    .tm-pricing-shell::before {
        content: "";
        position: absolute;
        width: 420px;
        height: 420px;
        border-radius: 999px;
        top: -260px;
        right: -120px;
        background: rgba(37, 99, 235, 0.10);
        filter: blur(10px);
        pointer-events: none;
    }

    .tm-metric-card,
    .tm-plan-card,
    .tm-value-card,
    .tm-trust-card,
    .tm-faq-card,
    .tm-quote-card {
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: rgba(255, 255, 255, 0.80);
        box-shadow:
            0 18px 46px rgba(15, 23, 42, 0.065),
            0 2px 8px rgba(15, 23, 42, 0.035),
            inset 0 1px 0 rgba(255, 255, 255, 0.74);
        backdrop-filter: blur(16px);
        transition:
            transform 220ms ease,
            box-shadow 220ms ease,
            border-color 220ms ease,
            background 220ms ease;
        will-change: transform;
    }

    .tm-metric-card:hover,
    .tm-plan-card:hover,
    .tm-value-card:hover,
    .tm-trust-card:hover,
    .tm-faq-card:hover,
    .tm-quote-card:hover {
        transform: translateY(-4px);
        border-color: rgba(100, 116, 139, 0.30);
        box-shadow:
            0 26px 64px rgba(15, 23, 42, 0.10),
            0 8px 20px rgba(37, 99, 235, 0.045),
            inset 0 1px 0 rgba(255, 255, 255, 0.82);
    }

    .tm-metric-card {
        min-height: 145px;
        padding: 1.15rem;
        border-radius: 24px;
    }

    .tm-metric-label {
        color: #2563eb;
        font-size: 0.72rem;
        font-weight: 950;
        letter-spacing: 0.11em;
        text-transform: uppercase;
        margin-bottom: 0.55rem;
    }

    .tm-metric-value {
        color: #0f172a;
        font-size: 1.55rem;
        line-height: 1.1;
        font-weight: 950;
        letter-spacing: -0.04em;
        margin-bottom: 0.45rem;
    }

    .tm-muted-copy {
        color: #64748b;
        line-height: 1.55;
        font-size: 0.94rem;
    }

    .tm-section-heading {
        margin: 2.6rem 0 1rem 0;
        color: #0f172a;
        font-size: clamp(1.65rem, 2vw, 2.15rem);
        font-weight: 950;
        letter-spacing: -0.045em;
    }

    .tm-section-copy {
        margin: -0.55rem 0 1.2rem 0;
        max-width: 760px;
        color: #64748b;
        line-height: 1.65;
    }

    .tm-plan-card {
        position: relative;
        min-height: 585px;
        padding: 1.8rem;
        border-radius: 32px;
        overflow: hidden;
    }

    .tm-plan-card-pro {
        border-color: rgba(16, 185, 129, 0.46);
        background:
            radial-gradient(circle at top right, rgba(16, 185, 129, 0.20), transparent 34%),
            radial-gradient(circle at bottom left, rgba(37, 99, 235, 0.13), transparent 38%),
            rgba(255, 255, 255, 0.93);
        box-shadow:
            0 34px 90px rgba(16, 185, 129, 0.15),
            0 12px 32px rgba(37, 99, 235, 0.08),
            inset 0 1px 0 rgba(255, 255, 255, 0.80);
    }

    .tm-plan-card-pro:hover {
        transform: translateY(-6px);
        border-color: rgba(16, 185, 129, 0.62);
        box-shadow:
            0 42px 110px rgba(16, 185, 129, 0.20),
            0 16px 38px rgba(37, 99, 235, 0.11),
            inset 0 1px 0 rgba(255, 255, 255, 0.88);
    }

    .tm-plan-card-pro::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: inherit;
        pointer-events: none;
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
    }

    .tm-ribbon {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.40rem 0.78rem;
        border-radius: 999px;
        background: rgba(16, 185, 129, 0.14);
        color: #047857;
        border: 1px solid rgba(16, 185, 129, 0.24);
        font-size: 0.74rem;
        font-weight: 950;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-bottom: 1rem;
    }

    .tm-plan-name {
        color: #0f172a;
        font-size: 1.45rem;
        font-weight: 950;
        letter-spacing: -0.03em;
    }

    .tm-price {
        color: #0f172a;
        font-size: 4.2rem;
        line-height: 0.95;
        letter-spacing: -0.08em;
        font-weight: 950;
        margin: 0.75rem 0 0.35rem 0;
    }

    .tm-price span {
        color: #64748b;
        font-size: 1rem;
        letter-spacing: 0;
        font-weight: 850;
    }

    .tm-price-note {
        color: #64748b;
        font-size: 0.87rem;
        margin-bottom: 1.15rem;
    }

    .tm-plan-description {
        color: #475569;
        line-height: 1.62;
        min-height: 78px;
        margin-bottom: 1rem;
    }

    .tm-feature-list {
        display: grid;
        gap: 0.58rem;
        margin-top: 1rem;
    }

    .tm-feature-item {
        display: flex;
        align-items: flex-start;
        gap: 0.62rem;
        padding: 0.72rem 0.78rem;
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.16);
        background: rgba(248, 250, 252, 0.68);
        color: #334155;
        line-height: 1.4;
        font-weight: 760;
    }

    .tm-feature-item-pro {
        border-color: rgba(16, 185, 129, 0.18);
        background: rgba(236, 253, 245, 0.67);
    }

    .tm-feature-icon {
        flex: 0 0 auto;
        width: 1.35rem;
        text-align: center;
    }

    .tm-roi-panel {
        padding: 1.35rem;
        border-radius: 28px;
        border: 1px solid rgba(37, 99, 235, 0.24);
        background:
            radial-gradient(circle at top left, rgba(37, 99, 235, 0.15), transparent 36%),
            radial-gradient(circle at bottom right, rgba(16, 185, 129, 0.13), transparent 38%),
            rgba(255, 255, 255, 0.82);
        box-shadow: 0 26px 68px rgba(37, 99, 235, 0.09);
    }

    .tm-roi-number {
        color: #0f172a;
        font-size: 2.25rem;
        font-weight: 950;
        letter-spacing: -0.06em;
        line-height: 1;
        margin-bottom: 0.35rem;
    }

    .tm-roi-label {
        color: #64748b;
        font-size: 0.88rem;
        line-height: 1.5;
    }

    .tm-comparison {
        overflow: hidden;
        border-radius: 28px;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: rgba(255, 255, 255, 0.80);
        box-shadow:
            0 24px 64px rgba(15, 23, 42, 0.075),
            0 6px 18px rgba(37, 99, 235, 0.04),
            inset 0 1px 0 rgba(255, 255, 255, 0.72);
        transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    }

    .tm-comparison:hover {
        transform: translateY(-3px);
        border-color: rgba(100, 116, 139, 0.30);
        box-shadow:
            0 32px 78px rgba(15, 23, 42, 0.11),
            0 10px 24px rgba(37, 99, 235, 0.055),
            inset 0 1px 0 rgba(255, 255, 255, 0.80);
    }

    .tm-feature-row {
        display: grid;
        grid-template-columns: minmax(180px, 1.7fr) minmax(90px, 0.65fr) minmax(90px, 0.65fr);
        align-items: center;
        gap: 1rem;
        padding: 0.92rem 1rem;
        border-bottom: 1px solid rgba(148, 163, 184, 0.17);
        color: #475569;
        font-size: 0.94rem;
    }

    .tm-feature-row:last-child { border-bottom: 0; }
    .tm-feature-row:nth-child(even) { background: rgba(248, 250, 252, 0.62); }

    .tm-feature-header {
        color: #f8fafc;
        background: linear-gradient(135deg, #0f172a, #1e293b) !important;
        font-weight: 950;
    }

    .tm-feature-name { color: #0f172a; font-weight: 900; }
    .tm-feature-pro { color: #047857; font-weight: 950; }

    .tm-secure-strip {
        padding: 1.4rem;
        border-radius: 28px;
        background:
            radial-gradient(circle at top right, rgba(37, 99, 235, 0.24), transparent 36%),
            linear-gradient(135deg, rgba(15, 23, 42, 0.97), rgba(30, 41, 59, 0.95));
        border: 1px solid rgba(148, 163, 184, 0.24);
        box-shadow: 0 28px 72px rgba(15, 23, 42, 0.18);
    }

    .tm-secure-title {
        color: #f8fafc;
        font-size: 1.35rem;
        font-weight: 950;
        letter-spacing: -0.025em;
        margin-bottom: 0.45rem;
    }

    .tm-secure-copy {
        color: #cbd5e1;
        line-height: 1.65;
    }

    .tm-value-card,
    .tm-trust-card {
        padding: 1.18rem;
        border-radius: 24px;
        min-height: 165px;
    }

    .tm-card-icon {
        font-size: 1.35rem;
        margin-bottom: 0.55rem;
    }

    .tm-card-title {
        color: #0f172a;
        font-size: 1.05rem;
        font-weight: 950;
        letter-spacing: -0.02em;
        margin-bottom: 0.45rem;
    }

    .tm-quote-card {
        padding: 1.35rem;
        border-radius: 26px;
        min-height: 190px;
    }

    .tm-quote-text {
        color: #1e293b;
        font-size: 1.03rem;
        font-weight: 760;
        line-height: 1.65;
        margin-bottom: 1rem;
    }

    .tm-quote-meta {
        color: #64748b;
        font-size: 0.84rem;
        line-height: 1.5;
    }

    .tm-faq-card {
        padding: 1.05rem 1.15rem;
        border-radius: 20px;
        margin-bottom: 0.78rem;
    }

    .tm-faq-question {
        color: #0f172a;
        font-weight: 950;
        margin-bottom: 0.25rem;
    }

    .tm-cta-panel {
        padding: 1.8rem;
        border-radius: 32px;
        border: 1px solid rgba(16, 185, 129, 0.34);
        background:
            radial-gradient(circle at top right, rgba(16, 185, 129, 0.20), transparent 34%),
            radial-gradient(circle at bottom left, rgba(37, 99, 235, 0.16), transparent 38%),
            rgba(255, 255, 255, 0.91);
        box-shadow:
            0 30px 82px rgba(16, 185, 129, 0.14),
            0 12px 34px rgba(37, 99, 235, 0.09),
            0 0 0 1px rgba(255, 255, 255, 0.38) inset;
        margin-top: 1rem;
        position: relative;
        overflow: hidden;
        transition: transform 240ms ease, box-shadow 240ms ease, border-color 240ms ease;
    }

    .tm-cta-panel::before {
        content: "";
        position: absolute;
        width: 260px;
        height: 260px;
        right: -120px;
        top: -140px;
        border-radius: 999px;
        background: radial-gradient(circle, rgba(255, 255, 255, 0.72), rgba(16, 185, 129, 0.10) 44%, transparent 72%);
        filter: blur(6px);
        pointer-events: none;
        opacity: 0.85;
    }

    .tm-cta-panel:hover {
        transform: translateY(-4px);
        border-color: rgba(16, 185, 129, 0.52);
        box-shadow:
            0 38px 96px rgba(16, 185, 129, 0.18),
            0 16px 42px rgba(37, 99, 235, 0.12),
            0 0 42px rgba(16, 185, 129, 0.08),
            0 0 0 1px rgba(255, 255, 255, 0.50) inset;
    }

    .tm-cta-title {
        color: #0f172a;
        font-size: clamp(1.8rem, 3vw, 2.65rem);
        font-weight: 950;
        letter-spacing: -0.06em;
        line-height: 1.03;
        margin-bottom: 0.6rem;
    }

    .tm-cta-price {
        color: #047857;
        font-size: 1.2rem;
        font-weight: 950;
        margin-bottom: 0.55rem;
    }

    .tm-cta-copy {
        color: #64748b;
        line-height: 1.65;
        max-width: 760px;
    }

    .tm-contact-panel {
        padding: 1.25rem 1.35rem;
        border-radius: 24px;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: rgba(255, 255, 255, 0.74);
        box-shadow:
            0 18px 48px rgba(15, 23, 42, 0.065),
            0 4px 14px rgba(37, 99, 235, 0.035),
            inset 0 1px 0 rgba(255, 255, 255, 0.70);
        transition: transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease;
    }

    .tm-contact-panel:hover {
        transform: translateY(-3px);
        border-color: rgba(100, 116, 139, 0.28);
        box-shadow:
            0 24px 60px rgba(15, 23, 42, 0.09),
            0 8px 20px rgba(37, 99, 235, 0.045),
            inset 0 1px 0 rgba(255, 255, 255, 0.80);
    }

    @media (prefers-reduced-motion: reduce) {
        .tm-pricing-shell,
        .tm-metric-card,
        .tm-plan-card,
        .tm-value-card,
        .tm-trust-card,
        .tm-faq-card,
        .tm-quote-card,
        .tm-comparison,
        .tm-cta-panel,
        .tm-contact-panel {
            transition: none !important;
        }

        .tm-metric-card:hover,
        .tm-plan-card:hover,
        .tm-value-card:hover,
        .tm-trust-card:hover,
        .tm-faq-card:hover,
        .tm-quote-card:hover,
        .tm-comparison:hover,
        .tm-cta-panel:hover,
        .tm-contact-panel:hover {
            transform: none !important;
        }
    }

    @media (max-width: 720px) {
        .tm-feature-row {
            grid-template-columns: 1.4fr 0.7fr 0.7fr;
            gap: 0.55rem;
            padding: 0.82rem 0.72rem;
            font-size: 0.82rem;
        }

        .tm-plan-card {
            min-height: auto;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="tm-pricing-shell">', unsafe_allow_html=True)
render_hero(
    "Enterprise-grade PayPal pricing",
    "One workspace. Every CV workflow.",
    "Start free, then unlock the complete TalentMatch Pro platform for AI-powered CV analysis, ATS optimisation, CV rewriting, semantic matching, recruiter workflows, Candidate Database access and professional reports.",
    "💳",
)
st.markdown("</div>", unsafe_allow_html=True)


metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
metric_cards = [
    (
        metric_col1,
        "Billing",
        "PayPal only",
        "Checkout, approval and recurring subscription management are handled by PayPal.",
    ),
    (
        metric_col2,
        "Pro price",
        f"${PRO_PRICE_USD} / month",
        "One transparent monthly subscription with no TalentMatch Pro setup fee.",
    ),
    (
        metric_col3,
        "Access",
        "Full workspace",
        "Unlock Pro tools, Recruiter Workspace, Candidate Database and premium exports.",
    ),
    (
        metric_col4,
        "Control",
        "Cancel anytime",
        "Manage the recurring subscription from your PayPal account.",
    ),
]
for column, label, value, description in metric_cards:
    with column:
        st.markdown(
            f"""
            <div class="tm-metric-card">
                <div class="tm-metric-label">{label}</div>
                <div class="tm-metric-value">{value}</div>
                <div class="tm-muted-copy">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown('<div class="tm-section-heading">Choose your plan</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tm-section-copy">Use the free workspace for core CV tasks, or move to Pro when you need the complete repeatable workflow.</div>',
    unsafe_allow_html=True,
)

free_col, pro_col = st.columns(2, gap="large")
with free_col:
    st.markdown(
        """
        <div class="tm-plan-card">
            <div class="tm-ribbon">Starter workspace</div>
            <div class="tm-plan-name">Free</div>
            <div class="tm-price">$0<span>/month</span></div>
            <div class="tm-price-note">No payment method required</div>
            <div class="tm-plan-description">
                A focused entry point for testing TalentMatch Pro and completing a lightweight CV workflow.
            </div>
            <div class="tm-feature-list">
                <div class="tm-feature-item"><span class="tm-feature-icon">✓</span><span>3 CV analyses</span></div>
                <div class="tm-feature-item"><span class="tm-feature-icon">✓</span><span>ATS Checker access</span></div>
                <div class="tm-feature-item"><span class="tm-feature-icon">✓</span><span>CV Rewrite preview</span></div>
                <div class="tm-feature-item"><span class="tm-feature-icon">✓</span><span>TXT export</span></div>
                <div class="tm-feature-item"><span class="tm-feature-icon">—</span><span>No premium PDF reports</span></div>
                <div class="tm-feature-item"><span class="tm-feature-icon">—</span><span>No Semantic Match or Recruiter Workspace</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with pro_col:
    st.markdown(
        f"""
        <div class="tm-plan-card tm-plan-card-pro">
            <div class="tm-ribbon">⭐ Most popular</div>
            <div class="tm-plan-name">TalentMatch Pro</div>
            <div class="tm-price">${PRO_PRICE_USD}<span>/month</span></div>
            <div class="tm-price-note">Recurring monthly subscription via PayPal</div>
            <div class="tm-plan-description">
                The complete AI CV and recruiter workflow for serious job search, repeatable optimisation and professional reporting.
            </div>
            <div class="tm-feature-list">
                <div class="tm-feature-item tm-feature-item-pro"><span class="tm-feature-icon">✓</span><span>Unlimited CV analyses</span></div>
                <div class="tm-feature-item tm-feature-item-pro"><span class="tm-feature-icon">✓</span><span>Premium PDF reports and TXT exports</span></div>
                <div class="tm-feature-item tm-feature-item-pro"><span class="tm-feature-icon">✓</span><span>Full CV Rewrite AI workflow</span></div>
                <div class="tm-feature-item tm-feature-item-pro"><span class="tm-feature-icon">✓</span><span>Semantic Match intelligence</span></div>
                <div class="tm-feature-item tm-feature-item-pro"><span class="tm-feature-icon">✓</span><span>Recruiter Mode and Candidate Database</span></div>
                <div class="tm-feature-item tm-feature-item-pro"><span class="tm-feature-icon">✓</span><span>Full saved History and priority workflow</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not is_logged_in():
        st.warning("Please log in before upgrading to Pro.")
        st.page_link("pages/login.py", label="🔐 Go to Login")
    elif is_pro:
        st.success("🚀 Your TalentMatch Pro subscription is active.")
        if st.button("💳 Manage PayPal Subscription", use_container_width=True):
            with st.spinner("Opening PayPal subscription management..."):
                response = api_post("/billing/create-portal", timeout=60)
            if response.status_code == 200:
                try:
                    portal_url = response.json().get("portal_url")
                except Exception:
                    portal_url = None
                if portal_url:
                    st.session_state["paypal_portal_url"] = portal_url
                else:
                    st.error("PayPal subscription portal URL is missing.")
                    try:
                        st.json(response.json())
                    except Exception:
                        st.code(response.text)
            else:
                st.error(f"Status: {response.status_code}")
                try:
                    st.json(response.json())
                except Exception:
                    st.code(response.text)

        if st.session_state.get("paypal_portal_url"):
            st.link_button(
                "Open PayPal Subscription Settings",
                st.session_state["paypal_portal_url"],
                use_container_width=True,
            )
    else:
        st.info(f"Secure ${PRO_PRICE_USD}/month subscription powered by PayPal.")
        if st.button("🚀 Upgrade to Pro with PayPal", use_container_width=True):
            with st.spinner("Creating PayPal subscription checkout..."):
                response = api_post("/billing/create-checkout", timeout=60)
            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    st.error("Backend returned an invalid PayPal checkout response.")
                    st.code(response.text)
                    st.stop()

                checkout_url = data.get("checkout_url")
                if not checkout_url:
                    st.error("PayPal checkout URL is missing from the backend response.")
                    st.json(data)
                    st.stop()

                st.session_state["paypal_checkout_url"] = checkout_url
                st.success("PayPal checkout created successfully.")
            else:
                st.error(f"Status: {response.status_code}")
                try:
                    st.json(response.json())
                except Exception:
                    st.code(response.text)

        if st.session_state.get("paypal_checkout_url"):
            st.link_button(
                "Open Secure PayPal Checkout",
                st.session_state["paypal_checkout_url"],
                use_container_width=True,
            )


st.markdown('<div class="tm-section-heading">Workflow value estimator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="tm-section-copy">Estimate the time value of a repeatable CV workflow. Results are illustrative and depend on how you use the platform.</div>',
    unsafe_allow_html=True,
)

input_col1, input_col2, input_col3 = st.columns(3)
with input_col1:
    cv_tasks_per_month = st.number_input(
        "CV or job-matching tasks per month",
        min_value=1,
        max_value=200,
        value=12,
        step=1,
    )
with input_col2:
    manual_minutes_per_task = st.number_input(
        "Manual minutes per task",
        min_value=5,
        max_value=240,
        value=45,
        step=5,
    )
with input_col3:
    estimated_time_reduction = st.slider(
        "Estimated time reduction",
        min_value=10,
        max_value=80,
        value=50,
        step=5,
        format="%d%%",
    )

manual_hours = (cv_tasks_per_month * manual_minutes_per_task) / 60
estimated_hours_saved = manual_hours * (estimated_time_reduction / 100)
hours_per_dollar = estimated_hours_saved / PRO_PRICE_USD

st.markdown('<div class="tm-roi-panel">', unsafe_allow_html=True)
roi_col1, roi_col2, roi_col3 = st.columns(3)
with roi_col1:
    st.markdown(
        f'<div class="tm-roi-number">{manual_hours:.1f} h</div><div class="tm-roi-label">Estimated manual workload per month</div>',
        unsafe_allow_html=True,
    )
with roi_col2:
    st.markdown(
        f'<div class="tm-roi-number">{estimated_hours_saved:.1f} h</div><div class="tm-roi-label">Illustrative time saved per month</div>',
        unsafe_allow_html=True,
    )
with roi_col3:
    st.markdown(
        f'<div class="tm-roi-number">{hours_per_dollar:.2f} h</div><div class="tm-roi-label">Illustrative hours saved per subscription dollar</div>',
        unsafe_allow_html=True,
    )
st.markdown("</div>", unsafe_allow_html=True)
st.caption("Estimator only. It is not a guarantee of time savings, productivity or employment outcomes.")


st.markdown('<div class="tm-section-heading">Feature comparison</div>', unsafe_allow_html=True)
comparison = [
    ("ATS Checker", "Included", "Included"),
    ("CV Analysis", "3 analyses", "Unlimited"),
    ("CV Rewrite AI", "Preview", "Full workflow"),
    ("Semantic Match", "Locked", "Included"),
    ("Recruiter Mode", "Locked", "Included"),
    ("Candidate Database", "Locked", "Included"),
    ("Premium PDF Reports", "Locked", "Included"),
    ("Saved History", "Basic", "Full"),
    ("Subscription billing", "—", "PayPal"),
]
rows = "".join(
    f"""
    <div class="tm-feature-row">
        <div class="tm-feature-name">{feature}</div>
        <div>{free}</div>
        <div class="tm-feature-pro">{pro}</div>
    </div>
    """
    for feature, free, pro in comparison
)
st.markdown(
    f"""
    <div class="tm-comparison">
        <div class="tm-feature-row tm-feature-header">
            <div>Feature</div>
            <div>Free</div>
            <div>Pro</div>
        </div>
        {rows}
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="tm-section-heading">Secure checkout and account control</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="tm-secure-strip">
        <div class="tm-secure-title">🔒 PayPal-powered recurring subscription</div>
        <div class="tm-secure-copy">
            Checkout and subscription approval happen on PayPal pages. TalentMatch Pro does not store card details.
            After approval, the application synchronises Pro access with your account. Subscription management and
            cancellation are handled through PayPal.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


st.markdown('<div class="tm-section-heading">What Pro unlocks</div>', unsafe_allow_html=True)
value_cards = [
    ("📥", "Professional exports", "Generate polished PDF and TXT reports for your CV, ATS and matching workflows."),
    ("🧠", "Semantic intelligence", "Compare meaning, context, strengths and gaps beyond exact keyword overlap."),
    ("👥", "Recruiter Workspace", "Rank candidates, review hiring-ready insights and manage the Candidate Database."),
]
value_columns = st.columns(3)
for column, (icon, title, description) in zip(value_columns, value_cards):
    with column:
        st.markdown(
            f"""
            <div class="tm-value-card">
                <div class="tm-card-icon">{icon}</div>
                <div class="tm-card-title">{title}</div>
                <div class="tm-muted-copy">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown('<div class="tm-section-heading">Built for a complete workflow</div>', unsafe_allow_html=True)
workflow_cards = [
    (
        "Job seeker workflow",
        "Analyse a CV, check ATS readiness, rewrite weak sections, compare against a job description and export the result.",
        "Best for individual career preparation",
    ),
    (
        "Recruiter workflow",
        "Review multiple candidates, compare semantic fit, preserve analysis history and organise candidate records.",
        "Best for structured screening",
    ),
    (
        "Production SaaS workflow",
        "Use Firebase authentication, PostgreSQL persistence, OpenAI-powered analysis, PayPal billing and Render deployment.",
        "Built on the TalentMatch Pro production stack",
    ),
]
workflow_columns = st.columns(3)
for column, (title, text, meta) in zip(workflow_columns, workflow_cards):
    with column:
        st.markdown(
            f"""
            <div class="tm-quote-card">
                <div class="tm-quote-text">{text}</div>
                <div class="tm-card-title">{title}</div>
                <div class="tm-quote-meta">{meta}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown('<div class="tm-section-heading">Trust and privacy</div>', unsafe_allow_html=True)
trust_cards = [
    ("💳", "Secure payments", "PayPal handles checkout and recurring subscription approval."),
    ("🤖", "AI-powered workflow", "TalentMatch Pro supports practical CV and job-matching tasks."),
    ("🔒", "Card privacy", "TalentMatch Pro does not store customer card details."),
    ("☁️", "Cloud deployed", "The application is designed for a production SaaS deployment workflow."),
]
trust_columns = st.columns(4)
for column, (icon, title, description) in zip(trust_columns, trust_cards):
    with column:
        st.markdown(
            f"""
            <div class="tm-trust-card">
                <div class="tm-card-icon">{icon}</div>
                <div class="tm-card-title">{title}</div>
                <div class="tm-muted-copy">{description}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


st.markdown('<div class="tm-section-heading">Frequently asked questions</div>', unsafe_allow_html=True)
faq_items = [
    (
        "How much does TalentMatch Pro cost?",
        f"The Pro subscription costs ${PRO_PRICE_USD} per month and is billed through PayPal.",
    ),
    (
        "Can I cancel at any time?",
        "Yes. Subscription management and cancellation are handled through your PayPal account.",
    ),
    (
        "Does TalentMatch Pro store my card details?",
        "No. Checkout happens on PayPal pages, and TalentMatch Pro does not store your card details.",
    ),
    (
        "When does Pro access activate?",
        "After PayPal approval, TalentMatch Pro refreshes your profile and synchronises the active subscription status.",
    ),
    (
        "What happens if Pro access is still syncing?",
        "Wait a few moments and refresh the Pricing or Account page. The PayPal webhook and account refresh complete the sync.",
    ),
    (
        "Are AI-generated results guaranteed?",
        "No. AI-generated CV, ATS and matching outputs should be reviewed before use and do not guarantee employment outcomes.",
    ),
]
for question, answer in faq_items:
    st.markdown(
        f"""
        <div class="tm-faq-card">
            <div class="tm-faq-question">{question}</div>
            <div class="tm-muted-copy">{answer}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    f"""
    <div class="tm-cta-panel">
        <div class="tm-cta-title">Start your complete TalentMatch Pro workflow.</div>
        <div class="tm-cta-price">${PRO_PRICE_USD}/month · PayPal recurring subscription</div>
        <div class="tm-cta-copy">
            Unlock unlimited CV analysis, Semantic Match, Recruiter Mode, Candidate Database access,
            full History and professional reports. Cancel at any time through PayPal.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

cta_left, cta_right = st.columns([1, 1])
with cta_left:
    if not is_logged_in():
        st.page_link("pages/register.py", label="📝 Create Free Account")
    else:
        st.page_link("app.py", label="🏠 Return to Dashboard")
with cta_right:
    if not is_logged_in():
        st.page_link("pages/login.py", label="🔐 Log In to Upgrade")
    elif is_pro:
        st.success("Pro is already active on this account.")
    else:
        if st.button("🚀 Start Pro with PayPal", use_container_width=True, key="pricing_bottom_checkout"):
            with st.spinner("Creating PayPal subscription checkout..."):
                response = api_post("/billing/create-checkout", timeout=60)
            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    st.error("Backend returned an invalid PayPal checkout response.")
                    st.code(response.text)
                    st.stop()

                checkout_url = data.get("checkout_url")
                if checkout_url:
                    st.session_state["paypal_checkout_url"] = checkout_url
                    st.success("PayPal checkout created successfully.")
                else:
                    st.error("PayPal checkout URL is missing from the backend response.")
                    st.json(data)
            else:
                st.error(f"Status: {response.status_code}")
                try:
                    st.json(response.json())
                except Exception:
                    st.code(response.text)

        if st.session_state.get("paypal_checkout_url"):
            st.link_button(
                "Open Secure PayPal Checkout",
                st.session_state["paypal_checkout_url"],
                use_container_width=True,
            )


st.markdown('<div class="tm-section-heading">Contact</div>', unsafe_allow_html=True)
st.markdown(
    f"""
    <div class="tm-contact-panel">
        <div class="tm-card-title">TalentMatch Pro billing support</div>
        <div class="tm-muted-copy">
            Email: support@talentmatchcv.com<br>
            Pro plan: ${PRO_PRICE_USD}/month via PayPal<br>
            Billing provider: PayPal only
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

render_footer()
