import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

try:
    from components.sidebar import render_sidebar
except Exception:
    render_sidebar = None


APP_NAME = "TalentMatch Pro"
BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")
PAGE_TITLE = "Candidate Database"


# ------------------------------------------------------------
# Page config
# ------------------------------------------------------------
st.set_page_config(
    page_title=f"{PAGE_TITLE} | {APP_NAME}",
    page_icon="👥",
    layout="wide",
)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
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
    except Exception:
        return fallback


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    response = requests.get(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        params=params,
        timeout=60,
    )

    if response.status_code == 401:
        st.error("You must be logged in to view Candidate Database.")
        st.stop()

    if response.status_code >= 400:
        raise RuntimeError(f"Backend returned {response.status_code}: {response.text[:500]}")

    if not response.content:
        return None

    return response.json()


def api_put(path: str, payload: Dict[str, Any]) -> Any:
    response = requests.put(
        f"{BACKEND_URL}{path}",
        headers={**get_auth_headers(), "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )

    if response.status_code == 401:
        st.error("You must be logged in to update candidates.")
        st.stop()

    if response.status_code >= 400:
        raise RuntimeError(f"Backend returned {response.status_code}: {response.text[:500]}")

    if not response.content:
        return None

    return response.json()


def api_delete(path: str) -> None:
    response = requests.delete(
        f"{BACKEND_URL}{path}",
        headers=get_auth_headers(),
        timeout=60,
    )

    if response.status_code == 401:
        st.error("You must be logged in to delete candidates.")
        st.stop()

    if response.status_code >= 400:
        raise RuntimeError(f"Backend returned {response.status_code}: {response.text[:500]}")


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
        normalized = text.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return text[:16]


def candidate_score(candidate: Dict[str, Any]) -> int:
    for key in ("score", "combined_score", "match_score", "semantic_score"):
        value = candidate.get(key)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str) and value.isdigit():
            return int(value)

    return 0


def candidate_rank(candidate: Dict[str, Any]) -> int:
    value = candidate.get("rank", 0)
    try:
        return int(value)
    except Exception:
        return 0


def candidate_status(candidate: Dict[str, Any]) -> str:
    return str(candidate.get("status") or "new")


def candidate_tags(candidate: Dict[str, Any]) -> List[str]:
    tags = safe_json_loads(candidate.get("tags"), [])
    if isinstance(tags, list):
        return [str(tag).strip() for tag in tags if str(tag).strip()]

    return []


def list_to_text(items: Any) -> str:
    parsed = safe_json_loads(items, [])

    if isinstance(parsed, list):
        return ", ".join(str(item) for item in parsed if str(item).strip())

    if isinstance(parsed, dict):
        return json.dumps(parsed, ensure_ascii=False)

    return str(items or "")


def render_metric_card(label: str, value: Any, helper: str) -> None:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-label">{label}</div>
            <div class="tm-number">{value}</div>
            <div class="tm-muted">{helper}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_candidate_table(candidates: List[Dict[str, Any]]) -> None:
    rows = []

    for candidate in candidates:
        rows.append(
            {
                "ID": candidate.get("id"),
                "Candidate": candidate.get("filename", "Unknown"),
                "Score": candidate_score(candidate),
                "Rank": candidate_rank(candidate),
                "Status": candidate_status(candidate),
                "Favorite": "⭐" if candidate.get("favorite") else "",
                "Tags": ", ".join(candidate_tags(candidate)),
                "Created": format_date(candidate.get("created_at")),
            }
        )

    if not rows:
        st.info("No candidates found yet. Run Recruiter Mode first, then save candidates to this database.")
        return

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
    )


def refresh_candidates() -> None:
    st.session_state.pop("candidate_database_items", None)


def load_candidates() -> List[Dict[str, Any]]:
    if "candidate_database_items" not in st.session_state:
        payload = api_get("/recruiter/candidates")
        st.session_state["candidate_database_items"] = normalize_candidates(payload)

    return st.session_state["candidate_database_items"]


# ------------------------------------------------------------
# Styling
# ------------------------------------------------------------
st.markdown(
    """
    <style>
        .block-container {
            max-width: 1180px;
            padding-top: 3.5rem;
            padding-bottom: 5rem;
        }

        .tm-hero {
            padding: 2.4rem 2.7rem;
            border-radius: 32px;
            background: linear-gradient(135deg, rgba(220, 231, 255, 0.95), rgba(213, 250, 241, 0.72));
            border: 1px solid rgba(125, 159, 210, 0.25);
            margin-bottom: 2rem;
        }

        .tm-kicker {
            color: #2563eb;
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.28em;
            text-transform: uppercase;
            margin-bottom: 0.7rem;
        }

        .tm-title {
            font-size: 3.2rem;
            line-height: 1.05;
            font-weight: 900;
            color: #182238;
            margin-bottom: 0.8rem;
        }

        .tm-subtitle {
            font-size: 1.2rem;
            color: #657894;
            max-width: 760px;
            line-height: 1.55;
        }

        .tm-card {
            padding: 1.3rem 1.45rem;
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.55);
            border: 1px solid rgba(126, 148, 180, 0.18);
            min-height: 135px;
        }

        .tm-label {
            font-size: 0.78rem;
            color: #2563eb;
            font-weight: 900;
            letter-spacing: 0.22em;
            text-transform: uppercase;
        }

        .tm-number {
            color: #182238;
            font-size: 2.2rem;
            font-weight: 900;
            margin-top: 0.45rem;
        }

        .tm-muted {
            color: #6b7f9a;
            margin-top: 0.25rem;
        }

        .tm-section {
            font-size: 1.65rem;
            font-weight: 900;
            color: #182238;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 18px;
            min-height: 3rem;
            font-weight: 700;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------
if render_sidebar:
    try:
        render_sidebar()
    except TypeError:
        render_sidebar()
    except Exception:
        st.sidebar.title(APP_NAME)
else:
    st.sidebar.title(APP_NAME)
    st.sidebar.page_link("app.py", label="🏠 Dashboard")
    st.sidebar.page_link("pages/cv_analysis.py", label="📄 CV Analysis")
    st.sidebar.page_link("pages/ats_checker.py", label="📋 ATS Checker")
    st.sidebar.page_link("pages/cv_rewrite.py", label="✍️ CV Rewrite")
    st.sidebar.page_link("pages/semantic_match.py", label="🧠 Semantic Match")
    st.sidebar.page_link("pages/recruiter_mode.py", label="👥 Recruiter Mode")


# ------------------------------------------------------------
# Main page
# ------------------------------------------------------------
st.markdown(
    """
    <div class="tm-hero">
        <div class="tm-kicker">Recruiter Workspace</div>
        <div class="tm-title">Candidate Database</div>
        <div class="tm-subtitle">
            Save, search, review and manage candidates ranked by TalentMatch Pro Recruiter Mode.
            This is the foundation for TalentMatch Pro v2.0 ATS-style workflows.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
high_score_count = sum(1 for candidate in candidates if candidate_score(candidate) >= 80)

metric_cols = st.columns(4)
with metric_cols[0]:
    render_metric_card("Total", total_candidates, "Saved candidates")
with metric_cols[1]:
    render_metric_card("Favorites", favorite_count, "Marked as priority")
with metric_cols[2]:
    render_metric_card("Average score", f"{average_score}%", "Across all candidates")
with metric_cols[3]:
    render_metric_card("Strong matches", high_score_count, "Score 80%+")


st.markdown('<div class="tm-section">Search and filters</div>', unsafe_allow_html=True)

filter_cols = st.columns([2.4, 1.2, 1.2, 1.2])
with filter_cols[0]:
    search_query = st.text_input("Search by filename, summary, status or tags", placeholder="Search candidates...")
with filter_cols[1]:
    min_score = st.slider("Minimum score", min_value=0, max_value=100, value=0, step=5)
with filter_cols[2]:
    status_filter = st.selectbox(
        "Status",
        ["All", "new", "shortlisted", "interview", "rejected", "hired"],
        index=0,
    )
with filter_cols[3]:
    sort_option = st.selectbox(
        "Sort",
        ["Newest first", "Oldest first", "Score high to low", "Score low to high", "Rank"],
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
        or query in candidate_status(candidate).lower()
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
        if candidate_status(candidate).lower() == status_filter.lower()
    ]

if only_favorites:
    filtered_candidates = [
        candidate
        for candidate in filtered_candidates
        if bool(candidate.get("favorite"))
    ]

if sort_option == "Newest first":
    filtered_candidates.sort(key=lambda c: str(c.get("created_at", "")), reverse=True)
elif sort_option == "Oldest first":
    filtered_candidates.sort(key=lambda c: str(c.get("created_at", "")))
elif sort_option == "Score high to low":
    filtered_candidates.sort(key=candidate_score, reverse=True)
elif sort_option == "Score low to high":
    filtered_candidates.sort(key=candidate_score)
elif sort_option == "Rank":
    filtered_candidates.sort(key=candidate_rank)


st.markdown('<div class="tm-section">Candidates</div>', unsafe_allow_html=True)
render_candidate_table(filtered_candidates)


st.markdown('<div class="tm-section">Candidate details</div>', unsafe_allow_html=True)

if not filtered_candidates:
    st.info("No candidate selected.")
else:
    candidate_options = {
        f"#{candidate.get('id')} · {candidate.get('filename', 'Unknown')} · {candidate_score(candidate)}%": candidate
        for candidate in filtered_candidates
    }

    selected_label = st.selectbox("Select candidate", list(candidate_options.keys()))
    selected_candidate = candidate_options[selected_label]
    selected_id = selected_candidate.get("id")

    detail_cols = st.columns([1.2, 1.2, 1.2, 1.2])
    with detail_cols[0]:
        st.metric("Score", f"{candidate_score(selected_candidate)}%")
    with detail_cols[1]:
        st.metric("Rank", candidate_rank(selected_candidate))
    with detail_cols[2]:
        st.metric("Status", candidate_status(selected_candidate))
    with detail_cols[3]:
        st.metric("Favorite", "Yes" if selected_candidate.get("favorite") else "No")

    st.markdown("### AI Summary")
    st.write(selected_candidate.get("summary") or "No summary saved.")

    info_cols = st.columns(2)
    with info_cols[0]:
        st.markdown("### Matched skills")
        matched_skills = safe_json_loads(selected_candidate.get("matched_skills"), [])
        if matched_skills:
            for item in matched_skills:
                st.success(str(item))
        else:
            st.caption("No matched skills saved.")

        st.markdown("### Matched keywords")
        matched_keywords = safe_json_loads(selected_candidate.get("matched_keywords"), [])
        if matched_keywords:
            st.write(", ".join(str(item) for item in matched_keywords))
        else:
            st.caption("No matched keywords saved.")

    with info_cols[1]:
        st.markdown("### Missing skills")
        missing_skills = safe_json_loads(selected_candidate.get("missing_skills"), [])
        if missing_skills:
            for item in missing_skills:
                st.warning(str(item))
        else:
            st.caption("No missing skills saved.")

        st.markdown("### Missing keywords")
        missing_keywords = safe_json_loads(selected_candidate.get("missing_keywords"), [])
        if missing_keywords:
            st.write(", ".join(str(item) for item in missing_keywords))
        else:
            st.caption("No missing keywords saved.")

    st.markdown("### Recommendations")
    recommendations = safe_json_loads(selected_candidate.get("recommendations"), [])
    if recommendations:
        for item in recommendations:
            st.info(str(item))
    else:
        st.caption("No recommendations saved.")

    st.divider()

    st.markdown("### Manage candidate")

    edit_cols = st.columns([1, 1, 2])
    with edit_cols[0]:
        favorite_value = st.checkbox("Favorite", value=bool(selected_candidate.get("favorite")))
    with edit_cols[1]:
        status_value = st.selectbox(
            "Candidate status",
            ["new", "shortlisted", "interview", "rejected", "hired"],
            index=["new", "shortlisted", "interview", "rejected", "hired"].index(
                candidate_status(selected_candidate)
                if candidate_status(selected_candidate) in ["new", "shortlisted", "interview", "rejected", "hired"]
                else "new"
            ),
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
        height=140,
        placeholder="Add notes about this candidate...",
    )

    update_cols = st.columns([1, 1, 2])
    with update_cols[0]:
        if st.button("💾 Save changes", use_container_width=True):
            try:
                payload = {
                    "favorite": favorite_value,
                    "status": status_value,
                    "notes": notes_value,
                    "tags": [tag.strip() for tag in tags_value.split(",") if tag.strip()],
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
        if st.button("🗑 Delete candidate", use_container_width=True, disabled=not delete_confirmed):
            try:
                api_delete(f"/recruiter/candidates/{selected_id}")
                st.success("Candidate deleted.")
                refresh_candidates()
                st.rerun()
            except Exception as exc:
                st.error(f"Failed to delete candidate: {exc}")


st.markdown('<div class="tm-section">Export</div>', unsafe_allow_html=True)

export_rows = []
for candidate in filtered_candidates:
    export_rows.append(
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
            "recommendations": list_to_text(candidate.get("recommendations")),
            "created_at": candidate.get("created_at"),
        }
    )

csv_data = pd.DataFrame(export_rows).to_csv(index=False).encode("utf-8") if export_rows else b""

st.download_button(
    "⬇️ Export Candidate Database CSV",
    data=csv_data,
    file_name="talentmatch_candidate_database.csv",
    mime="text/csv",
    use_container_width=True,
    disabled=not bool(export_rows),
)
