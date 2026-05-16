import math
import os
import re
from typing import Any

from openai import OpenAI

OPENAI_MODEL_EMBEDDING = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small",
)

OPENAI_MODEL_CHAT = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


STOPWORDS = {
    "and", "or", "the", "a", "an", "to", "of", "for", "in", "on", "with",
    "as", "is", "are", "be", "by", "this", "that", "you", "your", "we",
    "our", "will", "from", "at", "it", "their", "they", "them", "role",
    "candidate", "experience", "skills", "strong", "work", "working",
    "build", "building", "product", "what", "have", "has", "about",
    "into", "against", "real", "helps", "using", "job", "description",
}


def clean_text(text: str, max_chars: int = 12000) -> str:
    text = text or ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def get_embedding(text: str) -> list[float]:
    cleaned = clean_text(text)

    response = client.embeddings.create(
        model=OPENAI_MODEL_EMBEDDING,
        input=cleaned,
    )

    return response.data[0].embedding


def extract_keywords(text: str, limit: int = 40) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower())

    keywords: list[str] = []

    for word in words:
        clean = word.strip(".,:;()[]{}")

        if not clean:
            continue

        if clean in STOPWORDS:
            continue

        if clean not in keywords:
            keywords.append(clean)

    priority_terms = [
        "python", "fastapi", "sql", "postgresql", "docker", "firebase",
        "openai", "ai", "saas", "backend", "frontend", "streamlit",
        "authentication", "auth", "storage", "billing", "deployment",
        "cloud", "pdf", "prompt", "database", "api", "apis", "mvp",
        "react", "typescript", "javascript", "aws", "gcp", "azure",
        "kubernetes", "redis", "celery", "stripe", "lemonsqueezy",
    ]

    ordered: list[str] = []

    for term in priority_terms:
        if term in keywords:
            ordered.append(term)

    for keyword in keywords:
        if keyword not in ordered:
            ordered.append(keyword)

    return ordered[:limit]


def keyword_overlap_score(cv_text: str, job_description: str) -> dict[str, Any]:
    job_keywords = extract_keywords(job_description)
    cv_lower = cv_text.lower()

    matched = []
    missing = []

    for keyword in job_keywords:
        if keyword.lower() in cv_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)

    score = round((len(matched) / len(job_keywords)) * 100) if job_keywords else 0

    return {
        "keyword_score": score,
        "total_keywords": len(job_keywords),
        "matched_keywords": matched,
        "missing_keywords": missing,
    }


def semantic_score(cv_text: str, job_description: str) -> int:
    cv_embedding = get_embedding(cv_text)
    job_embedding = get_embedding(job_description)

    similarity = cosine_similarity(cv_embedding, job_embedding)

    score = round(max(0.0, min(similarity, 1.0)) * 100)

    return score


def get_verdict(score: int) -> str:
    if score >= 80:
        return "Strong Semantic Match"

    if score >= 60:
        return "Good Semantic Match"

    return "Weak Semantic Match"


def explain_semantic_match(
    cv_text: str,
    job_description: str,
    semantic_score_value: int,
    keyword_score_value: int,
    matched_keywords: list[str],
    missing_keywords: list[str],
) -> dict[str, Any]:
    prompt = f"""
You are an expert technical recruiter.

Compare the CV against the job description.

Return ONLY valid JSON with this exact structure:
{{
  "summary": "short recruiter-style summary",
  "matched_themes": ["theme 1", "theme 2", "theme 3"],
  "missing_themes": ["gap 1", "gap 2", "gap 3"],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]
}}

Scores:
Semantic score: {semantic_score_value}/100
Keyword score: {keyword_score_value}/100

Matched keywords:
{matched_keywords[:20]}

Missing keywords:
{missing_keywords[:20]}

CV:
{clean_text(cv_text, 9000)}

Job description:
{clean_text(job_description, 5000)}
""".strip()

    response = client.chat.completions.create(
        model=OPENAI_MODEL_CHAT,
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": "You return strict JSON only. No markdown.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    raw = response.choices[0].message.content or "{}"

    try:
        import json

        parsed = json.loads(raw)
    except Exception:
        parsed = {
            "summary": raw,
            "matched_themes": [],
            "missing_themes": [],
            "recommendations": [],
        }

    return {
        "summary": str(parsed.get("summary", "")),
        "matched_themes": list(parsed.get("matched_themes", [])),
        "missing_themes": list(parsed.get("missing_themes", [])),
        "recommendations": list(parsed.get("recommendations", [])),
    }


def analyze_semantic_match(cv_text: str, job_description: str) -> dict[str, Any]:
    cv_text = clean_text(cv_text)
    job_description = clean_text(job_description)

    keywords = keyword_overlap_score(cv_text, job_description)
    semantic = semantic_score(cv_text, job_description)

    keyword_score_value = int(keywords["keyword_score"])

    combined_score = round((semantic * 0.7) + (keyword_score_value * 0.3))

    explanation = explain_semantic_match(
        cv_text=cv_text,
        job_description=job_description,
        semantic_score_value=semantic,
        keyword_score_value=keyword_score_value,
        matched_keywords=keywords["matched_keywords"],
        missing_keywords=keywords["missing_keywords"],
    )

    return {
        "semantic_score": semantic,
        "keyword_score": keyword_score_value,
        "combined_score": combined_score,
        "verdict": get_verdict(combined_score),
        "total_keywords": keywords["total_keywords"],
        "matched_keywords": keywords["matched_keywords"],
        "missing_keywords": keywords["missing_keywords"],
        **explanation,
    }