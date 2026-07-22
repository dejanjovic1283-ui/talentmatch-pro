from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st

from auth_utils import api_post, is_logged_in, is_pro_user
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


st.set_page_config(page_title="Recruiter Mode • TalentMatch Pro", page_icon="👥", layout="wide")
apply_global_styles()
render_sidebar()


DEFAULT_JOB_DESCRIPTION = """Founding Full-Stack AI SaaS Engineer

We are building TalentMatch Pro, an AI-powered SaaS platform that helps job seekers compare their CVs against real job descriptions, identify gaps, and improve their application strategy.

What you will do:
- Build and scale a FastAPI + Streamlit product
- Integrate Firebase authentication and storage
- Ship AI-powered CV analysis with OpenAI
- Own billing workflows with PayPal
- Improve product reliability, UX, and deployment pipelines

Requirements:
- Python
- FastAPI
- PostgreSQL
- Docker
- Firebase
- OpenAI APIs
- PayPal billing
- Streamlit
- Render deployment
- Strong product mindset
""".strip()

BACKEND_URL = os.getenv("BACKEND_URL", "https://api.talentmatchcv.com").rstrip("/")


def get_positive_int_env(name: str, default: int) -> int:
    """Return a positive integer environment value or a safe default."""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        parsed_value = int(raw_value)
    except (TypeError, ValueError):
        return default

    return parsed_value if parsed_value > 0 else default


RECRUITER_MAX_CANDIDATES = get_positive_int_env(
    "RECRUITER_MAX_CANDIDATES",
    100,
)
RECRUITER_REQUEST_TIMEOUT_SECONDS = get_positive_int_env(
    "RECRUITER_REQUEST_TIMEOUT_SECONDS",
    900,
)


def get_auth_headers() -> Dict[str, str]:
    token = (
        st.session_state.get("id_token")
        or st.session_state.get("firebase_id_token")
        or st.session_state.get("token")
        or st.session_state.get("auth_token")
    )
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def save_candidate_to_database(candidate: Dict[str, Any], job_description: str) -> Tuple[bool, str]:
    payload = {
        "filename": candidate["filename"],
        "score": candidate["score"],
        "rank": candidate["rank"],
        "semantic_score": candidate["semantic_score"],
        "keyword_score": candidate["keyword_score"],
        "verdict": candidate["verdict"],
        "summary": candidate["summary"],
        "matched_skills": candidate["strengths"],
        "missing_skills": candidate["weaknesses"],
        "matched_keywords": [],
        "missing_keywords": [],
        "recommendations": candidate["recommendations"],
        "job_description": job_description,
        "status": "new",
        "favorite": False,
        "notes": "",
        "tags": [],
    }

    try:
        response = requests.post(
            f"{BACKEND_URL}/recruiter/candidates",
            headers=get_auth_headers(),
            json=payload,
            timeout=60,
        )
    except requests.RequestException as exc:
        return False, f"Network error while saving {candidate['filename']}: {exc}"

    if response.status_code in (200, 201):
        return True, f"{candidate['filename']} saved to Candidate Database."

    if response.status_code == 409:
        return False, f"{candidate['filename']} is already saved in Candidate Database."

    try:
        detail = response.json()
    except ValueError:
        detail = response.text[:500]

    return False, f"Could not save {candidate['filename']}: {response.status_code} - {detail}"


def normalize_response(raw: Any) -> Tuple[Optional[Any], Optional[str]]:
    if isinstance(raw, tuple):
        if len(raw) >= 2:
            return raw[0], raw[1]
        if len(raw) == 1:
            return raw[0], None
        return None, "Empty response from backend."
    return raw, None


def response_to_json(response: Any) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if response is None:
        return None, "No response from backend."

    if isinstance(response, dict):
        return response, None

    status_code = getattr(response, "status_code", None)
    text = getattr(response, "text", "") or ""

    if status_code is not None and status_code >= 400:
        try:
            payload = response.json()
            detail = payload.get("detail") or payload.get("error") or payload
        except Exception:
            detail = text[:1000]
        return None, f"Recruiter Mode failed: {status_code} - {detail}"

    try:
        payload = response.json()
    except Exception:
        return None, f"Backend returned invalid JSON: {text[:1000]}"

    if not isinstance(payload, dict):
        return None, "Backend response is not a JSON object."

    if payload.get("error") or payload.get("detail"):
        return None, str(payload.get("error") or payload.get("detail"))

    return payload, None


def normalize_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value if item is not None and str(item).strip()]
    if isinstance(value, str):
        parts = [part.strip() for part in value.replace("\n", ",").split(",")]
        return [part for part in parts if part]
    return [str(value)]


def get_score(data: Dict[str, Any], *keys: str, default: int = 0) -> int:
    for key in keys:
        value = data.get(key)
        if value is not None:
            try:
                return max(0, min(int(float(str(value).replace("%", "").strip())), 100))
            except Exception:
                continue
    return default


def candidate_list(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = (
        result.get("candidates")
        or result.get("ranked_candidates")
        or result.get("rankings")
        or result.get("results")
        or []
    )

    if not isinstance(candidates, list):
        return []

    normalized: List[Dict[str, Any]] = []

    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            continue

        filename = (
            candidate.get("filename")
            or candidate.get("candidate")
            or candidate.get("name")
            or f"Candidate {index}"
        )

        score = get_score(candidate, "score", "combined_score", "match_score")
        semantic_score = get_score(candidate, "semantic_score")
        keyword_score = get_score(candidate, "keyword_score")
        verdict = str(candidate.get("verdict") or ("Strong Match" if score >= 80 else "Good Match" if score >= 60 else "Needs Review"))
        summary = str(candidate.get("summary") or candidate.get("recruiter_summary") or "")
        strengths = normalize_list(candidate.get("strengths") or candidate.get("matched_skills") or candidate.get("matched_themes"))
        weaknesses = normalize_list(candidate.get("weaknesses") or candidate.get("missing_skills") or candidate.get("missing_themes"))
        recommendations = normalize_list(candidate.get("recommendations"))

        normalized.append(
            {
                "rank": int(candidate.get("rank") or index),
                "filename": str(filename),
                "score": score,
                "semantic_score": semantic_score,
                "keyword_score": keyword_score,
                "verdict": verdict,
                "summary": summary,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "recommendations": recommendations,
            }
        )

    normalized.sort(key=lambda item: (item["rank"], -item["score"]))
    return normalized


def draw_wrapped_lines(canvas_obj: Any, text: str, x: float, y: float, max_width: float, line_height: float, font_name: str, font_size: int) -> float:
    words = str(text).split()
    if not words:
        return y - line_height

    line = ""
    for word in words:
        candidate = f"{line} {word}".strip()
        if canvas_obj.stringWidth(candidate, font_name, font_size) <= max_width:
            line = candidate
            continue
        canvas_obj.drawString(x, y, line)
        y -= line_height
        line = word

    if line:
        canvas_obj.drawString(x, y, line)
        y -= line_height

    return y


def build_csv_report(result: Dict[str, Any]) -> str:
    candidates = candidate_list(result)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Rank", "Filename", "Score", "Semantic Score", "Keyword Score", "Verdict", "Summary"])

    for item in candidates:
        writer.writerow(
            [
                item["rank"],
                item["filename"],
                item["score"],
                item["semantic_score"],
                item["keyword_score"],
                item["verdict"],
                item["summary"],
            ]
        )

    return output.getvalue()


def build_text_report(result: Dict[str, Any], job_description: str) -> str:
    candidates = candidate_list(result)
    summary = str(result.get("summary") or result.get("recruiter_summary") or f"Recruiter ranking completed for {len(candidates)} candidate(s).")
    recommendations = normalize_list(result.get("recommendations"))

    lines = [
        "TalentMatch Pro - Recruiter Mode Report",
        "=" * 44,
        f"Generated: {datetime.now(timezone.utc).isoformat()} UTC",
        f"Candidates ranked: {len(candidates)}",
        "",
        "Recruiter Summary",
        "-" * 24,
        summary,
        "",
        "Candidate Ranking",
        "-" * 24,
    ]

    for item in candidates:
        lines.extend(
            [
                f"{item['rank']}. {item['filename']}",
                f"Score: {item['score']}/100",
                f"Semantic Score: {item['semantic_score']}/100",
                f"Keyword Score: {item['keyword_score']}/100",
                f"Verdict: {item['verdict']}",
                f"Summary: {item['summary'] or 'No candidate summary returned.'}",
                "Strengths:",
                *([f"- {value}" for value in item["strengths"]] or ["- No strengths returned."]),
                "Weaknesses / Gaps:",
                *([f"- {value}" for value in item["weaknesses"]] or ["- No weaknesses returned."]),
                "Recommendations:",
                *([f"- {value}" for value in item["recommendations"]] or ["- No candidate recommendations returned."]),
                "",
            ]
        )

    lines.extend(["Overall Recommendations", "-" * 24])
    lines.extend([f"- {item}" for item in recommendations] or ["- No overall recommendations returned."])
    lines.extend(["", "Job Description", "-" * 24, job_description])

    return "\n".join(lines)


def create_pdf_report(result: Dict[str, Any], job_description: str) -> Optional[bytes]:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
    except Exception:
        st.error("PDF export requires ReportLab. Add `reportlab` to frontend requirements.")
        return None

    candidates = candidate_list(result)
    summary = str(result.get("summary") or result.get("recruiter_summary") or f"Recruiter ranking completed for {len(candidates)} candidate(s).")
    recommendations = normalize_list(result.get("recommendations"))

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 18 * mm
    x = margin
    y = height - margin

    def footer_new_page() -> None:
        nonlocal y
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.HexColor("#64748B"))
        pdf.drawString(margin, 12 * mm, "Generated by TalentMatch Pro")
        pdf.drawRightString(width - margin, 12 * mm, f"Page {pdf.getPageNumber()}")
        pdf.showPage()
        y = height - margin

    def ensure_space(required: float = 35 * mm) -> None:
        if y < required:
            footer_new_page()

    def section(title: str) -> None:
        nonlocal y
        ensure_space(28 * mm)
        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(x, y, title)
        y -= 10 * mm

    def paragraph(text: str, font_size: int = 10) -> None:
        nonlocal y
        pdf.setFont("Helvetica", font_size)
        pdf.setFillColor(colors.HexColor("#1E293B"))
        for raw_line in str(text).splitlines() or [""]:
            ensure_space(22 * mm)
            if not raw_line.strip():
                y -= 4 * mm
                continue
            y = draw_wrapped_lines(pdf, raw_line, x, y, width - 2 * margin, 5.4 * mm, "Helvetica", font_size)
            y -= 1.5 * mm

    def bullets(items: List[str], fallback: str) -> None:
        nonlocal y
        values = items if items else [fallback]
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.HexColor("#1E293B"))
        for item in values:
            ensure_space(24 * mm)
            pdf.drawString(x + 4 * mm, y, "•")
            y = draw_wrapped_lines(pdf, item, x + 10 * mm, y, width - 2 * margin - 10 * mm, 5.4 * mm, "Helvetica", 10)
            y -= 1.5 * mm

    pdf.setFillColor(colors.HexColor("#2563EB"))
    pdf.roundRect(x, y - 10 * mm, 5 * mm, 5 * mm, 1 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(x + 8 * mm, y - 8 * mm, "TalentMatch Pro")
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 9)
    pdf.drawRightString(width - margin, y - 8 * mm, "Recruiter Mode")
    y -= 24 * mm

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 28)
    pdf.drawString(x, y, "Recruiter Mode Report")
    y -= 11 * mm

    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.setFont("Helvetica", 11)
    pdf.drawString(x, y, f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    pdf.drawRightString(width - margin, y, f"Candidates: {len(candidates)}")
    y -= 12 * mm

    top = candidates[0] if candidates else None
    card_h = 36 * mm
    pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
    pdf.setFillColor(colors.HexColor("#F8FAFC"))
    pdf.roundRect(x, y - card_h, width - 2 * margin, card_h, 4 * mm, fill=1, stroke=1)

    pdf.setFillColor(colors.HexColor("#0F172A"))
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(x + 8 * mm, y - 15 * mm, "Top Candidate")
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(x + 8 * mm, y - 26 * mm, top["filename"] if top else "No candidate")
    pdf.setFont("Helvetica-Bold", 26)
    pdf.drawRightString(width - margin - 8 * mm, y - 18 * mm, f"{top['score']}/100" if top else "N/A")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColor(colors.HexColor("#64748B"))
    pdf.drawRightString(width - margin - 8 * mm, y - 29 * mm, top["verdict"] if top else "")
    y -= card_h + 14 * mm

    section("Recruiter Summary")
    paragraph(summary)

    section("Candidate Ranking")
    for item in candidates:
        ensure_space(48 * mm)
        pdf.setFillColor(colors.HexColor("#F8FAFC"))
        pdf.setStrokeColor(colors.HexColor("#CBD5E1"))
        pdf.roundRect(x, y - 18 * mm, width - 2 * margin, 18 * mm, 3 * mm, fill=1, stroke=1)

        pdf.setFillColor(colors.HexColor("#0F172A"))
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(x + 6 * mm, y - 7 * mm, f"#{item['rank']} {item['filename']}")
        pdf.drawRightString(width - margin - 6 * mm, y - 7 * mm, f"{item['score']}/100")
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.HexColor("#64748B"))
        pdf.drawString(x + 6 * mm, y - 14 * mm, f"Semantic: {item['semantic_score']} • Keyword: {item['keyword_score']} • {item['verdict']}")
        y -= 24 * mm

        if item["summary"]:
            paragraph(item["summary"], font_size=9)

        if item["strengths"]:
            pdf.setFont("Helvetica-Bold", 10)
            pdf.setFillColor(colors.HexColor("#0F172A"))
            pdf.drawString(x, y, "Strengths")
            y -= 6 * mm
            bullets(item["strengths"], "No strengths returned.")

        if item["weaknesses"]:
            pdf.setFont("Helvetica-Bold", 10)
            pdf.setFillColor(colors.HexColor("#0F172A"))
            pdf.drawString(x, y, "Weaknesses / Gaps")
            y -= 6 * mm
            bullets(item["weaknesses"], "No weaknesses returned.")

    section("Overall Recommendations")
    bullets(recommendations, "No overall recommendations returned.")

    section("Job Description")
    paragraph(job_description)

    footer_new_page()
    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()


def clear_recruiter_state() -> None:
    for key in [
        "recruiter_result",
        "recruiter_filenames",
        "recruiter_job_description",
        "recruiter_csv_report",
        "recruiter_txt_report",
        "recruiter_pdf_report",
        "recruiter_active_job_id",
        "recruiter_job_status",
    ]:
        st.session_state.pop(key, None)


def render_candidate_card(item: Dict[str, Any]) -> None:
    """Render one ranked candidate with consistent recruiter intelligence sections."""
    st.markdown(
        f"""
        <div class="tm-card" style="margin-bottom:1rem">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap">
                <div>
                    <div class="tm-kicker">RANK #{safe_html(item["rank"])}</div>
                    <div class="tm-card-title" style="margin-top:.35rem">
                        {safe_html(item["filename"])}
                    </div>
                </div>
                <span class="tm-pill tm-pill-green">
                    {safe_html(item["score"])}/100 · {safe_html(item["verdict"])}
                </span>
            </div>
            <div class="tm-muted" style="margin-top:.8rem">
                {safe_html(item["summary"] or "No candidate summary returned.")}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    score_col_1, score_col_2, score_col_3 = st.columns(3)
    with score_col_1:
        render_score_card(
            label="OVERALL",
            value=item["score"],
            caption=item["verdict"],
            tone="blue",
        )
    with score_col_2:
        render_score_card(
            label="SEMANTIC",
            value=item["semantic_score"],
            caption="Meaning and role alignment",
            tone="green",
        )
    with score_col_3:
        render_score_card(
            label="KEYWORD",
            value=item["keyword_score"],
            caption="Target-role terminology",
            tone="purple",
        )

    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.markdown("#### ✅ Strengths")
        render_list_cards(
            item["strengths"],
            kind="success",
            empty_message="No strengths returned.",
        )
    with detail_right:
        st.markdown("#### ⚠️ Weaknesses / gaps")
        render_list_cards(
            item["weaknesses"],
            kind="warning",
            empty_message="No weaknesses returned.",
        )

    if item["recommendations"]:
        with st.expander("🎯 Candidate-specific recommendations"):
            render_list_cards(
                item["recommendations"],
                kind="info",
                empty_message="No candidate recommendations returned.",
            )


def render_results(result: Dict[str, Any]) -> None:
    """Render recruiter ranking results and Candidate Database actions."""
    job_description = str(
        st.session_state.get("recruiter_job_description", "")
    )
    candidates = candidate_list(result)
    summary = str(
        result.get("summary")
        or result.get("recruiter_summary")
        or f"Recruiter ranking completed for {len(candidates)} candidate(s)."
    )
    recommendations = normalize_list(result.get("recommendations"))

    if not recommendations:
        seen: set[str] = set()
        for candidate in candidates:
            for recommendation in candidate.get("recommendations", []):
                normalized = recommendation.strip()
                key = normalized.casefold()
                if normalized and key not in seen:
                    seen.add(key)
                    recommendations.append(normalized)

    st.success("Recruiter ranking completed successfully and saved to History.")

    top = candidates[0] if candidates else None
    average_score = (
        round(sum(item["score"] for item in candidates) / len(candidates))
        if candidates
        else 0
    )

    st.markdown("## Recruiter intelligence")
    st.caption(
        "Review the shortlist, compare ranking signals, and move qualified profiles "
        "into Candidate Database."
    )

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    with metric_1:
        render_score_card(
            label="CANDIDATES",
            value=len(candidates),
            caption="Profiles ranked",
            tone="blue",
            suffix="",
        )
    with metric_2:
        render_score_card(
            label="TOP SCORE",
            value=top["score"] if top else 0,
            caption=top["verdict"] if top else "No result",
            tone="green",
        )
    with metric_3:
        render_score_card(
            label="AVERAGE",
            value=average_score,
            caption="Average ranking score",
            tone="purple",
        )
    with metric_4:
        render_score_card(
            label="TOP PROFILE",
            value="READY" if top else "N/A",
            caption=top["filename"] if top else "No candidate",
            tone="amber",
            suffix="",
        )

    st.markdown("## Executive recruiter summary")
    st.markdown(
        f"""
        <div class="tm-card" style="border-left:5px solid #2563eb;padding:1.35rem 1.5rem">
            <div class="tm-kicker">HIRING PERSPECTIVE</div>
            <div class="tm-muted" style="margin-top:.65rem;line-height:1.7">
                {safe_html(summary)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if candidates:
        st.markdown("## Candidate leaderboard")
        st.caption(
            "The leaderboard provides a compact comparison before the detailed candidate review."
        )
        table_rows = [
            {
                "Rank": item["rank"],
                "Candidate": item["filename"],
                "Score": item["score"],
                "Semantic": item["semantic_score"],
                "Keyword": item["keyword_score"],
                "Verdict": item["verdict"],
            }
            for item in candidates
        ]
        st.dataframe(
            table_rows,
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("## Candidate review")
        for item in candidates:
            render_candidate_card(item)
    else:
        st.warning("No ranked candidates were returned.")

    st.markdown("## Overall recommendations")
    render_list_cards(
        recommendations,
        kind="info",
        empty_message="No overall recommendations returned.",
    )

    st.divider()
    st.markdown("## Recruiter Workspace")
    st.caption(
        "Save ranked profiles to Candidate Database for shortlisting, notes, "
        "status tracking, favorites, tags, and export."
    )

    save_all_col, database_col = st.columns([1.2, 1])
    with save_all_col:
        save_all_clicked = st.button(
            "💾 Save all candidates to Candidate Database",
            type="primary",
            use_container_width=True,
            disabled=not bool(candidates),
        )
    with database_col:
        st.page_link(
            "pages/candidate_database.py",
            label="🗂 Open Candidate Database",
            use_container_width=True,
        )

    if save_all_clicked:
        saved_count = 0
        duplicate_count = 0
        messages: List[str] = []

        with st.spinner("Saving candidates to Recruiter Workspace..."):
            for candidate in candidates:
                saved, message = save_candidate_to_database(
                    candidate,
                    job_description,
                )
                messages.append(message)
                if saved:
                    saved_count += 1
                elif "already" in message.casefold():
                    duplicate_count += 1

        if saved_count:
            st.success(
                f"Saved {saved_count} of {len(candidates)} candidate(s) "
                "to Candidate Database."
            )
        elif duplicate_count == len(candidates) and candidates:
            st.info("All ranked candidates are already available in Candidate Database.")

        if saved_count + duplicate_count < len(candidates):
            with st.expander("Save details"):
                for message in messages:
                    st.write(f"• {message}")

    if "recruiter_csv_report" not in st.session_state:
        st.session_state["recruiter_csv_report"] = build_csv_report(result)

    if "recruiter_txt_report" not in st.session_state:
        st.session_state["recruiter_txt_report"] = build_text_report(
            result,
            job_description,
        )

    if "recruiter_pdf_report" not in st.session_state:
        with st.spinner("Preparing PDF report..."):
            st.session_state["recruiter_pdf_report"] = create_pdf_report(
                result,
                job_description,
            )

    st.divider()
    render_report_panel(
        title="Recruiter report center",
        description=(
            "Export the ranked shortlist as CSV and download complete TXT or PDF "
            "reports with recruiter summary, candidate evidence, recommendations, "
            "and Job Description context."
        ),
        icon="📥",
    )

    col_csv, col_txt, col_pdf = st.columns(3)
    with col_csv:
        st.download_button(
            "📊 Export Candidate Ranking (.csv)",
            data=st.session_state["recruiter_csv_report"].encode("utf-8"),
            file_name="talentmatch_candidate_ranking.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col_txt:
        st.download_button(
            "⬇️ Export Recruiter Report (.txt)",
            data=st.session_state["recruiter_txt_report"].encode("utf-8"),
            file_name="talentmatch_recruiter_mode_report.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col_pdf:
        pdf_bytes = st.session_state.get("recruiter_pdf_report")
        if pdf_bytes:
            st.download_button(
                "📄 Export Recruiter Report (.pdf)",
                data=pdf_bytes,
                file_name="talentmatch_recruiter_mode_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button(
                "📄 PDF report unavailable",
                disabled=True,
                use_container_width=True,
            )


render_page_intro(
    kicker="RECRUITER INTELLIGENCE",
    title="Recruiter Mode",
    subtitle=(
        "Rank multiple candidates against one role, compare semantic and keyword "
        "signals, review recruiter evidence, and save qualified profiles to Candidate Database."
    ),
    icon="🏆",
    badge="PRO WORKSPACE",
)

if not is_logged_in():
    st.warning("Please log in before using Recruiter Mode.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

if not is_pro_user():
    st.warning("Recruiter Mode is a Pro feature.")
    st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
    st.stop()

st.markdown("## Rank candidates")
st.caption(
    f"Upload up to {RECRUITER_MAX_CANDIDATES} PDF CVs and compare every candidate against the same complete job description."
)

render_action_panel(
    eyebrow="RECRUITER WORKFLOW",
    title="Prepare the shortlist",
    description=(
        "Use complete source CVs and the exact target role. TalentMatch Pro will rank "
        "candidates using combined, semantic, and keyword signals before you save them "
        "to Candidate Database."
    ),
    icon="🚀",
)

left, right = st.columns([1, 1.15])

with left:
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-card-title">📚 Candidate CVs</div>
            <div class="tm-muted" style="margin-top:.55rem">
                Upload between 1 and {RECRUITER_MAX_CANDIDATES} PDF CVs. Every profile is
                evaluated against the same target role for a consistent comparison.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload Candidate CVs (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
        key="recruiter_candidate_uploads",
    )

    if uploaded_files:
        selected_count = len(uploaded_files)
        st.success(
            f"Selected {selected_count} / {RECRUITER_MAX_CANDIDATES} candidate file(s)."
        )
        with st.expander(
            f"📚 Review selected files ({selected_count})",
            expanded=selected_count <= 10,
        ):
            for uploaded_file in uploaded_files:
                st.caption(
                    f"• {uploaded_file.name} "
                    f"({uploaded_file.size / 1024:.1f} KB)"
                )

with right:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🧾 Job description</div>
            <div class="tm-muted" style="margin-top:.55rem">
                Paste the complete target role once. All uploaded candidates will
                be ranked against the same responsibilities, skills, and requirements.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    job_description = st.text_area(
        "Job Description",
        value=DEFAULT_JOB_DESCRIPTION,
        height=330,
        key="recruiter_job_description_input",
    )

file_count = len(uploaded_files or [])
can_submit = (
    1 <= file_count <= RECRUITER_MAX_CANDIDATES
    and bool(job_description.strip())
)

run_clicked = st.button(
    "🚀 Rank Candidates",
    type="primary",
    use_container_width=True,
    disabled=not can_submit,
)

if file_count > RECRUITER_MAX_CANDIDATES:
    st.error(
        f"Maximum {RECRUITER_MAX_CANDIDATES} candidate CVs are allowed "
        "per ranking run."
    )

if run_clicked:
    if not uploaded_files:
        st.error("Please upload at least one candidate CV.")
        st.stop()

    if len(uploaded_files) > RECRUITER_MAX_CANDIDATES:
        st.error(
            f"Maximum {RECRUITER_MAX_CANDIDATES} candidate CVs are allowed "
            "per ranking run."
        )
        st.stop()

    normalized_job_description = job_description.strip()
    if not normalized_job_description:
        st.error("Please paste the job description.")
        st.stop()

    clear_recruiter_state()
    files = [
        (
            "files",
            (uploaded_file.name, uploaded_file.getvalue(), "application/pdf"),
        )
        for uploaded_file in uploaded_files
    ]
    data = {"job_description": normalized_job_description}

    with st.spinner("Securely queuing recruiter batch..."):
        raw_response = api_post(
            "/recruiter/jobs",
            data=data,
            files=files,
            timeout=RECRUITER_REQUEST_TIMEOUT_SECONDS,
        )

    response, call_error = normalize_response(raw_response)
    if call_error:
        st.error(f"Recruiter Mode failed: {call_error}")
        st.stop()

    payload, parse_error = response_to_json(response)
    if parse_error:
        st.error(parse_error)
        st.stop()
    if not payload or not payload.get("job_id"):
        st.error("Recruiter Mode failed: backend did not return a job ID.")
        st.stop()

    st.session_state["recruiter_active_job_id"] = str(payload["job_id"])
    st.session_state["recruiter_job_status"] = payload
    st.session_state["recruiter_filenames"] = [f.name for f in uploaded_files]
    st.session_state["recruiter_job_description"] = normalized_job_description
    st.success("Recruiter batch queued. Processing continues safely in the background.")
    st.rerun()

active_job_id = st.session_state.get("recruiter_active_job_id")
if active_job_id:
    st.divider()
    st.markdown("## Batch processing status")
    try:
        job_response = requests.get(
            f"{BACKEND_URL}/recruiter/jobs/{active_job_id}",
            headers=get_auth_headers(),
            timeout=60,
        )
    except requests.RequestException as exc:
        st.warning(f"Could not refresh recruiter job status: {exc}")
    else:
        job_payload, job_error = response_to_json(job_response)
        if job_error:
            st.warning(job_error)
        elif job_payload:
            st.session_state["recruiter_job_status"] = job_payload
            status = str(job_payload.get("status") or "queued")
            progress_value = max(0, min(100, int(job_payload.get("progress") or 0)))
            processed = int(job_payload.get("processed_candidates") or 0)
            total = int(job_payload.get("total_candidates") or 0)
            st.progress(
                progress_value,
                text=f"{status.title()} · {processed}/{total} candidates · {progress_value}%",
            )

            if status == "completed" and isinstance(job_payload.get("result"), dict):
                st.session_state["recruiter_result"] = job_payload["result"]
                st.session_state.pop("recruiter_active_job_id", None)
                st.session_state.pop("recruiter_csv_report", None)
                st.session_state.pop("recruiter_txt_report", None)
                st.session_state.pop("recruiter_pdf_report", None)
                st.success(f"Ranking completed for {total} candidate CV(s).")
                st.rerun()
            elif status == "failed":
                st.session_state.pop("recruiter_active_job_id", None)
                st.error(job_payload.get("error_message") or "Recruiter batch failed.")
            else:
                st.caption(
                    "You may leave this page and return later. The job state is stored in the database."
                )
                import time as _time
                _time.sleep(2)
                st.rerun()

result = st.session_state.get("recruiter_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
