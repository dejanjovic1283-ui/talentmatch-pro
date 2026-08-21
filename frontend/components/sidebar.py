from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

import streamlit as st

from auth_utils import (
    clear_auth,
    is_admin_user,
    is_logged_in,
    is_pro_user,
    refresh_profile,
)
from components.language_selector import render_language_selector
from components.ui import apply_theme_overrides, get_display_name, get_initials, safe_html
from i18n import get_locale, t


APP_VERSION: Final[str] = "v3.0 FINAL"
THEME_KEY: Final[str] = "tm_theme"
THEMES: Final[tuple[str, ...]] = ("system", "light", "dark")

COPY: Final[dict[str, dict[str, str]]] = {
    "en": {"welcome":"Welcome back","guest":"Guest","premium":"Premium Member","starter":"Starter Workspace","create":"Create account","signin":"Sign in","sync":"Sync","workspace":"Workspace","pro_tools":"Pro tools","recruiter":"Recruiter Workspace","account":"Account","company":"Company","refresh":"Refresh profile","health":"System health","ready":"Ready","live":"Live","quick":"Quick actions","analyze":"Analyze CV","ats":"Check ATS","rewrite":"Rewrite CV","appearance":"Appearance","theme":"Theme","system":"System","light":"Light","dark":"Dark","owner":"Founder & Owner","original":"Original SaaS Product","tagline":"AI Career Intelligence Platform"},
    "sr_latn": {"welcome":"Dobro došli","guest":"Gost","premium":"Premium član","starter":"Početni radni prostor","create":"Kreirajte nalog","signin":"Prijavite se","sync":"Sinhronizacija","workspace":"Radni prostor","pro_tools":"Pro alati","recruiter":"Regruterski radni prostor","account":"Nalog","company":"Kompanija","refresh":"Osveži profil","health":"Status sistema","ready":"Spremno","live":"Aktivno","quick":"Brze akcije","analyze":"Analiziraj CV","ats":"Proveri ATS","rewrite":"Prepravi CV","appearance":"Izgled","theme":"Tema","system":"Sistemska","light":"Svetla","dark":"Tamna","owner":"Osnivač i vlasnik","original":"Originalni SaaS proizvod","tagline":"AI platforma za karijeru"},
    "sr_cyrl": {"welcome":"Добро дошли","guest":"Гост","premium":"Премијум члан","starter":"Почетни радни простор","create":"Креирајте налог","signin":"Пријавите се","sync":"Синхронизација","workspace":"Радни простор","pro_tools":"Про алати","recruiter":"Регрутерски радни простор","account":"Налог","company":"Компанија","refresh":"Освежи профил","health":"Статус система","ready":"Спремно","live":"Активно","quick":"Брзе акције","analyze":"Анализирај CV","ats":"Провери ATS","rewrite":"Преради CV","appearance":"Изглед","theme":"Тема","system":"Системска","light":"Светла","dark":"Тамна","owner":"Оснивач и власник","original":"Оригинални SaaS производ","tagline":"AI платформа за каријеру"},
    "de": {"welcome":"Willkommen zurück","guest":"Gast","premium":"Premium-Mitglied","starter":"Starter-Arbeitsbereich","create":"Konto erstellen","signin":"Anmelden","sync":"Synchronisierung","workspace":"Arbeitsbereich","pro_tools":"Pro-Werkzeuge","recruiter":"Recruiter-Arbeitsbereich","account":"Konto","company":"Unternehmen","refresh":"Profil aktualisieren","health":"Systemstatus","ready":"Bereit","live":"Live","quick":"Schnellaktionen","analyze":"Lebenslauf analysieren","ats":"ATS prüfen","rewrite":"Lebenslauf überarbeiten","appearance":"Darstellung","theme":"Design","system":"System","light":"Hell","dark":"Dunkel","owner":"Gründer & Inhaber","original":"Originales SaaS-Produkt","tagline":"KI-Plattform für Karriereintelligenz"},
    "fr": {"welcome":"Bon retour","guest":"Invité","premium":"Membre Premium","starter":"Espace de démarrage","create":"Créer un compte","signin":"Se connecter","sync":"Synchronisation","workspace":"Espace de travail","pro_tools":"Outils Pro","recruiter":"Espace recruteur","account":"Compte","company":"Entreprise","refresh":"Actualiser le profil","health":"État du système","ready":"Prêt","live":"Actif","quick":"Actions rapides","analyze":"Analyser le CV","ats":"Vérifier l’ATS","rewrite":"Réécrire le CV","appearance":"Apparence","theme":"Thème","system":"Système","light":"Clair","dark":"Sombre","owner":"Fondateur et propriétaire","original":"Produit SaaS original","tagline":"Plateforme d’intelligence de carrière par IA"},
    "es": {"welcome":"Bienvenido de nuevo","guest":"Invitado","premium":"Miembro Premium","starter":"Espacio inicial","create":"Crear cuenta","signin":"Iniciar sesión","sync":"Sincronización","workspace":"Espacio de trabajo","pro_tools":"Herramientas Pro","recruiter":"Espacio de reclutamiento","account":"Cuenta","company":"Empresa","refresh":"Actualizar perfil","health":"Estado del sistema","ready":"Listo","live":"Activo","quick":"Acciones rápidas","analyze":"Analizar CV","ats":"Comprobar ATS","rewrite":"Reescribir CV","appearance":"Apariencia","theme":"Tema","system":"Sistema","light":"Claro","dark":"Oscuro","owner":"Fundador y propietario","original":"Producto SaaS original","tagline":"Plataforma de inteligencia profesional con IA"},
    "it": {"welcome":"Bentornato","guest":"Ospite","premium":"Membro Premium","starter":"Area iniziale","create":"Crea account","signin":"Accedi","sync":"Sincronizzazione","workspace":"Area di lavoro","pro_tools":"Strumenti Pro","recruiter":"Area recruiter","account":"Account","company":"Azienda","refresh":"Aggiorna profilo","health":"Stato del sistema","ready":"Pronto","live":"Attivo","quick":"Azioni rapide","analyze":"Analizza CV","ats":"Controlla ATS","rewrite":"Riscrivi CV","appearance":"Aspetto","theme":"Tema","system":"Sistema","light":"Chiaro","dark":"Scuro","owner":"Fondatore e proprietario","original":"Prodotto SaaS originale","tagline":"Piattaforma di intelligence professionale con IA"},
}


def c(key: str) -> str:
    locale = get_locale()
    return COPY.get(locale, COPY["en"]).get(key, COPY["en"].get(key, key))


def _css() -> None:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"]{background:radial-gradient(circle at top left,rgba(37,99,235,.24),transparent 32%),radial-gradient(circle at bottom right,rgba(16,185,129,.18),transparent 34%),linear-gradient(180deg,#0f172a,#111827 48%,#020617);border-right:1px solid rgba(148,163,184,.2)}
    section[data-testid="stSidebar"] *{color:#e5e7eb}
    section[data-testid="stSidebar"] a{border-radius:15px;padding:.24rem .45rem;font-weight:800;border:1px solid transparent;transition:.16s ease}
    section[data-testid="stSidebar"] a:hover{background:rgba(37,99,235,.18);border-color:rgba(96,165,250,.2);transform:translateX(2px)}
    section[data-testid="stSidebar"] .stButton>button{border-radius:15px!important;font-weight:900!important;border:1px solid rgba(148,163,184,.24)!important;background:rgba(15,23,42,.66)!important;color:#f8fafc!important}
    section[data-testid="stSidebar"] div[data-baseweb="select"]>div,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="combobox"],
    section[data-testid="stSidebar"] .react-aria-ComboBox>div[role="group"]{background:#111827!important;border:1px solid rgba(148,163,184,.34)!important;border-radius:15px!important;color:#f8fafc!important;opacity:1!important}
    section[data-testid="stSidebar"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] div[data-baseweb="select"] input,
    section[data-testid="stSidebar"] div[data-baseweb="select"] div[role="combobox"],
    section[data-testid="stSidebar"] .react-aria-ComboBox input[role="combobox"]{background:transparent!important;color:#f8fafc!important;-webkit-text-fill-color:#f8fafc!important;caret-color:#f8fafc!important;opacity:1!important}
    section[data-testid="stSidebar"] .react-aria-ComboBox input[role="combobox"]::placeholder{color:#94a3b8!important;-webkit-text-fill-color:#94a3b8!important;opacity:1!important}
    section[data-testid="stSidebar"] div[data-baseweb="select"] svg,
    section[data-testid="stSidebar"] .react-aria-ComboBox button[aria-label="Open"],
    section[data-testid="stSidebar"] .react-aria-ComboBox button[aria-label="Open"] svg{background:transparent!important;border:0!important;box-shadow:none!important;fill:#cbd5e1!important;color:#cbd5e1!important;opacity:1!important}
    section[data-testid="stSidebar"] div[data-baseweb="select"]>div:hover,
    section[data-testid="stSidebar"] .react-aria-ComboBox>div[role="group"]:hover{border-color:rgba(96,165,250,.58)!important}
    section[data-testid="stSidebar"] div[data-baseweb="select"]>div:focus-within,
    section[data-testid="stSidebar"] .react-aria-ComboBox>div[role="group"]:focus-within{border-color:#60a5fa!important;box-shadow:0 0 0 3px rgba(96,165,250,.18)!important}
    .tm-side-card{padding:1rem;border-radius:24px;border:1px solid rgba(148,163,184,.22);background:rgba(15,23,42,.72);box-shadow:0 18px 44px rgba(0,0,0,.2);margin:.35rem 0 1rem}
    .tm-side-brand{background:radial-gradient(circle at top left,rgba(37,99,235,.28),transparent 42%),radial-gradient(circle at bottom right,rgba(16,185,129,.18),transparent 44%),rgba(15,23,42,.88)}
    .tm-side-row{display:flex;align-items:center;gap:.78rem}.tm-side-logo{width:54px;height:54px;border-radius:19px;display:flex;align-items:center;justify-content:center;font-size:1.75rem;background:linear-gradient(135deg,#2563eb,#10b981)}
    .tm-side-title{font-size:1.27rem;font-weight:950;color:#f8fafc!important}.tm-side-muted{color:#94a3b8!important;font-size:.8rem;line-height:1.42}
    .tm-side-avatar{width:58px;height:58px;border-radius:21px;background:linear-gradient(135deg,#60a5fa,#34d399);display:flex;align-items:center;justify-content:center;font-weight:950}
    .tm-side-kicker{color:#93c5fd!important;font-size:.7rem;font-weight:950;text-transform:uppercase;letter-spacing:.08em}.tm-side-name{font-weight:950;color:#f8fafc!important}
    .tm-side-section{color:#94a3b8!important;font-size:.7rem;font-weight:950;letter-spacing:.115em;text-transform:uppercase;margin:1.05rem 0 .4rem}
    .tm-side-health{display:flex;justify-content:space-between;padding:.18rem 0;font-size:.76rem}.tm-side-dot{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:#22c55e;margin-right:.35rem;box-shadow:0 0 0 4px rgba(34,197,94,.12)}
    .tm-owner{margin-top:.65rem;padding:.7rem;border-radius:15px;border:1px solid rgba(251,191,36,.28);background:rgba(251,191,36,.07);color:#fde68a!important;font-size:.7rem;font-weight:850}
    </style>
    """, unsafe_allow_html=True)


def _section(title: str) -> None:
    st.markdown(f'<div class="tm-side-section">{safe_html(title)}</div>', unsafe_allow_html=True)


def _brand() -> None:
    st.markdown(
        '<div class="tm-side-card tm-side-brand"><div class="tm-side-row">'
        '<div class="tm-side-logo">🎯</div><div>'
        '<div class="tm-side-title">TalentMatch Pro™</div>'
        f'<div class="tm-side-muted">{safe_html(c("tagline"))}</div>'
        '</div></div></div>',
        unsafe_allow_html=True,
    )


def _user() -> None:
    logged = is_logged_in()
    name = get_display_name() if logged else c("guest")
    initials = get_initials(name) if logged else "TM"
    membership = c("premium") if logged and is_pro_user() else (c("starter") if logged else c("create"))
    plan = "PRO" if logged and is_pro_user() else ("FREE" if logged else c("signin").upper())
    sync = datetime.now(timezone.utc).strftime("%H:%M UTC") if logged else "—"
    st.markdown(
        '<div class="tm-side-card"><div class="tm-side-row">'
        f'<div class="tm-side-avatar">{safe_html(initials)}</div><div>'
        f'<div class="tm-side-kicker">{safe_html(c("welcome"))}</div>'
        f'<div class="tm-side-name">{safe_html(name)}</div>'
        f'<div class="tm-side-muted">{safe_html(membership)}</div>'
        '</div></div>'
        f'<div class="tm-side-muted" style="margin-top:.7rem">{safe_html(plan)} • {safe_html(c("sync"))}: {safe_html(sync)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _sync_theme_selection() -> None:
    """Synchronize the widget theme before the next full Streamlit rerun."""
    selected = str(st.session_state.get("tm_sidebar_theme", "system")).strip().lower()
    st.session_state[THEME_KEY] = selected if selected in THEMES else "system"


def _preferences() -> None:
    _section(f"🌍 {t('language.title', default='Language')}")
    render_language_selector(compact=True, key="tm_sidebar_language")
    _section(f"🎨 {c('appearance')}")

    current = str(st.session_state.get(THEME_KEY, "system")).strip().lower()
    if current not in THEMES:
        current = "system"

    if "tm_sidebar_theme" not in st.session_state:
        st.session_state["tm_sidebar_theme"] = current

    selected = st.selectbox(
        c("theme"),
        THEMES,
        format_func=lambda value: c(value),
        key="tm_sidebar_theme",
        on_change=_sync_theme_selection,
        label_visibility="collapsed",
    )
    st.session_state[THEME_KEY] = selected
    apply_theme_overrides(selected)


def _nav() -> None:
    _section(c("workspace"))
    st.page_link("app.py", label=f"🏠 {t('navigation.dashboard')}")
    st.page_link("pages/cv_analysis.py", label=f"📄 {t('navigation.cv_analysis')}")
    st.page_link("pages/ats_checker.py", label=f"📋 {t('navigation.ats_checker')}")
    st.page_link("pages/cv_rewrite.py", label=f"✍ {t('navigation.cv_rewrite')}")

    _section(c("pro_tools"))
    target = "pages/semantic_match.py" if is_pro_user() else "pages/pricing.py"
    lock = "" if is_pro_user() else " 🔒"
    st.page_link(target, label=f"🧠 {t('navigation.semantic_match')}{lock}")

    _section(c("recruiter"))
    recruiter_target = "pages/recruiter_mode.py" if is_pro_user() else "pages/pricing.py"
    database_target = "pages/candidate_database.py" if is_pro_user() else "pages/pricing.py"
    st.page_link(recruiter_target, label=f"👥 {t('navigation.recruiter_mode')}{lock}")
    st.page_link(database_target, label=f"🗂 {t('navigation.candidate_database')}{lock}")

    _section(c("account"))
    st.page_link("pages/history.py", label=f"📜 {t('navigation.history')}")
    st.page_link("pages/pricing.py", label=f"💳 {t('navigation.pricing')}")
    st.page_link("pages/account.py", label=f"⚙ {t('navigation.account')}")

    if is_admin_user():
        _section(t("navigation.administration", default="Administration"))
        st.page_link(
            "pages/admin_analytics.py",
            label=f"📊 {t('navigation.admin_analytics', default='Admin Analytics')}",
        )

    _section(c("company"))
    st.page_link("pages/about.py", label=f"ℹ {t('navigation.about')}")
    st.page_link("pages/contact.py", label=f"📬 {t('navigation.contact')}")
    st.page_link("pages/terms.py", label=f"📃 {t('navigation.terms')}")
    st.page_link("pages/privacy.py", label=f"🔒 {t('navigation.privacy')}")
    st.page_link("pages/refund.py", label=f"💸 {t('navigation.refund')}")


def _quick_actions() -> None:
    _section(f"⚡ {c('quick')}")
    left, right = st.columns(2)
    with left:
        st.page_link("pages/cv_analysis.py", label=f"📄 {c('analyze')}", use_container_width=True)
        st.page_link("pages/cv_rewrite.py", label=f"✍ {c('rewrite')}", use_container_width=True)
    with right:
        st.page_link("pages/ats_checker.py", label=f"📋 {c('ats')}", use_container_width=True)
        target = "pages/recruiter_mode.py" if is_pro_user() else "pages/pricing.py"
        st.page_link(target, label=f"👥 {t('navigation.recruiter_mode')}", use_container_width=True)


def _auth() -> None:
    st.divider()
    if is_logged_in():
        if st.button(f"🔄 {c('refresh')}", use_container_width=True):
            refresh_profile()
            st.rerun()
        if st.button(f"🚪 {t('navigation.logout')}", use_container_width=True):
            clear_auth()
            st.rerun()
    else:
        st.page_link("pages/login.py", label=f"🔐 {t('navigation.login')}")
        st.page_link("pages/register.py", label=f"📝 {t('navigation.register')}")


def _health_and_footer() -> None:
    ready, live = safe_html(c("ready")), safe_html(c("live"))
    st.markdown(
        '<div class="tm-side-card">'
        f'<div class="tm-side-title" style="font-size:.9rem">🟢 {safe_html(c("health"))}</div>'
        f'<div class="tm-side-health"><span><span class="tm-side-dot"></span>Backend</span><span>{ready}</span></div>'
        f'<div class="tm-side-health"><span><span class="tm-side-dot"></span>Frontend</span><span>{ready}</span></div>'
        f'<div class="tm-side-health"><span><span class="tm-side-dot"></span>Firebase</span><span>{ready}</span></div>'
        f'<div class="tm-side-health"><span><span class="tm-side-dot"></span>PayPal</span><span>{live}</span></div>'
        f'<div class="tm-side-health"><span><span class="tm-side-dot"></span>OpenAI</span><span>{ready}</span></div>'
        '</div>'
        '<div class="tm-side-card tm-side-muted">'
        f'<b style="color:#f8fafc">TalentMatch Pro™ {APP_VERSION}</b><br>{safe_html(c("original"))}<br>'
        'PayPal • OpenAI • PDF • Recruiter Workspace'
        f'<div class="tm-owner">{safe_html(c("owner"))}<br><b>Dejan Jović</b><br>TMP-V3-FINAL-2026</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render the TalentMatch Pro v3 enterprise sidebar."""
    with st.sidebar:
        _css()
        _brand()
        _user()
        _preferences()
        _quick_actions()
        _nav()
        _auth()
        _health_and_footer()
