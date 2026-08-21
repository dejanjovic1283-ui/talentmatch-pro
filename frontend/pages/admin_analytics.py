from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

import streamlit as st

from auth_utils import api_get, is_admin_user, is_logged_in
from components.sidebar import render_sidebar
from components.ui import (
    apply_global_styles,
    render_action_panel,
    render_empty_state,
    render_kpi_card,
    render_page_intro,
    render_section_title,
)


ADMIN_ANALYTICS_ENDPOINT = "/admin/analytics"
ADMIN_ANALYTICS_TIMEOUT_SECONDS = 90

ANALYSIS_MIX_LABELS: tuple[tuple[str, str, str], ...] = (
    ("cv_analysis", "CV Analysis", "📄"),
    ("ats_checker", "ATS Checker", "📋"),
    ("semantic_match", "Semantic Match", "🧠"),
    ("recruiter_mode", "Recruiter Mode", "👥"),
    ("cv_rewrite", "CV Rewrite", "✍️"),
    ("other", "Other", "🗂️"),
)


st.set_page_config(
    page_title="Admin Analytics • TalentMatch Pro",
    page_icon="📊",
    layout="wide",
)

apply_global_styles()
render_sidebar()


def _as_mapping(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _as_non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, int):
        return value if value >= 0 else None

    if isinstance(value, float) and value.is_integer() and value >= 0:
        return int(value)

    return None


def _as_non_negative_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    numeric = float(value)
    if numeric < 0:
        return None

    return numeric


def _as_percentage(value: Any) -> float | None:
    numeric = _as_non_negative_number(value)
    if numeric is None or numeric > 100:
        return None
    return numeric


def _require_int(mapping: Mapping[str, Any], key: str) -> int:
    value = _as_non_negative_int(mapping.get(key))
    if value is None:
        raise ValueError(f"Invalid integer metric: {key}")
    return value


def _require_number(mapping: Mapping[str, Any], key: str) -> float:
    value = _as_non_negative_number(mapping.get(key))
    if value is None:
        raise ValueError(f"Invalid numeric metric: {key}")
    return value


def _require_percentage(mapping: Mapping[str, Any], key: str) -> float:
    value = _as_percentage(mapping.get(key))
    if value is None:
        raise ValueError(f"Invalid percentage metric: {key}")
    return value


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value):,}"
    return f"{value:,.1f}"


def _format_usd(value: float) -> str:
    if float(value).is_integer():
        return f"${int(value):,}"
    return f"${value:,.2f}"


def _format_percentage(value: float) -> str:
    if float(value).is_integer():
        return f"{int(value)}%"
    return f"{value:.1f}%"


def _format_generated_at(value: str) -> str:
    clean = str(value or "").strip()
    if not clean:
        return "Unavailable"

    try:
        parsed = datetime.fromisoformat(clean.replace("Z", "+00:00"))
    except ValueError:
        return "Unavailable"

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    normalized = parsed.astimezone(timezone.utc)
    return normalized.strftime("%Y-%m-%d %H:%M UTC")


def _parse_analytics_payload(payload: Any) -> dict[str, Any]:
    root = _as_mapping(payload)
    if root is None:
        raise ValueError("Analytics payload must be an object.")

    generated_at_raw = root.get("generated_at")
    if not isinstance(generated_at_raw, str) or not generated_at_raw.strip():
        raise ValueError("Missing generated_at.")

    users = _as_mapping(root.get("users"))
    analyses = _as_mapping(root.get("analyses"))
    mix = _as_mapping(root.get("analysis_mix"))
    billing = _as_mapping(root.get("billing"))
    missing_skills_raw = root.get("top_missing_skills")

    if users is None or analyses is None or mix is None or billing is None:
        raise ValueError("Analytics payload sections are incomplete.")

    if not isinstance(missing_skills_raw, list):
        raise ValueError("top_missing_skills must be a list.")

    parsed_missing_skills: list[dict[str, Any]] = []
    for item in missing_skills_raw:
        item_mapping = _as_mapping(item)
        if item_mapping is None:
            raise ValueError("Invalid missing skill entry.")

        name = item_mapping.get("name")
        count = _as_non_negative_int(item_mapping.get("count"))
        if not isinstance(name, str) or not name.strip() or count is None or count <= 0:
            raise ValueError("Invalid missing skill entry.")

        parsed_missing_skills.append(
            {
                "name": name.strip(),
                "count": count,
            }
        )

    parsed_mix = {
        key: _require_int(mix, key)
        for key, _, _ in ANALYSIS_MIX_LABELS
    }

    return {
        "generated_at": generated_at_raw.strip(),
        "users": {
            "total_users": _require_int(users, "total_users"),
            "free_users": _require_int(users, "free_users"),
            "active_pro_users": _require_int(users, "active_pro_users"),
            "paid_subscribers": _require_int(users, "paid_subscribers"),
            "pro_conversion_rate": _require_percentage(users, "pro_conversion_rate"),
        },
        "analyses": {
            "total_analyses": _require_int(analyses, "total_analyses"),
            "scored_analyses": _require_int(analyses, "scored_analyses"),
            "average_score": _require_percentage(analyses, "average_score"),
            "strong_matches": _require_int(analyses, "strong_matches"),
            "competitive_matches": _require_int(analyses, "competitive_matches"),
            "needs_work_matches": _require_int(analyses, "needs_work_matches"),
        },
        "analysis_mix": parsed_mix,
        "top_missing_skills": parsed_missing_skills,
        "billing": {
            "pro_price_usd": _require_number(billing, "pro_price_usd"),
            "estimated_mrr_usd": _require_number(billing, "estimated_mrr_usd"),
        },
    }


def _analytics_error_message(status_code: int | None) -> str:
    if status_code == 401:
        return (
            "Your authenticated session could not be verified. "
            "Sign in again and reopen Admin Analytics."
        )

    if status_code == 403:
        return (
            "This account is not authorized to access administrator analytics. "
            "Admin access is controlled by the backend."
        )

    if status_code == 429:
        return (
            "Admin Analytics is temporarily rate limited. "
            "Wait a moment and try again."
        )

    if status_code is not None and status_code >= 500:
        return (
            "Admin Analytics is temporarily unavailable because the backend "
            "could not complete the analytics request."
        )

    return "Admin Analytics could not be loaded. Please try again."


def _load_analytics() -> dict[str, Any] | None:
    with st.spinner("Loading secure administrator analytics..."):
        response = api_get(
            ADMIN_ANALYTICS_ENDPOINT,
            timeout=ADMIN_ANALYTICS_TIMEOUT_SECONDS,
        )

    status_code = getattr(response, "status_code", None)

    if status_code != 200:
        st.error(_analytics_error_message(status_code))
        return None

    headers = getattr(response, "headers", {}) or {}
    content_type = str(headers.get("content-type", "")).lower()

    if content_type and "json" not in content_type:
        st.error(
            "Admin Analytics returned an unexpected response format. "
            "No analytics data was displayed."
        )
        return None

    try:
        payload = response.json()
    except Exception:
        st.error(
            "Admin Analytics returned an unreadable response. "
            "No analytics data was displayed."
        )
        return None

    try:
        return _parse_analytics_payload(payload)
    except ValueError:
        st.error(
            "Admin Analytics returned an unexpected data schema. "
            "No partial or unverified metrics were displayed."
        )
        return None


def _render_business_overview(data: Mapping[str, Any]) -> None:
    users = data["users"]
    analyses = data["analyses"]
    billing = data["billing"]

    render_section_title(
        "Business overview",
        "Current platform adoption, paid subscriber signal, and aggregate analysis volume.",
    )

    columns = st.columns(4)
    with columns[0]:
        render_kpi_card(
            "Total users",
            f"{users['total_users']:,}",
            icon="👤",
            delta="Registered accounts",
        )
    with columns[1]:
        render_kpi_card(
            "Paid subscribers",
            f"{users['paid_subscribers']:,}",
            icon="💳",
            delta="PayPal-qualified",
        )
    with columns[2]:
        render_kpi_card(
            "Total analyses",
            f"{analyses['total_analyses']:,}",
            icon="📊",
            delta="All persisted analysis records",
        )
    with columns[3]:
        render_kpi_card(
            "Estimated MRR",
            _format_usd(billing["estimated_mrr_usd"]),
            icon="💰",
            delta="Estimate, not recognized revenue",
        )


def _render_product_quality(data: Mapping[str, Any]) -> None:
    analyses = data["analyses"]

    render_section_title(
        "Product quality",
        (
            "Quality metrics use only scored analysis workflows. "
            "CV Rewrite is excluded because its stored score is synthetic."
        ),
    )

    first_row = st.columns(2)
    with first_row[0]:
        render_kpi_card(
            "Scored analyses",
            f"{analyses['scored_analyses']:,}",
            icon="🎯",
            delta="CV Analysis • ATS • Semantic • Recruiter",
        )
    with first_row[1]:
        render_kpi_card(
            "Average score",
            f"{_format_number(analyses['average_score'])}/100",
            icon="📈",
            delta="Across scored analyses only",
        )

    quality_row = st.columns(3)
    with quality_row[0]:
        render_kpi_card(
            "Strong",
            f"{analyses['strong_matches']:,}",
            icon="🔥",
            delta="Score ≥ 75",
        )
    with quality_row[1]:
        render_kpi_card(
            "Competitive",
            f"{analyses['competitive_matches']:,}",
            icon="✅",
            delta="Score 50–74",
        )
    with quality_row[2]:
        render_kpi_card(
            "Needs work",
            f"{analyses['needs_work_matches']:,}",
            icon="🛠️",
            delta="Score < 50",
        )


def _render_plan_intelligence(data: Mapping[str, Any]) -> None:
    users = data["users"]
    billing = data["billing"]
    conversion = float(users["pro_conversion_rate"])

    render_section_title(
        "Plan & conversion intelligence",
        "Free, Pro-enabled, and financially qualified PayPal subscriber signals.",
    )

    columns = st.columns(4)
    with columns[0]:
        render_kpi_card(
            "Free users",
            f"{users['free_users']:,}",
            icon="🌱",
            delta="Not currently Pro-enabled",
        )
    with columns[1]:
        render_kpi_card(
            "Pro-enabled users",
            f"{users['active_pro_users']:,}",
            icon="💎",
            delta="Application access state",
        )
    with columns[2]:
        render_kpi_card(
            "Paid conversion",
            _format_percentage(conversion),
            icon="📈",
            delta="Paid subscribers ÷ total users",
        )
    with columns[3]:
        render_kpi_card(
            "Pro price",
            f"{_format_usd(billing['pro_price_usd'])}/month",
            icon="🏷️",
            delta="PayPal subscription price",
        )

    st.progress(min(max(conversion / 100.0, 0.0), 1.0))
    st.caption(
        "Paid subscriber metrics require a stored PayPal subscription ID and "
        "an active/approved subscription status. Estimated MRR is an operational "
        "estimate and is not recognized accounting revenue."
    )


def _render_analysis_mix(data: Mapping[str, Any]) -> None:
    mix = data["analysis_mix"]
    total = sum(int(mix[key]) for key, _, _ in ANALYSIS_MIX_LABELS)

    render_section_title(
        "Analysis mix",
        "Persisted workflow volume by canonical analysis type.",
    )

    if total == 0:
        render_empty_state(
            title="No analysis activity yet",
            message=(
                "The analytics endpoint is healthy, but there are no persisted "
                "analysis records to distribute across workflows."
            ),
            icon="📊",
        )
        return

    first_row = st.columns(3)
    second_row = st.columns(3)

    for index, (key, label, icon) in enumerate(ANALYSIS_MIX_LABELS):
        target_row = first_row if index < 3 else second_row
        target_column = target_row[index if index < 3 else index - 3]
        count = int(mix[key])
        share = (count / total * 100.0) if total else 0.0

        with target_column:
            render_kpi_card(
                label,
                f"{count:,}",
                icon=icon,
                delta=f"{_format_percentage(share)} of analysis records",
            )


def _render_missing_skills(data: Mapping[str, Any]) -> None:
    skills = data["top_missing_skills"]

    render_section_title(
        "Top missing skills & keywords",
        "Most frequent persisted missing-skill signals across analyzed records.",
    )

    if not skills:
        render_empty_state(
            title="No missing-skill signals yet",
            message=(
                "No persisted missing skills are available for aggregation. "
                "This is a valid zero-data state."
            ),
            icon="🧩",
        )
        return

    for start in range(0, len(skills), 5):
        row_items = skills[start : start + 5]
        columns = st.columns(len(row_items))

        for column, skill in zip(columns, row_items):
            with column:
                render_kpi_card(
                    str(skill["name"]),
                    f"{int(skill['count']):,}",
                    icon="🧩",
                    delta="Missing-skill occurrences",
                )


def _render_platform_status(data: Mapping[str, Any]) -> None:
    billing = data["billing"]

    render_section_title(
        "Platform & data status",
        "How to interpret this administrator snapshot.",
    )

    columns = st.columns(3)
    with columns[0]:
        render_kpi_card(
            "Snapshot generated",
            _format_generated_at(data["generated_at"]),
            icon="🕒",
            delta="Backend-generated UTC timestamp",
        )
    with columns[1]:
        render_kpi_card(
            "Data source",
            "Backend database",
            icon="🗄️",
            delta="Authenticated backend aggregation",
        )
    with columns[2]:
        render_kpi_card(
            "Billing basis",
            f"{_format_usd(billing['pro_price_usd'])}/month",
            icon="🅿️",
            delta="PayPal only",
        )

    with st.container(border=True):
        st.markdown("**Administrator data rules**")
        st.markdown(
            "- **Total Analyses** includes every persisted analysis record.\n"
            "- **Product quality** excludes CV Rewrite because its score is synthetic.\n"
            "- **Strong** = score ≥ 75; **Competitive** = 50–74; **Needs work** = below 50.\n"
            "- **Estimated MRR** is derived from financially qualified PayPal subscribers; "
            "it is not a payment ledger or recognized revenue.\n"
            "- This screen does not invent an “active users” metric because no reliable "
            "last-activity field is available in the current data model."
        )


render_page_intro(
    kicker="ADMIN INTELLIGENCE",
    title="Admin Analytics",
    subtitle=(
        "Secure, real-data visibility into TalentMatch Pro adoption, product quality, "
        "workflow usage, missing-skill demand, and PayPal subscription signals."
    ),
    icon="📊",
    badge="ADMIN ONLY",
)

if not is_logged_in():
    render_empty_state(
        title="Sign in to open Admin Analytics",
        message=(
            "Administrator analytics are private and available only after authentication."
        ),
        icon="🔐",
    )
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

if not is_admin_user():
    render_empty_state(
        title="Administrator access required",
        message=(
            "This page is restricted to accounts authorized by the backend "
            "administrator policy."
        ),
        icon="🛡️",
    )
    st.page_link("app.py", label="🏠 Return to Dashboard")
    st.stop()

render_action_panel(
    title="Administrator intelligence workspace",
    description=(
        "Review live business and product signals from the protected backend analytics "
        "endpoint. No demo metrics or hardcoded dashboard data are used."
    ),
    icon="🛡️",
    eyebrow="SECURE ADMIN CONTROL",
)

toolbar_left, toolbar_right = st.columns([5, 1])
with toolbar_left:
    st.caption(
        "Metrics are generated from persisted users, analysis records, and qualifying "
        "PayPal subscription state."
    )
with toolbar_right:
    if st.button("🔄 Refresh", use_container_width=True):
        st.rerun()

analytics = _load_analytics()
if analytics is None:
    st.stop()

_render_business_overview(analytics)
_render_product_quality(analytics)
_render_plan_intelligence(analytics)
_render_analysis_mix(analytics)
_render_missing_skills(analytics)
_render_platform_status(analytics)
