from __future__ import annotations

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


def rank_candidates(
    candidates: list[dict[str, str]],
    job_description: str,
) -> dict[str, Any]:
    """
    candidates format:
    [
        {
            "filename": "candidate.pdf",
            "cv_text": "extracted pdf text"
        }
    ]
    """

    ranked: list[dict[str, Any]] = []

    for candidate in candidates:
        filename = candidate.get("filename", "candidate.pdf")
        cv_text = candidate.get("cv_text", "")

        if not cv_text.strip():
            ranked.append(
                {
                    "filename": filename,
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
            )
            continue

        analysis = analyze_semantic_match(
            cv_text=cv_text,
            job_description=job_description,
        )

        combined_score = int(analysis.get("combined_score", 0) or 0)

        ranked.append(
            {
                "filename": filename,
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
        )

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

    return {
        "total_candidates": len(ranked),
        "average_score": average_score,
        "top_candidate": top_candidate,
        "candidates": ranked,
    }