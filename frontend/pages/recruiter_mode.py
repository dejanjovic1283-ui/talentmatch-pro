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
from components.ui import apply_global_styles, render_hero, safe_html


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
    ]:
        st.session_state.pop(key, None)


def render_candidate_card(item: Dict[str, Any]) -> None:
    strengths = "".join(f"<span class='tm-pill tm-pill-green'>{safe_html(value)}</span>" for value in item["strengths"][:12])
    weaknesses = "".join(f"<span class='tm-pill'>{safe_html(value)}</span>" for value in item["weaknesses"][:12])
    summary = safe_html(item["summary"] or "No candidate summary returned.")

    st.markdown(
        f"""
        <div class="tm-card" style="margin-bottom:1rem">
            <div class="tm-kicker">Rank #{safe_html(item["rank"])}</div>
            <div class="tm-card-title">{safe_html(item["filename"])}</div>
            <div class="tm-muted">{summary}</div>
            <br>
            <span class="tm-pill tm-pill-green">Score: {safe_html(item["score"])}/100</span>
            <span class="tm-pill">Semantic: {safe_html(item["semantic_score"])}/100</span>
            <span class="tm-pill">Keyword: {safe_html(item["keyword_score"])}/100</span>
            <span class="tm-pill">{safe_html(item["verdict"])}</span>
            <br><br>
            <div class="tm-kicker">Strengths</div>
            <div>{strengths or "<span class='tm-muted'>No strengths returned.</span>"}</div>
            <br>
            <div class="tm-kicker">Weaknesses / Gaps</div>
            <div>{weaknesses or "<span class='tm-muted'>No weaknesses returned.</span>"}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results(result: Dict[str, Any]) -> None:
    job_description = st.session_state.get("recruiter_job_description", "")
    candidates = candidate_list(result)
    summary = str(result.get("summary") or result.get("recruiter_summary") or f"Recruiter ranking completed for {len(candidates)} candidate(s).")
    recommendations = normalize_list(result.get("recommendations"))
    if not recommendations:
        seen = set()
        for candidate in candidates:
            for recommendation in candidate.get("recommendations", []):
                normalized = recommendation.strip()
                key = normalized.casefold()
                if normalized and key not in seen:
                    seen.add(key)
                    recommendations.append(normalized)

    st.success("Recruiter ranking completed.")

    top = candidates[0] if candidates else None
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Candidates", len(candidates))
    with col2:
        st.metric("Top score", f"{top['score']}/100" if top else "N/A")
    with col3:
        st.metric("Top candidate", top["filename"] if top else "N/A")

    st.markdown('<div class="tm-section-title">Recruiter Summary</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="tm-card">
            <div class="tm-muted">{safe_html(summary)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if candidates:
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

        st.markdown('<div class="tm-section-title">Candidate leaderboard</div>', unsafe_allow_html=True)
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        st.markdown('<div class="tm-section-title">Candidate details</div>', unsafe_allow_html=True)
        for item in candidates:
            render_candidate_card(item)
    else:
        st.warning("No ranked candidates returned.")

    st.markdown('<div class="tm-section-title">Overall Recommendations</div>', unsafe_allow_html=True)
    if recommendations:
        for index, item in enumerate(recommendations, start=1):
            st.markdown(
                f"""
                <div class="tm-card" style="margin-bottom:.75rem">
                    <div class="tm-kicker">Recommendation {index}</div>
                    <div class="tm-muted">{safe_html(item)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No overall recommendations returned.")

    st.markdown("---")
    st.markdown('<div class="tm-section-title">Recruiter Workspace</div>', unsafe_allow_html=True)
    st.caption("Save ranked candidates to Candidate Database for shortlisting, notes, status tracking and export.")

    save_all_col, database_col = st.columns([1.2, 1])
    with save_all_col:
        save_all_clicked = st.button(
            "💾 Save all candidates to Candidate Database",
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
        messages: List[str] = []
        with st.spinner("Saving candidates to Recruiter Workspace..."):
            for candidate in candidates:
                saved, message = save_candidate_to_database(candidate, job_description)
                messages.append(message)
                if saved:
                    saved_count += 1

        if saved_count:
            st.success(f"Saved {saved_count} of {len(candidates)} candidate(s) to Candidate Database.")
        if saved_count < len(candidates):
            with st.expander("Save details"):
                for message in messages:
                    st.write(f"• {message}")

    if "recruiter_csv_report" not in st.session_state:
        st.session_state["recruiter_csv_report"] = build_csv_report(result)

    if "recruiter_txt_report" not in st.session_state:
        st.session_state["recruiter_txt_report"] = build_text_report(result, job_description)

    st.markdown("---")
    st.markdown('<div class="tm-section-title">Download Reports</div>', unsafe_allow_html=True)

    col_csv, col_txt, col_pdf = st.columns(3)

    with col_csv:
        st.download_button(
            "📊 Export Ranking (.csv)",
            data=st.session_state["recruiter_csv_report"].encode("utf-8"),
            file_name="talentmatch_candidate_ranking.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col_txt:
        st.download_button(
            "📥 Export Recruiter Report (.txt)",
            data=st.session_state["recruiter_txt_report"].encode("utf-8"),
            file_name="talentmatch_recruiter_mode_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with col_pdf:
        if "recruiter_pdf_report" not in st.session_state:
            with st.spinner("Preparing PDF report..."):
                st.session_state["recruiter_pdf_report"] = create_pdf_report(result, job_description)

        pdf_bytes = st.session_state.get("recruiter_pdf_report")
        if pdf_bytes:
            st.download_button(
                "📄 Export Recruiter Report (.pdf)",
                data=pdf_bytes,
                file_name="talentmatch_recruiter_mode_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )


render_hero(
    "Recruiter Workspace",
    "Recruiter Mode",
    "Rank candidates, review recruiter intelligence and save selected profiles to Candidate Database.",
    "🏆",
)

if not is_logged_in():
    st.warning("Please login before using Recruiter Mode.")
    st.page_link("pages/login.py", label="🔐 Go to Login")
    st.stop()

if not is_pro_user():
    st.warning("Recruiter Mode is a Pro feature.")
    st.page_link("pages/pricing.py", label="💳 Upgrade to Pro")
    st.stop()

st.markdown('<div class="tm-section-title">Rank candidates</div>', unsafe_allow_html=True)

left, right = st.columns([1, 1.25])

with left:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">📚 Candidate CVs</div>
            <div class="tm-muted">Upload multiple PDF CVs. Maximum allowed: 10 candidates per ranking run.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_files = st.file_uploader(
        "Upload Candidate CVs (PDF)",
        type=["pdf"],
        accept_multiple_files=True,
    )

    if uploaded_files:
        st.success(f"Selected {len(uploaded_files)} candidate file(s).")
        for uploaded_file in uploaded_files[:10]:
            st.caption(f"• {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

with right:
    st.markdown(
        """
        <div class="tm-card">
            <div class="tm-card-title">🧾 Job description</div>
            <div class="tm-muted">Paste the target job description once. Every uploaded candidate is ranked against this role.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    job_description = st.text_area("Job Description", value=DEFAULT_JOB_DESCRIPTION, height=330)

file_count = len(uploaded_files or [])
run_clicked = st.button(
    "🚀 Rank Candidates",
    use_container_width=True,
    disabled=file_count == 0 or not job_description.strip(),
)

if run_clicked:
    if not uploaded_files:
        st.error("Please upload at least one candidate CV.")
        st.stop()

    if len(uploaded_files) > 10:
        st.error("Maximum 10 candidate CVs are allowed per ranking run.")
        st.stop()

    if not job_description.strip():
        st.error("Please paste the job description.")
        st.stop()

    clear_recruiter_state()

    files = [
        ("files", (uploaded_file.name, uploaded_file.getvalue(), "application/pdf"))
        for uploaded_file in uploaded_files
    ]
    data = {"job_description": job_description.strip()}

    with st.spinner("Ranking candidates with AI..."):
        raw_response = api_post("/recruiter/rank-candidates", data=data, files=files, timeout=240)

    response, call_error = normalize_response(raw_response)
    if call_error:
        st.error(f"Recruiter Mode failed: {call_error}")
        st.stop()

    payload, parse_error = response_to_json(response)
    if parse_error:
        st.error(parse_error)
        st.stop()

    if not payload:
        st.error("Recruiter Mode failed: empty backend response.")
        st.stop()

    st.session_state["recruiter_result"] = payload
    st.session_state["recruiter_filenames"] = [uploaded_file.name for uploaded_file in uploaded_files]
    st.session_state["recruiter_job_description"] = job_description.strip()

result = st.session_state.get("recruiter_result")
if isinstance(result, dict):
    st.divider()
    render_results(result)
