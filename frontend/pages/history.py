import csv
import json
import os
from datetime import datetime
from io import StringIO
from urllib.parse import urlencode

import requests
import streamlit as st

from auth_utils import api_get, is_logged_in, is_pro_user


st.set_page_config(page_title="History • TalentMatch Pro", page_icon="📜", layout="wide")

st.title("📜 Analysis History")
st.caption("View, filter, and export your previous CV analyses and reports.")


BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")


def api_url(path: str) -> str:
    clean_path = path if path.startswith("/") else f"/{path}"
    return f"{BACKEND_URL}{clean_path}"


def get_auth_headers() -> dict[str, str]:
    token = st.session_state.get("access_token") or st.session_state.get("token")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


TYPE_LABELS = {
    "cv_analysis": "CV Analysis",
    "cv_rewrite": "CV Rewrite",
    "ats_checker": "ATS",
    "ats": "ATS",
    "semantic_match": "Semantic",
    "recruiter_mode": "Recruiter",
}

FILTER_OPTIONS = {
    "All": None,
    "ATS": "ats_checker",
    "Semantic": "semantic_match",
    "Recruiter": "recruiter_mode",
    "CV Analysis": "cv_analysis",
    "CV Rewrite": "cv_rewrite",
}

BADGE_STYLES = {
    "cv_analysis": ("CV Analysis", "#E8F0FE", "#174EA6"),
    "cv_rewrite": ("CV Rewrite", "#E0F7FA", "#006064"),
    "ats_checker": ("ATS", "#E6F4EA", "#137333"),
    "semantic_match": ("Semantic", "#FEF7E0", "#B06000"),
    "recruiter_mode": ("Recruiter", "#F3E8FD", "#6A1B9A"),
    "ats": ("ATS", "#E6F4EA", "#137333"),
}


def safe_list(value):
    if value is None:
        return []

    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []

        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass

        return [item.strip() for item in raw.split(",") if item.strip()]

    return [str(value).strip()] if str(value).strip() else []


def normalize_type(item: dict) -> str:
    return str(item.get("analysis_type") or "cv_analysis").strip().lower()


def history_label(item: dict) -> str:
    analysis_type = normalize_type(item)
    return TYPE_LABELS.get(analysis_type, analysis_type.replace("_", " ").title())


def render_badge(item: dict) -> None:
    analysis_type = normalize_type(item)
    label, background, color = BADGE_STYLES.get(
        analysis_type,
        (history_label(item), "#ECEFF1", "#263238"),
    )
    st.markdown(
        f"""
        <span style="
            display:inline-block;
            padding:0.25rem 0.7rem;
            border-radius:999px;
            background:{background};
            color:{color};
            font-weight:700;
            font-size:0.85rem;
            margin-bottom:0.5rem;
        ">{label}</span>
        """,
        unsafe_allow_html=True,
    )


def parse_history_response(response):
    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""
    headers = getattr(response, "headers", {}) or {}
    content_type = headers.get("content-type", "")

    if status_code != 200:
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("error") or payload
            return None, f"Failed to load history: {status_code} - {detail}"
        except Exception:
            return None, f"Failed to load history: {status_code} - {text[:1000]}"

    if content_type and "application/json" not in content_type:
        return None, f"Backend returned non-JSON response: {text[:1000]}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    if isinstance(payload, list):
        return payload, None

    if isinstance(payload, dict):
        items = payload.get("items") or payload.get("history") or payload.get("data") or []
        if isinstance(items, list):
            return items, None

    return None, "Backend returned invalid history format."


def make_local_csv(items: list[dict]) -> bytes:
    output = StringIO()
    fieldnames = [
        "created_at",
        "analysis_type",
        "cv_filename",
        "score",
        "summary",
        "matched_skills",
        "missing_skills",
        "recommendations",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for item in items:
        writer.writerow(
            {
                "created_at": item.get("created_at") or item.get("date") or "",
                "analysis_type": history_label(item),
                "cv_filename": item.get("cv_filename") or item.get("filename") or "",
                "score": item.get("score") or item.get("match_score") or 0,
                "summary": item.get("summary") or "",
                "matched_skills": ", ".join(
                    safe_list(item.get("matched_skills") or item.get("strengths") or item.get("matched_keywords"))
                ),
                "missing_skills": ", ".join(
                    safe_list(item.get("missing_skills") or item.get("weaknesses") or item.get("missing_keywords"))
                ),
                "recommendations": " | ".join(safe_list(item.get("recommendations"))),
            }
        )

    return output.getvalue().encode("utf-8-sig")


def build_text_report(item: dict) -> str:
    cv_filename = item.get("cv_filename") or item.get("filename") or "CV"
    score = item.get("score") or item.get("match_score") or 0
    summary = item.get("summary") or item.get("analysis") or ""
    strengths = safe_list(item.get("strengths") or item.get("matched_skills") or item.get("matched_keywords"))
    weaknesses = safe_list(item.get("weaknesses") or item.get("missing_skills") or item.get("missing_keywords"))
    recommendations = safe_list(item.get("recommendations"))
    job_description = item.get("job_description") or item.get("job") or item.get("description") or ""

    lines = [
        "TalentMatch Pro - CV Analysis Report",
        "=" * 42,
        f"Generated: {datetime.utcnow().isoformat()} UTC",
        f"CV file: {cv_filename}",
        f"Type: {history_label(item)}",
        f"Score: {score}/100",
        "",
        "Summary",
        "-" * 20,
        summary or "No summary returned.",
        "",
        "Strengths",
        "-" * 20,
    ]

    lines.extend([f"- {value}" for value in strengths] or ["- No strengths returned."])

    lines.extend(["", "Weaknesses / Gaps", "-" * 20])
    lines.extend([f"- {value}" for value in weaknesses] or ["- No weaknesses returned."])

    lines.extend(["", "Recommendations", "-" * 20])
    lines.extend([f"- {value}" for value in recommendations] or ["- No recommendations returned."])

    if job_description:
        lines.extend(["", "Job Description", "-" * 20, str(job_description)])

    return "\n".join(lines)


def create_pdf_report(item: dict) -> bytes | None:
    strengths = safe_list(item.get("strengths") or item.get("matched_skills") or item.get("matched_keywords"))
    weaknesses = safe_list(item.get("weaknesses") or item.get("missing_skills") or item.get("missing_keywords"))
    recommendations = safe_list(item.get("recommendations"))

    data = {
        "cv_filename": item.get("cv_filename") or item.get("filename") or "CV",
        "score": str(item.get("score") or item.get("match_score") or 0),
        "summary": item.get("summary") or item.get("analysis") or "",
        "strengths_json": json.dumps(strengths, ensure_ascii=False),
        "weaknesses_json": json.dumps(weaknesses, ensure_ascii=False),
        "recommendations_json": json.dumps(recommendations, ensure_ascii=False),
        "job_description": item.get("job_description") or item.get("job") or item.get("description") or "",
    }

    try:
        response = requests.post(
            api_url("/reports/analysis-pdf"),
            headers=get_auth_headers(),
            data=data,
            timeout=120,
        )

        if response.status_code == 403:
            st.warning("🔒 PDF Report is available in Pro.")
            st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
            return None

        if response.status_code == 401:
            st.error("You are not logged in or your session expired. Please log in again.")
            return None

        if response.status_code >= 400:
            st.error(f"PDF report failed. Backend returned {response.status_code}.")
            st.code(response.text)
            return None

        return response.content

    except requests.exceptions.Timeout:
        st.error("PDF report timed out. Please try again.")
        return None

    except Exception as exc:
        st.error(f"PDF report failed: {exc}")
        return None


def safe_report_filename(cv_filename: str) -> str:
    safe_name = "".join(
        char if char.isalnum() or char in {"-", "_"} else "_"
        for char in cv_filename.replace(".pdf", "")
    ).strip("_")

    if not safe_name:
        safe_name = "talentmatch_cv"

    return f"{safe_name}_talentmatch_report"



def history_endpoint(selected_type: str | None) -> str:
    if not selected_type:
        return "/history"
    return "/history?" + urlencode({"analysis_type": selected_type})


if not is_logged_in():
    st.warning("Please login before viewing history.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

left, right = st.columns([2, 1])
with left:
    selected_label = st.radio(
        "Filter by analysis type",
        list(FILTER_OPTIONS.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
with right:
    if st.button("Refresh history", width="stretch"):
        for key in list(st.session_state.keys()):
            if str(key).startswith("history_items::"):
                st.session_state.pop(key, None)
        st.session_state.pop("history_items", None)
        st.session_state.pop("history_filter", None)
        st.rerun()

selected_type = FILTER_OPTIONS[selected_label]
cache_key = f"history_items::{selected_type or 'all'}"

if cache_key not in st.session_state:
    with st.spinner("Loading history..."):
        resp = api_get(history_endpoint(selected_type), timeout=90)
        parsed_items, error = parse_history_response(resp)

        if error:
            st.error(error)
            st.stop()

        st.session_state[cache_key] = parsed_items or []

items_raw = st.session_state.get(cache_key, [])
items: list[dict] = items_raw if isinstance(items_raw, list) else []
all_items_for_counts: list[dict] = items

if selected_type is not None:
    # Load all records once for global counters.
    if "history_items::all" not in st.session_state:
        with st.spinner("Loading counters..."):
            resp_all = api_get("/history", timeout=90)
            parsed_all, err_all = parse_history_response(resp_all)
            if err_all or not isinstance(parsed_all, list):
                all_items_for_counts = items
            else:
                all_items_for_counts = parsed_all
            st.session_state["history_items::all"] = all_items_for_counts
    else:
        cached_all = st.session_state.get("history_items::all", [])
        all_items_for_counts = cached_all if isinstance(cached_all, list) else []

counts = {
    "total": len(all_items_for_counts),
    "ats_checker": sum(1 for item in all_items_for_counts if normalize_type(item) in {"ats_checker", "ats"}),
    "semantic_match": sum(1 for item in all_items_for_counts if normalize_type(item) == "semantic_match"),
    "recruiter_mode": sum(1 for item in all_items_for_counts if normalize_type(item) == "recruiter_mode"),
    "cv_analysis": sum(1 for item in all_items_for_counts if normalize_type(item) == "cv_analysis"),
    "cv_rewrite": sum(1 for item in all_items_for_counts if normalize_type(item) == "cv_rewrite"),
}

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total", counts["total"])
m2.metric("ATS", counts["ats_checker"])
m3.metric("Semantic", counts["semantic_match"])
m4.metric("Recruiter", counts["recruiter_mode"])
m5.metric("CV Analysis", counts["cv_analysis"])
m6.metric("CV Rewrite", counts["cv_rewrite"])

st.divider()

csv_bytes = make_local_csv(items)

st.download_button(
    "⬇️ Download History CSV",
    data=csv_bytes,
    file_name="talentmatch_history.csv",
    mime="text/csv",
    width="stretch",
    disabled=not items,
)

if not items:
    st.info("No analyses found for this filter.")
    st.page_link("app.py", label="🚀 Run your first CV analysis")
    st.stop()

for idx, item in enumerate(items, start=1):
    if not isinstance(item, dict):
        continue

    score = item.get("score") or item.get("match_score") or 0
    cv_file = item.get("cv_filename") or item.get("cv_file") or item.get("filename") or item.get("file_name") or "CV"
    created_at = item.get("created_at") or item.get("date") or ""
    strengths = safe_list(item.get("matched_skills") or item.get("strengths") or item.get("matched_keywords"))
    missing = safe_list(item.get("missing_skills") or item.get("missing_keywords") or item.get("weaknesses"))
    recommendations = safe_list(item.get("recommendations"))
    summary = item.get("summary") or ""

    with st.container(border=True):
        render_badge(item)
        top_left, top_mid, top_right = st.columns([2.4, 1, 1])
        with top_left:
            st.subheader(f"{idx}. {cv_file}")
            if created_at:
                st.caption(str(created_at))
        with top_mid:
            st.caption("Score")
            st.metric(label="Score", value=f"{score}/100")
        with top_right:
            st.caption("Type")
            st.metric(
                label="Status",
                value=history_label(item)
            )

        if summary:
            st.markdown("**Summary**")
            st.write(summary)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("✅ **Strengths / Matched Skills**")
            if strengths:
                for skill in strengths:
                    st.markdown(f"- {skill}")
            else:
                st.caption("No matched skills saved.")

        with col2:
            st.markdown("❌ **Missing Skills**")
            if missing:
                for skill in missing:
                    st.markdown(f"- {skill}")
            else:
                st.caption("No missing skills saved.")

        if recommendations:
            st.markdown("💡 **Recommendations**")
            for rec in recommendations:
                st.markdown(f"- {rec}")

        st.markdown("---")
        st.markdown("### Download Report")

        report_text = build_text_report(item)
        report_filename = safe_report_filename(cv_file)

        report_col1, report_col2 = st.columns(2)

        with report_col1:
            st.download_button(
                label="⬇️ Download Report TXT",
                data=report_text.encode("utf-8"),
                file_name=f"{report_filename}.txt",
                mime="text/plain",
                width="stretch",
                key=f"history_txt_{idx}_{cv_file}_{created_at}",
            )

        with report_col2:
            if is_pro_user():
                pdf_report_bytes = create_pdf_report(item)

                if pdf_report_bytes:
                    st.download_button(
                        label="📄 Download PDF Report",
                        data=pdf_report_bytes,
                        file_name=f"{report_filename}.pdf",
                        mime="application/pdf",
                        width="stretch",
                        key=f"history_pdf_{idx}_{cv_file}_{created_at}",
                    )
            else:
                st.info("🔒 PDF Report is available in Pro.")
                st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
