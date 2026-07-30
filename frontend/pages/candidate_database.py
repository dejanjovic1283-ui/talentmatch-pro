from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

from auth_utils import is_logged_in, is_pro_user
from components.sidebar import render_sidebar
from components.ui import (
    apply_global_styles,
    render_action_panel,
    render_list_cards,
    render_page_intro,
    render_report_panel,
    render_score_card,
    safe_html,
)


APP_NAME = "TalentMatch Pro"
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")
PAGE_TITLE = "Candidate Database"
CANDIDATE_STATUSES = ["new", "shortlisted", "interview", "rejected", "hired"]


st.set_page_config(
    page_title=f"{PAGE_TITLE} | {APP_NAME}",
    page_icon="🗂",
    layout="wide",
)
apply_global_styles()
render_sidebar()


def get_auth_headers() -> Dict[str, str]:
    token = (
        st.session_state.get("id_token")
        or st.session_state.get("firebase_id_token")
        or st.session_state.get("token")
        or st.session_state.get("auth_token")
    )

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def safe_json_loads(value: Any, fallback: Any = None) -> Any:
    if fallback is None:
        fallback = []

    if value is None:
        return fallback
    if isinstance(value, (list, dict)):
        return value
    if not isinstance(value, str):
        return fallback

    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return fallback


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    try:
        response = requests.get(
            f"{BACKEND_URL}{path}",
            headers=get_auth_headers(),
            params=params,
            timeout=60,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not connect to Candidate Database: {exc}") from exc

    if response.status_code == 401:
        st.error("You must be logged in to view Candidate Database.")
        st.stop()

    if response.status_code >= 400:
        raise RuntimeError(
            f"Backend returned {response.status_code}: {response.text[:500]}"
        )

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Backend returned invalid JSON.") from exc


def api_put(path: str, payload: Dict[str, Any]) -> Any:
    try:
        response = requests.put(
            f"{BACKEND_URL}{path}",
            headers={**get_auth_headers(), "Content-Type": "application/json"},
            json=payload,
            timeout=60,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not update candidate: {exc}") from exc

    if response.status_code == 401:
        st.error("You must be logged in to update candidates.")
        st.stop()

    if response.status_code >= 400:
        raise RuntimeError(
            f"Backend returned {response.status_code}: {response.text[:500]}"
        )

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Backend returned invalid JSON.") from exc


def api_delete(path: str) -> None:
    try:
        response = requests.delete(
            f"{BACKEND_URL}{path}",
            headers=get_auth_headers(),
            timeout=60,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not delete candidate: {exc}") from exc

    if response.status_code == 401:
        st.error("You must be logged in to delete candidates.")
        st.stop()

    if response.status_code >= 400:
        raise RuntimeError(
            f"Backend returned {response.status_code}: {response.text[:500]}"
        )


def normalize_candidates(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for key in ("candidates", "items", "results", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value

    return []


def format_date(value: Any) -> str:
    if not value:
        return "—"

    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return text[:16]


def candidate_score(candidate: Dict[str, Any]) -> int:
    for key in ("score", "combined_score", "match_score", "semantic_score"):
        value = candidate.get(key)
        try:
            if value is not None:
                return max(0, min(int(float(str(value).replace("%", "").strip())), 100))
        except (TypeError, ValueError):
            continue
    return 0


def candidate_rank(candidate: Dict[str, Any]) -> int:
    try:
        return int(candidate.get("rank", 0))
    except (TypeError, ValueError):
        return 0


def candidate_status(candidate: Dict[str, Any]) -> str:
    return str(candidate.get("status") or "new").strip().lower()


def candidate_tags(candidate: Dict[str, Any]) -> List[str]:
    tags = safe_json_loads(candidate.get("tags"), [])
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]
    return []


def normalize_text_list(value: Any) -> List[str]:
    parsed = safe_json_loads(value, [])
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()]
    if isinstance(parsed, dict):
        return [json.dumps(parsed, ensure_ascii=False)]
    if parsed:
        return [str(parsed)]
    return []


def list_to_text(items: Any) -> str:
    return ", ".join(normalize_text_list(items))


def refresh_candidates() -> None:
    st.session_state.pop("candidate_database_items", None)


def load_candidates() -> List[Dict[str, Any]]:
    if "candidate_database_items" not in st.session_state:
        payload = api_get("/recruiter/candidates")
        st.session_state["candidate_database_items"] = normalize_candidates(payload)
    return st.session_state["candidate_database_items"]


def render_candidate_database_css() -> None:
    st.markdown(
        """
        <style>
        .tm-cdb-shell {
            display:flex;
            flex-direction:column;
            gap:2.5rem;
            width:100%;
        }

        .tm-cdb-trust-grid,
        .tm-cdb-metric-grid {
            display:grid;
            gap:1rem;
            width:100%;
        }

        .tm-cdb-trust-grid {
            grid-template-columns:repeat(4,minmax(0,1fr));
            margin-top:.35rem;
        }

        .tm-cdb-metric-grid {
            grid-template-columns:repeat(4,minmax(0,1fr));
        }

        .tm-cdb-trust-card,
        .tm-cdb-metric-card,
        .tm-cdb-panel,
        .tm-cdb-summary,
        .tm-cdb-export-card {
            border:1px solid rgba(148,163,184,.22);
            background:rgba(255,255,255,.88);
            box-shadow:0 18px 48px rgba(15,23,42,.06);
            backdrop-filter:blur(14px);
        }

        .tm-cdb-trust-card {
            min-height:112px;
            padding:1rem 1.05rem;
            border-radius:20px;
        }

        .tm-cdb-trust-icon {
            width:38px;
            height:38px;
            border-radius:13px;
            display:flex;
            align-items:center;
            justify-content:center;
            background:rgba(37,99,235,.10);
            font-size:1.05rem;
            margin-bottom:.65rem;
        }

        .tm-cdb-trust-title,
        .tm-cdb-panel-title,
        .tm-cdb-summary-title {
            color:#0f172a;
            font-weight:950;
            letter-spacing:-.025em;
        }

        .tm-cdb-trust-title {
            font-size:.98rem;
            margin-bottom:.2rem;
        }

        .tm-cdb-trust-copy,
        .tm-cdb-panel-copy,
        .tm-cdb-summary-copy {
            color:#64748b;
            line-height:1.55;
        }

        .tm-cdb-trust-copy {
            font-size:.88rem;
        }

        .tm-cdb-metric-card {
            min-height:166px;
            padding:1.25rem;
            border-radius:24px;
            position:relative;
            overflow:hidden;
        }

        .tm-cdb-metric-card:before {
            content:"";
            position:absolute;
            inset:0 0 auto 0;
            height:4px;
            background:linear-gradient(90deg,#2563eb,#10b981);
        }

        .tm-cdb-metric-label {
            color:#2563eb;
            font-size:.75rem;
            font-weight:950;
            letter-spacing:.13em;
            text-transform:uppercase;
            margin-bottom:.65rem;
        }

        .tm-cdb-metric-value {
            color:#0f172a;
            font-size:2.15rem;
            line-height:1;
            letter-spacing:-.055em;
            font-weight:950;
            margin-bottom:.55rem;
        }

        .tm-cdb-metric-note {
            color:#64748b;
            line-height:1.5;
        }

        .tm-cdb-panel {
            border-radius:26px;
            padding:1.35rem;
        }

        .tm-cdb-panel-title {
            font-size:1.15rem;
            margin-bottom:.45rem;
        }

        .tm-cdb-summary {
            border-radius:26px;
            padding:1.45rem;
            border-left:5px solid #2563eb;
            background:
                radial-gradient(circle at 92% 18%,rgba(37,99,235,.10),transparent 30%),
                rgba(255,255,255,.91);
        }

        .tm-cdb-summary-title {
            font-size:1.2rem;
            margin-bottom:.55rem;
        }

        .tm-cdb-status-pill {
            display:inline-flex;
            align-items:center;
            justify-content:center;
            border-radius:999px;
            padding:.4rem .72rem;
            font-size:.78rem;
            font-weight:950;
            letter-spacing:.06em;
            text-transform:uppercase;
            background:rgba(37,99,235,.10);
            color:#1d4ed8;
            border:1px solid rgba(37,99,235,.18);
        }

        .tm-cdb-keyword-wrap {
            display:flex;
            flex-wrap:wrap;
            gap:.55rem;
            margin-top:.7rem;
        }

        .tm-cdb-keyword {
            border-radius:999px;
            padding:.42rem .72rem;
            font-size:.82rem;
            font-weight:850;
            background:rgba(37,99,235,.08);
            color:#1e40af;
            border:1px solid rgba(37,99,235,.14);
        }

        .tm-cdb-export-card {
            padding:1.35rem;
            border-radius:26px;
            background:
                radial-gradient(circle at top right,rgba(16,185,129,.11),transparent 36%),
                rgba(255,255,255,.92);
        }

        .tm-cdb-table [data-testid="stDataFrame"] {
            border:1px solid rgba(148,163,184,.22);
            border-radius:20px;
            overflow:hidden;
            box-shadow:0 14px 36px rgba(15,23,42,.05);
        }

        .tm-cdb-actions [data-testid="stPageLink"] a,
        .tm-cdb-actions div[data-testid="stButton"] > button,
        .tm-cdb-actions div[data-testid="stDownloadButton"] > button {
            min-height:3.2rem;
            border-radius:16px;
            font-weight:900;
        }

        @media (max-width:1100px) {
            .tm-cdb-trust-grid,
            .tm-cdb-metric-grid {
                grid-template-columns:repeat(2,minmax(0,1fr));
            }
        }

        @media (max-width:760px) {
            .tm-cdb-shell {
                gap:2rem;
            }

            .tm-cdb-trust-grid,
            .tm-cdb-metric-grid {
                grid-template-columns:1fr;
            }

            .tm-cdb-trust-card,
            .tm-cdb-metric-card {
                min-height:auto;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_trust_bar() -> None:
    items = (
        ("🧠", "AI-ranked profiles", "Candidates originate from Recruiter Mode intelligence."),
        ("🔐", "Private workspace", "Firebase-authenticated and scoped to your account."),
        ("🏷", "Recruiter controls", "Statuses, favorites, tags, notes, and shortlist workflow."),
        ("📤", "Portable data", "Export the current filtered view as a structured CSV file."),
    )
    cards = "".join(
        (
            '<div class="tm-cdb-trust-card">'
            f'<div class="tm-cdb-trust-icon">{safe_html(icon)}</div>'
            f'<div class="tm-cdb-trust-title">{safe_html(title)}</div>'
            f'<div class="tm-cdb-trust-copy">{safe_html(copy)}</div>'
            "</div>"
        )
        for icon, title, copy in items
    )
    st.markdown(
        f'<div class="tm-cdb-trust-grid">{cards}</div>',
        unsafe_allow_html=True,
    )


def render_metric_grid(
    total_candidates: int,
    favorite_count: int,
    average_score: int,
    high_score_count: int,
) -> None:
    values = (
        ("Total candidates", total_candidates, "Profiles saved in Recruiter Workspace"),
        ("Priority profiles", favorite_count, "Candidates marked as favorites"),
        ("Average score", f"{average_score}%", "Average across the full database"),
        ("Strong matches", high_score_count, "Candidates scoring 80% or higher"),
    )
    cards = "".join(
        (
            '<div class="tm-cdb-metric-card">'
            f'<div class="tm-cdb-metric-label">{safe_html(label)}</div>'
            f'<div class="tm-cdb-metric-value">{safe_html(value)}</div>'
            f'<div class="tm-cdb-metric-note">{safe_html(note)}</div>'
            "</div>"
        )
        for label, value, note in values
    )
    st.markdown(
        f'<div class="tm-cdb-metric-grid">{cards}</div>',
        unsafe_allow_html=True,
    )


def render_candidate_table(candidates: List[Dict[str, Any]]) -> None:
    rows = [
        {
            "ID": candidate.get("id"),
            "Candidate": candidate.get("filename", "Unknown"),
            "Score": candidate_score(candidate),
            "Rank": candidate_rank(candidate),
            "Status": candidate_status(candidate).title(),
            "Favorite": "⭐" if candidate.get("favorite") else "",
            "Tags": ", ".join(candidate_tags(candidate)),
            "Created": format_date(candidate.get("created_at")),
        }
        for candidate in candidates
    ]

    if not rows:
        st.info(
            "No candidates match the current filters. Adjust the filters or save "
            "candidates from Recruiter Mode."
        )
        return

    st.markdown('<div class="tm-cdb-table">', unsafe_allow_html=True)
    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Score",
                help="Combined candidate match score",
                min_value=0,
                max_value=100,
                format="%d%%",
            ),
            "Rank": st.column_config.NumberColumn("Rank", format="%d"),
        },
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_keywords(title: str, values: List[str], empty_message: str) -> None:
    st.markdown(f"#### {title}")
    if not values:
        st.caption(empty_message)
        return

    chips = "".join(
        f'<span class="tm-cdb-keyword">{safe_html(value)}</span>'
        for value in values
    )
    st.markdown(
        f'<div class="tm-cdb-keyword-wrap">{chips}</div>',
        unsafe_allow_html=True,
    )


render_candidate_database_css()

render_page_intro(
    kicker="RECRUITER WORKSPACE",
    title="Candidate Database",
    subtitle=(
        "Search, review, shortlist, annotate, and export AI-ranked candidates from one "
        "secure recruiter workspace. Candidate Database remains fully integrated with "
        "TalentMatch Pro Recruiter Mode."
    ),
    icon="🗂",
    badge="PRO RECRUITER WORKSPACE",
)

if not is_logged_in():
    st.warning("Please login before using Candidate Database.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

if not is_pro_user():
    st.warning("Candidate Database is part of the Pro Recruiter Workspace.")
    st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
    st.stop()

st.markdown('<div class="tm-cdb-shell">', unsafe_allow_html=True)
render_trust_bar()

render_action_panel(
    eyebrow="CANDIDATE OPERATIONS",
    title="Manage the hiring pipeline",
    description=(
        "Return to Recruiter Mode to rank new profiles, refresh this workspace to sync "
        "saved candidates, or use filters below to focus on the strongest shortlist."
    ),
    icon="👥",
)

st.markdown('<div class="tm-cdb-actions">', unsafe_allow_html=True)
workspace_left, workspace_right = st.columns([1, 1])
with workspace_left:
    st.page_link(
        "pages/recruiter_mode.py",
        label="👥 Return to Recruiter Mode",
        use_container_width=True,
    )
with workspace_right:
    if st.button(
        "🔄 Refresh Candidate Database",
        use_container_width=True,
        type="primary",
    ):
        refresh_candidates()
        st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

try:
    candidates = load_candidates()
except Exception as exc:
    st.error(f"Failed to load Candidate Database: {exc}")
    st.stop()

total_candidates = len(candidates)
favorite_count = sum(1 for candidate in candidates if candidate.get("favorite"))
average_score = round(
    sum(candidate_score(candidate) for candidate in candidates) / total_candidates
    if total_candidates
    else 0
)
high_score_count = sum(
    1 for candidate in candidates if candidate_score(candidate) >= 80
)

st.markdown("## Recruiter overview")
st.caption(
    "A live summary of the candidate pipeline currently stored in your Recruiter Workspace."
)
render_metric_grid(
    total_candidates,
    favorite_count,
    average_score,
    high_score_count,
)

st.markdown("## Search and filters")
st.caption(
    "Search candidate evidence, narrow the score threshold, filter by workflow status, "
    "or isolate priority profiles."
)
st.markdown(
    """
    <div class="tm-cdb-panel">
        <div class="tm-cdb-panel-title">🔎 Shortlist controls</div>
        <div class="tm-cdb-panel-copy">
            Filters apply instantly to the candidate table, detail selector, and CSV export.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

filter_cols = st.columns([2.4, 1.2, 1.2, 1.2])
with filter_cols[0]:
    search_query = st.text_input(
        "Search by filename, summary, status or tags",
        placeholder="Search candidates...",
    )
with filter_cols[1]:
    min_score = st.slider(
        "Minimum score",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )
with filter_cols[2]:
    status_filter = st.selectbox(
        "Status",
        ["All", *CANDIDATE_STATUSES],
        index=0,
    )
with filter_cols[3]:
    sort_option = st.selectbox(
        "Sort",
        [
            "Newest first",
            "Oldest first",
            "Score high to low",
            "Score low to high",
            "Rank",
        ],
        index=0,
    )

action_cols = st.columns([1, 1, 3])
with action_cols[0]:
    if st.button("🔄 Refresh", use_container_width=True):
        refresh_candidates()
        st.rerun()
with action_cols[1]:
    only_favorites = st.toggle("Favorites only", value=False)

filtered_candidates = candidates[:]

if search_query.strip():
    query = search_query.strip().lower()
    filtered_candidates = [
        candidate
        for candidate in filtered_candidates
        if query in str(candidate.get("filename", "")).lower()
        or query in str(candidate.get("summary", "")).lower()
        or query in candidate_status(candidate)
        or query in ", ".join(candidate_tags(candidate)).lower()
    ]

filtered_candidates = [
    candidate
    for candidate in filtered_candidates
    if candidate_score(candidate) >= min_score
]

if status_filter != "All":
    filtered_candidates = [
        candidate
        for candidate in filtered_candidates
        if candidate_status(candidate) == status_filter.lower()
    ]

if only_favorites:
    filtered_candidates = [
        candidate
        for candidate in filtered_candidates
        if bool(candidate.get("favorite"))
    ]

if sort_option == "Newest first":
    filtered_candidates.sort(
        key=lambda candidate: str(candidate.get("created_at", "")),
        reverse=True,
    )
elif sort_option == "Oldest first":
    filtered_candidates.sort(
        key=lambda candidate: str(candidate.get("created_at", ""))
    )
elif sort_option == "Score high to low":
    filtered_candidates.sort(key=candidate_score, reverse=True)
elif sort_option == "Score low to high":
    filtered_candidates.sort(key=candidate_score)
elif sort_option == "Rank":
    filtered_candidates.sort(key=candidate_rank)

st.markdown("## Candidate pipeline")
st.caption(
    f"Showing {len(filtered_candidates)} of {total_candidates} saved candidate(s)."
)
render_candidate_table(filtered_candidates)

st.markdown("## Candidate intelligence")
st.caption(
    "Select a candidate to review ranking signals, AI evidence, recruiter notes, "
    "and workflow status."
)

if not filtered_candidates:
    st.info("No candidate is available for detailed review.")
else:
    candidate_options = {
        (
            f"#{candidate.get('id')} · "
            f"{candidate.get('filename', 'Unknown')} · "
            f"{candidate_score(candidate)}%"
        ): candidate
        for candidate in filtered_candidates
    }

    selected_label = st.selectbox(
        "Select candidate",
        list(candidate_options.keys()),
    )
    selected_candidate = candidate_options[selected_label]
    selected_id = selected_candidate.get("id")
    selected_score = candidate_score(selected_candidate)
    selected_rank = candidate_rank(selected_candidate)
    selected_status = candidate_status(selected_candidate)
    selected_favorite = bool(selected_candidate.get("favorite"))

    st.markdown(
        f"""
        <div class="tm-cdb-summary">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap">
                <div>
                    <div class="tm-cdb-summary-title">
                        {safe_html(selected_candidate.get("filename", "Unknown candidate"))}
                    </div>
                    <div class="tm-cdb-summary-copy">
                        {safe_html(selected_candidate.get("summary") or "No AI summary saved.")}
                    </div>
                </div>
                <span class="tm-cdb-status-pill">{safe_html(selected_status)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    detail_cols = st.columns(4)
    with detail_cols[0]:
        render_score_card(
            label="MATCH SCORE",
            value=selected_score,
            caption="Combined recruiter score",
            tone="blue",
        )
    with detail_cols[1]:
        render_score_card(
            label="RANK",
            value=selected_rank,
            caption="Current shortlist position",
            tone="green",
            suffix="",
        )
    with detail_cols[2]:
        render_score_card(
            label="STATUS",
            value=selected_status.upper(),
            caption="Recruiter workflow stage",
            tone="purple",
            suffix="",
        )
    with detail_cols[3]:
        render_score_card(
            label="PRIORITY",
            value="YES" if selected_favorite else "NO",
            caption="Favorite candidate",
            tone="amber",
            suffix="",
        )

    matched_skills = normalize_text_list(
        selected_candidate.get("matched_skills")
    )
    missing_skills = normalize_text_list(
        selected_candidate.get("missing_skills")
    )
    matched_keywords = normalize_text_list(
        selected_candidate.get("matched_keywords")
    )
    missing_keywords = normalize_text_list(
        selected_candidate.get("missing_keywords")
    )
    recommendations = normalize_text_list(
        selected_candidate.get("recommendations")
    )

    evidence_left, evidence_right = st.columns(2)
    with evidence_left:
        st.markdown("### ✅ Matched evidence")
        render_list_cards(
            matched_skills,
            kind="success",
            empty_message="No matched skills saved.",
        )
        render_keywords(
            "Matched keywords",
            matched_keywords,
            "No matched keywords saved.",
        )

    with evidence_right:
        st.markdown("### ⚠️ Missing evidence")
        render_list_cards(
            missing_skills,
            kind="warning",
            empty_message="No missing skills saved.",
        )
        render_keywords(
            "Missing keywords",
            missing_keywords,
            "No missing keywords saved.",
        )

    st.markdown("### 🎯 Recruiter recommendations")
    render_list_cards(
        recommendations,
        kind="info",
        empty_message="No recommendations saved.",
    )

    st.markdown("## Manage candidate")
    st.caption(
        "Update the candidate stage, priority flag, tags, and recruiter notes. "
        "Changes are persisted through the existing Recruiter Candidate API."
    )

    edit_cols = st.columns([1, 1, 2])
    with edit_cols[0]:
        favorite_value = st.checkbox(
            "Favorite",
            value=selected_favorite,
        )
    with edit_cols[1]:
        normalized_status = (
            selected_status if selected_status in CANDIDATE_STATUSES else "new"
        )
        status_value = st.selectbox(
            "Candidate status",
            CANDIDATE_STATUSES,
            index=CANDIDATE_STATUSES.index(normalized_status),
        )
    with edit_cols[2]:
        tags_value = st.text_input(
            "Tags",
            value=", ".join(candidate_tags(selected_candidate)),
            placeholder="backend, python, senior, interview",
        )

    notes_value = st.text_area(
        "Recruiter notes",
        value=str(selected_candidate.get("notes") or ""),
        height=150,
        placeholder="Add notes about this candidate...",
    )

    st.markdown('<div class="tm-cdb-actions">', unsafe_allow_html=True)
    update_cols = st.columns([1, 1, 2])
    with update_cols[0]:
        if st.button(
            "💾 Save changes",
            type="primary",
            use_container_width=True,
        ):
            try:
                payload = {
                    "favorite": favorite_value,
                    "status": status_value,
                    "notes": notes_value,
                    "tags": [
                        tag.strip()
                        for tag in tags_value.split(",")
                        if tag.strip()
                    ],
                }
                api_put(f"/recruiter/candidates/{selected_id}", payload)
                st.success("Candidate updated.")
                refresh_candidates()
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to update candidate: {exc}")

    with update_cols[1]:
        delete_confirmed = st.checkbox("Confirm delete")

    with update_cols[2]:
        if st.button(
            "🗑 Delete candidate",
            use_container_width=True,
            disabled=not delete_confirmed,
        ):
            try:
                api_delete(f"/recruiter/candidates/{selected_id}")
                st.success("Candidate deleted.")
                refresh_candidates()
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to delete candidate: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)

export_rows = [
    {
        "id": candidate.get("id"),
        "filename": candidate.get("filename"),
        "score": candidate_score(candidate),
        "rank": candidate_rank(candidate),
        "status": candidate_status(candidate),
        "favorite": bool(candidate.get("favorite")),
        "tags": ", ".join(candidate_tags(candidate)),
        "summary": candidate.get("summary", ""),
        "matched_skills": list_to_text(candidate.get("matched_skills")),
        "missing_skills": list_to_text(candidate.get("missing_skills")),
        "matched_keywords": list_to_text(candidate.get("matched_keywords")),
        "missing_keywords": list_to_text(candidate.get("missing_keywords")),
        "recommendations": list_to_text(candidate.get("recommendations")),
        "notes": candidate.get("notes", ""),
        "created_at": candidate.get("created_at"),
    }
    for candidate in filtered_candidates
]

csv_data = (
    pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8")
    if export_rows
    else b""
)

st.markdown("## Export center")
render_report_panel(
    title="Candidate Database export",
    description=(
        "Download the current filtered candidate view as CSV, including ranking, "
        "workflow status, tags, evidence, recommendations, notes, and timestamps."
    ),
    icon="📤",
)

st.markdown(
    f"""
    <div class="tm-cdb-export-card">
        <div class="tm-cdb-panel-title">Filtered recruiter dataset</div>
        <div class="tm-cdb-panel-copy">
            {len(export_rows)} candidate record(s) are ready for export. The file reflects
            the active search, score, status, favorite, and sort selections.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="tm-cdb-actions">', unsafe_allow_html=True)
st.download_button(
    "⬇️ Export Candidate Database CSV",
    data=csv_data,
    file_name="talentmatch_candidate_database.csv",
    mime="text/csv",
    use_container_width=True,
    disabled=not bool(export_rows),
)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)
