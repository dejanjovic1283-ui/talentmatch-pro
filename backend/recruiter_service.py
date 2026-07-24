from __future__ import annotations

from collections.abc import Callable
from typing import Any

from semantic_service import analyze_semantic_match


def candidate_verdict(score: int) -> str:
    if score >= 85:
        return "Top Candidate"
    if score >= 75:
        return "Strong Candidate"
    if score >= 60:
        return "Potential Fit"
    return "Weak Fit"


def analyze_candidate(candidate: dict[str, str], job_description: str) -> dict[str, Any]:
    """Analyze one candidate and return the canonical recruiter result payload."""
    filename = candidate.get("filename", "candidate.pdf")
    cv_text = candidate.get("cv_text", "")

    if not cv_text.strip():
        return {
            "filename": filename,
            "score": 0,
            "match_score": 0,
            "combined_score": 0,
            "semantic_score": 0,
            "keyword_score": 0,
            "verdict": "Could not read CV",
            "summary": "No readable text was extracted from this CV.",
            "matched_themes": [],
            "missing_themes": ["Unreadable or empty CV"],
            "recommendations": [
                "Upload a text-based PDF instead of a scanned image PDF."
            ],
            "matched_keywords": [],
            "missing_keywords": [],
        }

    analysis = analyze_semantic_match(
        cv_text=cv_text,
        job_description=job_description,
    )
    combined_score = int(analysis.get("combined_score", 0) or 0)
    return {
        "filename": filename,
        "score": combined_score,
        "match_score": combined_score,
        "combined_score": combined_score,
        "semantic_score": int(analysis.get("semantic_score", 0) or 0),
        "keyword_score": int(analysis.get("keyword_score", 0) or 0),
        "verdict": candidate_verdict(combined_score),
        "summary": analysis.get("summary", ""),
        "matched_themes": analysis.get("matched_themes", []),
        "missing_themes": analysis.get("missing_themes", []),
        "recommendations": analysis.get("recommendations", []),
        "matched_keywords": analysis.get("matched_keywords", []),
        "missing_keywords": analysis.get("missing_keywords", []),
    }


def build_ranking_result(ranked_candidates: list[dict[str, Any]]) -> dict[str, Any]:
    """Sort candidate results, assign ranks, and build the recruiter summary."""
    ranked = list(ranked_candidates)
    ranked.sort(
        key=lambda item: int(item.get("combined_score", 0) or 0),
        reverse=True,
    )
    for index, item in enumerate(ranked, start=1):
        item["rank"] = index

    top_candidate = ranked[0] if ranked else None
    average_score = (
        round(
            sum(int(item.get("combined_score", 0) or 0) for item in ranked)
            / len(ranked)
        )
        if ranked
        else 0
    )
    top_score = int(top_candidate.get("combined_score", 0) or 0) if top_candidate else 0
    summary = (
        f"Recruiter ranking completed for {len(ranked)} candidate(s). "
        f"Top candidate: {top_candidate.get('filename', 'candidate.pdf')}."
        if top_candidate
        else "Recruiter ranking completed for 0 candidate(s)."
    )
    return {
        "score": top_score,
        "match_score": top_score,
        "combined_score": top_score,
        "average_score": average_score,
        "analysis_type": "recruiter_mode",
        "summary": summary,
        "total_candidates": len(ranked),
        "top_candidate": top_candidate,
        "candidates": ranked,
    }


def rank_candidates(
    candidates: list[dict[str, str]],
    job_description: str,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Backward-compatible in-memory ranking path for small synchronous runs."""
    ranked: list[dict[str, Any]] = []
    total_candidates = len(candidates)
    for processed_count, candidate in enumerate(candidates, start=1):
        ranked.append(analyze_candidate(candidate, job_description))
        if progress_callback is not None:
            progress_callback(processed_count, total_candidates)
    return build_ranking_result(ranked)
