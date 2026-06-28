import time

import streamlit as st

from auth_utils import api_post, is_logged_in, is_pro_user, refresh_profile
from components.footer import render_footer
from components.sidebar import render_sidebar
from components.ui import apply_global_styles, render_hero


st.set_page_config(page_title="Pricing • TalentMatch Pro", page_icon="🚀", layout="wide")
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
            for _ in range(5):
                time.sleep(2)
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
        st.warning("Payment was approved, but Pro access is still syncing. Please refresh this page in a few moments.")
    else:
        st.info("Please login to verify your Pro status.")

if paypal_cancel:
    st.warning("PayPal checkout was cancelled. You can upgrade anytime.")


st.markdown(
    """
    <style>
    .tm-pricing-card {
        position: relative;
        min-height: 520px;
        padding: 1.7rem;
        border-radius: 30px;
        border: 1px solid rgba(148, 163, 184, 0.22);
        background: rgba(255, 255, 255, 0.82);
        box-shadow: 0 22px 65px rgba(15, 23, 42, 0.07);
        overflow: hidden;
    }
    .tm-pricing-card-pro {
        border: 1px solid rgba(16,185,129,.46);
        background:
            radial-gradient(circle at top right, rgba(16,185,129,.18), transparent 34%),
            radial-gradient(circle at bottom left, rgba(37,99,235,.12), transparent 38%),
            rgba(255, 255, 255, 0.92);
        box-shadow: 0 30px 80px rgba(16,185,129,.16);
    }
    .tm-ribbon {
        display: inline-flex;
        align-items: center;
        gap: .35rem;
        padding: .38rem .78rem;
        border-radius: 999px;
        background: rgba(16,185,129,.14);
        color: #047857;
        border: 1px solid rgba(16,185,129,.22);
        font-size: .76rem;
        font-weight: 950;
        letter-spacing: .07em;
        text-transform: uppercase;
        margin-bottom: .8rem;
    }
    .tm-price {
        font-size: 3.1rem;
        line-height: .95;
        letter-spacing: -.07em;
        font-weight: 950;
        color: #0f172a;
        margin: .45rem 0 .3rem 0;
    }
    .tm-price span {
        font-size: 1rem;
        letter-spacing: 0;
        color: #64748b;
        font-weight: 850;
    }
    .tm-feature-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: .78rem .9rem;
        border-bottom: 1px solid rgba(148,163,184,.18);
        color: #334155;
        font-size: .94rem;
    }
    .tm-feature-row:nth-child(odd) { background: rgba(248,250,252,.58); }
    .tm-feature-name { font-weight: 850; color: #0f172a; }
    .tm-check { font-weight: 950; color: #047857; }
    .tm-no { font-weight: 950; color: #b91c1c; }
    .tm-trust-card {
        padding: 1.15rem;
        border-radius: 22px;
        background: rgba(255,255,255,.76);
        border: 1px solid rgba(148,163,184,.22);
        min-height: 140px;
        box-shadow: 0 18px 44px rgba(15,23,42,.05);
    }
    .tm-faq-card {
        padding: 1rem 1.1rem;
        border-radius: 20px;
        background: rgba(255,255,255,.72);
        border: 1px solid rgba(148,163,184,.20);
        margin-bottom: .8rem;
    }
    .tm-secure-strip {
        padding: 1rem 1.15rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(15,23,42,.94), rgba(30,41,59,.92));
        border: 1px solid rgba(148,163,184,.24);
        box-shadow: 0 22px 54px rgba(15,23,42,.16);
    }
    .tm-secure-strip * { color: #e5e7eb !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


render_hero(
    "Premium PayPal pricing",
    "Start free. Upgrade when you are ready.",
    "TalentMatch Pro gives you a complete AI CV workspace: ATS optimization, CV rewrite, semantic matching, recruiter workflows and professional PDF reports.",
    "💳",
)

status_col1, status_col2, status_col3 = st.columns(3)
with status_col1:
    st.markdown(
        """
        <div class="tm-trust-card">
            <div class="tm-kicker">Billing</div>
            <div class="tm-card-title">PayPal only</div>
            <div class="tm-muted">Secure subscription checkout and billing handled by PayPal.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with status_col2:
    st.markdown(
        """
        <div class="tm-trust-card">
            <div class="tm-kicker">Current plan</div>
            <div class="tm-card-title">Free or Pro</div>
            <div class="tm-muted">Use core tools for free, then unlock the full workflow when needed.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with status_col3:
    st.markdown(
        """
        <div class="tm-trust-card">
            <div class="tm-kicker">Pro price</div>
            <div class="tm-card-title">$9 / month</div>
            <div class="tm-muted">Simple monthly subscription with no hidden platform fees.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="tm-section-title">Choose your plan</div>', unsafe_allow_html=True)

free_col, pro_col = st.columns(2)
with free_col:
    st.markdown(
        """
        <div class="tm-pricing-card">
            <div class="tm-ribbon">Starter</div>
            <div class="tm-card-title">Free</div>
            <div class="tm-price">$0<span>/mo</span></div>
            <div class="tm-muted">For testing the platform and running a lightweight CV workflow.</div>
            <br>
            <span class="tm-pill">✅ 3 CV analyses</span>
            <span class="tm-pill">✅ ATS Checker</span>
            <span class="tm-pill">✅ CV Rewrite preview</span>
            <span class="tm-pill">✅ TXT Export</span>
            <span class="tm-pill">❌ PDF Reports</span>
            <span class="tm-pill">❌ Semantic Match</span>
            <span class="tm-pill">❌ Recruiter Mode</span>
            <br><br>
            <div class="tm-muted">Best for trying TalentMatch Pro before upgrading.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with pro_col:
    st.markdown(
        """
        <div class="tm-pricing-card tm-pricing-card-pro">
            <div class="tm-ribbon">⭐ Most popular</div>
            <div class="tm-card-title">Pro</div>
            <div class="tm-price">$9<span>/mo</span></div>
            <div class="tm-muted">Full AI career workflow for serious job search, portfolio polish and recruiter-style screening.</div>
            <br>
            <span class="tm-pill tm-pill-green">✅ Unlimited analyses</span>
            <span class="tm-pill tm-pill-green">✅ Premium PDF Reports</span>
            <span class="tm-pill tm-pill-green">✅ CV Rewrite AI</span>
            <span class="tm-pill tm-pill-green">✅ Semantic Match</span>
            <span class="tm-pill tm-pill-green">✅ Recruiter Mode</span>
            <span class="tm-pill tm-pill-green">✅ Saved History</span>
            <span class="tm-pill tm-pill-green">✅ Priority workflow</span>
            <br><br>
            <div class="tm-muted">Best for users who want a polished, repeatable AI CV workflow.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not is_logged_in():
        st.warning("Please login before upgrading to Pro.")
        st.page_link("pages/login.py", label="🔐 Go to Login")
    elif is_pro:
        st.success("🚀 You already have Pro.")
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
        st.info("Secure monthly subscription powered by PayPal.")
        if st.button("🚀 Upgrade to Pro with PayPal", use_container_width=True):
            with st.spinner("Creating PayPal subscription checkout..."):
                response = api_post("/billing/create-checkout", timeout=60)
            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    st.error("Backend returned invalid PayPal checkout response.")
                    st.code(response.text)
                    st.stop()
                checkout_url = data.get("checkout_url")
                if not checkout_url:
                    st.error("PayPal checkout URL missing from backend response.")
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

st.markdown('<div class="tm-section-title">Feature comparison</div>', unsafe_allow_html=True)
comparison = [
    ("ATS Checker", "✅", "✅"),
    ("CV Analysis", "Limited", "Unlimited"),
    ("CV Rewrite AI", "Limited", "✅"),
    ("Semantic Match", "❌", "✅"),
    ("Recruiter Mode", "❌", "✅"),
    ("Premium PDF Reports", "❌", "✅"),
    ("Saved History", "Basic", "Full"),
    ("Billing provider", "—", "PayPal"),
]
rows = "".join(
    f"""
    <div class="tm-feature-row">
        <div class="tm-feature-name">{feature}</div>
        <div>{free}</div>
        <div class="tm-check">{pro}</div>
    </div>
    """
    for feature, free, pro in comparison
)
st.markdown(
    f"""
    <div class="tm-card" style="padding:0; overflow:hidden">
        <div class="tm-feature-row" style="background:rgba(15,23,42,.94); color:#e5e7eb">
            <div class="tm-feature-name" style="color:#fff">Feature</div>
            <div style="font-weight:950;color:#fff">Free</div>
            <div style="font-weight:950;color:#86efac">Pro</div>
        </div>
        {rows}
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="tm-section-title">Secure checkout</div>', unsafe_allow_html=True)
st.markdown(
    """
    <div class="tm-secure-strip">
        <div style="font-weight:950;font-size:1.2rem;margin-bottom:.35rem">🔒 PayPal-powered subscription</div>
        <div style="color:#cbd5e1;line-height:1.55">
            Secure PayPal checkout • No card details stored by TalentMatch Pro • Cancel anytime • Instant Pro sync after approval
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="tm-section-title">What Pro unlocks</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        """
        <div class="tm-trust-card">
            <div class="tm-card-title">📥 Branded PDF reports</div>
            <div class="tm-muted">Export professional reports with TalentMatch Pro footer, page numbers and clean formatting.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        """
        <div class="tm-trust-card">
            <div class="tm-card-title">🧠 Semantic matching</div>
            <div class="tm-muted">Understand meaning, context and gaps beyond exact keyword overlap.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        """
        <div class="tm-trust-card">
            <div class="tm-card-title">👥 Recruiter workflow</div>
            <div class="tm-muted">Rank candidates and review hiring-ready insights for recruiter-style workflows.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown('<div class="tm-section-title">Trust and privacy</div>', unsafe_allow_html=True)
t1, t2, t3, t4 = st.columns(4)
with t1:
    st.markdown('<div class="tm-trust-card"><div class="tm-card-title">💳 Secure Payments</div><div class="tm-muted">Checkout is handled by PayPal.</div></div>', unsafe_allow_html=True)
with t2:
    st.markdown('<div class="tm-trust-card"><div class="tm-card-title">🤖 AI Powered</div><div class="tm-muted">Built for practical CV and job matching workflows.</div></div>', unsafe_allow_html=True)
with t3:
    st.markdown('<div class="tm-trust-card"><div class="tm-card-title">🔒 Privacy First</div><div class="tm-muted">No card details are stored by TalentMatch Pro.</div></div>', unsafe_allow_html=True)
with t4:
    st.markdown('<div class="tm-trust-card"><div class="tm-card-title">☁️ Cloud Ready</div><div class="tm-muted">Designed for production SaaS deployment.</div></div>', unsafe_allow_html=True)

st.markdown('<div class="tm-section-title">FAQ</div>', unsafe_allow_html=True)
faq_items = [
    ("Can I cancel anytime?", "Yes. Subscription management is handled through PayPal."),
    ("Is PayPal secure?", "Yes. Checkout and subscription approval happen on PayPal's secure pages."),
    ("Does TalentMatch Pro store my card?", "No. TalentMatch Pro does not store your card details."),
    ("When does Pro activate?", "After PayPal approval, the app refreshes your profile and syncs Pro access."),
]
for question, answer in faq_items:
    st.markdown(
        f"""
        <div class="tm-faq-card">
            <div style="font-weight:950;color:#0f172a">{question}</div>
            <div class="tm-muted">{answer}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()
st.markdown("### 📬 Contact")
st.write("**TalentMatch Pro** · support@talentmatchcv.com · Pro Plan: $9/month via PayPal")
render_footer()
