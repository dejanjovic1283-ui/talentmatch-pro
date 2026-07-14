from __future__ import annotations

import json
import logging
import math
import os
import re
from typing import Any, Callable, TypeVar

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    OpenAI,
    PermissionDeniedError,
    RateLimitError,
)

from openai_service import AIServiceError
from resilience import (
    CircuitBreakerOpenError,
    ExternalServiceError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
    build_resilience_executor,
    get_float_setting,
)


T = TypeVar("T")

LOGGER = logging.getLogger("talentmatch.semantic")

OPENAI_SEMANTIC_SERVICE_NAME = "OpenAI Semantic"
OPENAI_CONFIGURATION_PREFIX = "OPENAI"

DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_CHAT_MODEL = "gpt-5-mini"

STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "to",
    "of",
    "for",
    "in",
    "on",
    "with",
    "as",
    "is",
    "are",
    "be",
    "by",
    "this",
    "that",
    "you",
    "your",
    "we",
    "our",
    "will",
    "from",
    "at",
    "it",
    "their",
    "they",
    "them",
    "role",
    "candidate",
    "experience",
    "skills",
    "strong",
    "work",
    "working",
    "build",
    "building",
    "product",
    "what",
    "have",
    "has",
    "about",
    "into",
    "against",
    "real",
    "helps",
    "using",
    "job",
    "description",
}

PRIORITY_TERMS = [
    "python",
    "fastapi",
    "sql",
    "postgresql",
    "docker",
    "firebase",
    "openai",
    "ai",
    "saas",
    "backend",
    "frontend",
    "streamlit",
    "authentication",
    "auth",
    "storage",
    "billing",
    "deployment",
    "cloud",
    "pdf",
    "prompt",
    "database",
    "api",
    "apis",
    "mvp",
    "react",
    "typescript",
    "javascript",
    "aws",
    "gcp",
    "azure",
    "kubernetes",
    "redis",
    "celery",
    "paypal",
]

OPENAI_SEMANTIC_RESILIENCE = build_resilience_executor(
    service=OPENAI_SEMANTIC_SERVICE_NAME,
    prefix=OPENAI_CONFIGURATION_PREFIX,
    logger=LOGGER,
)


def _get_openai_timeout_seconds() -> float:
    return get_float_setting(
        "OPENAI_TIMEOUT_SECONDS",
        90.0,
        minimum=1.0,
        maximum=300.0,
    )


def _get_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise AIServiceError(
            "OPENAI_API_KEY is missing.",
            status_code=500,
            error_code="openai_configuration_error",
        )

    return OpenAI(
        api_key=api_key,
        timeout=_get_openai_timeout_seconds(),
        max_retries=0,
    )


def _get_embedding_model() -> str:
    model = os.getenv(
        "OPENAI_EMBEDDING_MODEL",
        DEFAULT_EMBEDDING_MODEL,
    ).strip()

    if not model:
        raise AIServiceError(
            "OPENAI_EMBEDDING_MODEL is missing.",
            status_code=500,
            error_code="openai_configuration_error",
        )

    return model


def _get_chat_model() -> str:
    model = os.getenv("OPENAI_MODEL", DEFAULT_CHAT_MODEL).strip()

    if not model:
        raise AIServiceError(
            "OPENAI_MODEL is missing.",
            status_code=500,
            error_code="openai_configuration_error",
        )

    return model


def _extract_openai_message(exc: Exception) -> str:
    fallback_message = str(exc).strip() or "Unknown OpenAI error."

    try:
        response = getattr(exc, "response", None)
        if response is None:
            return fallback_message

        body = response.json()
        if not isinstance(body, dict):
            return fallback_message

        error = body.get("error")
        if not isinstance(error, dict):
            return fallback_message

        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()
    except Exception:
        return fallback_message

    return fallback_message


def _is_retryable_openai_error(exc: Exception) -> bool:
    if isinstance(
        exc,
        (
            APITimeoutError,
            APIConnectionError,
            RateLimitError,
        ),
    ):
        return True

    if isinstance(exc, APIStatusError):
        status_code = int(getattr(exc, "status_code", 0) or 0)
        return (
            status_code in {408, 409, 429}
            or status_code >= 500
        )

    return False


def _translate_openai_error(exc: Exception) -> ExternalServiceError:
    if isinstance(exc, AIServiceError):
        return exc

    if isinstance(exc, CircuitBreakerOpenError):
        return AIServiceError(
            exc.message,
            status_code=exc.status_code,
            error_code=exc.error_code,
            retryable=True,
            retry_after_seconds=exc.retry_after_seconds,
        )

    if isinstance(exc, APITimeoutError):
        timeout_error = ExternalServiceTimeoutError(
            service=OPENAI_SEMANTIC_SERVICE_NAME,
            message="OpenAI semantic request timed out. Please try again.",
        )
        return AIServiceError(
            timeout_error.message,
            status_code=timeout_error.status_code,
            error_code=timeout_error.error_code,
            retryable=True,
        )

    if isinstance(exc, APIConnectionError):
        unavailable_error = ExternalServiceUnavailableError(
            service=OPENAI_SEMANTIC_SERVICE_NAME,
            message=(
                "OpenAI semantic service is temporarily unreachable. "
                "Please try again."
            ),
        )
        return AIServiceError(
            unavailable_error.message,
            status_code=unavailable_error.status_code,
            error_code=unavailable_error.error_code,
            retryable=True,
        )

    if isinstance(exc, RateLimitError):
        return AIServiceError(
            (
                "OpenAI rate limit or quota exceeded: "
                f"{_extract_openai_message(exc)}"
            ),
            status_code=429,
            error_code="openai_rate_limit_exceeded",
            retryable=True,
        )

    if isinstance(exc, AuthenticationError):
        return AIServiceError(
            "OpenAI authentication failed. Verify OPENAI_API_KEY.",
            status_code=500,
            error_code="openai_authentication_error",
        )

    if isinstance(exc, PermissionDeniedError):
        return AIServiceError(
            (
                "OpenAI semantic request was denied: "
                f"{_extract_openai_message(exc)}"
            ),
            status_code=403,
            error_code="openai_permission_denied",
        )

    if isinstance(exc, BadRequestError):
        return AIServiceError(
            (
                "OpenAI rejected the semantic request: "
                f"{_extract_openai_message(exc)}"
            ),
            status_code=400,
            error_code="openai_bad_request",
        )

    if isinstance(exc, APIStatusError):
        status_code = int(getattr(exc, "status_code", 500) or 500)
        message = _extract_openai_message(exc)

        if status_code == 429:
            return AIServiceError(
                f"OpenAI rate limit or quota exceeded: {message}",
                status_code=429,
                error_code="openai_rate_limit_exceeded",
                retryable=True,
            )

        if status_code >= 500:
            return AIServiceError(
                "OpenAI semantic service is temporarily unavailable.",
                status_code=503,
                error_code="openai_service_unavailable",
                retryable=True,
            )

        return AIServiceError(
            f"OpenAI API error: {message}",
            status_code=status_code,
            error_code="openai_api_error",
        )

    if isinstance(exc, APIError):
        return AIServiceError(
            f"OpenAI API error: {_extract_openai_message(exc)}",
            status_code=502,
            error_code="openai_api_error",
        )

    if isinstance(exc, json.JSONDecodeError):
        return AIServiceError(
            "OpenAI returned invalid JSON.",
            status_code=502,
            error_code="openai_invalid_json",
        )

    return AIServiceError(
        "Semantic analysis failed because of an unexpected service error.",
        status_code=500,
        error_code="openai_unexpected_error",
    )


def _execute_openai_operation(
    operation: Callable[[], T],
    *,
    operation_name: str,
) -> T:
    try:
        return OPENAI_SEMANTIC_RESILIENCE.execute(
            operation,
            operation_name=operation_name,
            is_retryable=_is_retryable_openai_error,
            translate_error=_translate_openai_error,
            allow_retry=True,
        )
    except CircuitBreakerOpenError as exc:
        translated = _translate_openai_error(exc)
        raise translated from exc
    except ExternalServiceError:
        raise
    except Exception as exc:
        translated = _translate_openai_error(exc)
        raise translated from exc


def _normalise_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


def clean_text(text: str, max_chars: int = 12000) -> str:
    normalised = re.sub(r"\s+", " ", text or "").strip()
    return normalised[:max_chars]


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

    if not cleaned:
        return []

    client = _get_client()
    model = _get_embedding_model()

    def operation() -> list[float]:
        response = client.embeddings.create(
            model=model,
            input=cleaned,
        )

        if not response.data:
            raise AIServiceError(
                "OpenAI returned no embedding data.",
                status_code=502,
                error_code="openai_empty_embedding",
            )

        embedding = response.data[0].embedding

        if not embedding:
            raise AIServiceError(
                "OpenAI returned an empty embedding.",
                status_code=502,
                error_code="openai_empty_embedding",
            )

        return [float(value) for value in embedding]

    return _execute_openai_operation(
        operation,
        operation_name="semantic_embedding",
    )


def extract_keywords(text: str, limit: int = 40) -> list[str]:
    words = re.findall(
        r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}",
        (text or "").lower(),
    )

    keywords: list[str] = []

    for word in words:
        cleaned_word = word.strip(".,:;()[]{}")

        if not cleaned_word:
            continue

        if cleaned_word in STOPWORDS:
            continue

        if cleaned_word not in keywords:
            keywords.append(cleaned_word)

    ordered: list[str] = []

    for term in PRIORITY_TERMS:
        if term in keywords:
            ordered.append(term)

    for keyword in keywords:
        if keyword not in ordered:
            ordered.append(keyword)

    return ordered[: max(0, limit)]


def keyword_overlap_score(
    cv_text: str,
    job_description: str,
) -> dict[str, Any]:
    job_keywords = extract_keywords(job_description)
    cv_lower = (cv_text or "").lower()

    matched: list[str] = []
    missing: list[str] = []

    for keyword in job_keywords:
        if keyword.lower() in cv_lower:
            matched.append(keyword)
        else:
            missing.append(keyword)

    score = (
        round((len(matched) / len(job_keywords)) * 100)
        if job_keywords
        else 0
    )

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
    bounded_similarity = max(0.0, min(similarity, 1.0))

    return round(bounded_similarity * 100)


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

    client = _get_client()
    model = _get_chat_model()

    def operation() -> dict[str, Any]:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
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

        if not response.choices:
            raise AIServiceError(
                "OpenAI returned no semantic explanation choices.",
                status_code=502,
                error_code="openai_empty_choices",
            )

        raw = response.choices[0].message.content or ""

        if not raw.strip():
            raise AIServiceError(
                "OpenAI returned an empty semantic explanation.",
                status_code=502,
                error_code="openai_empty_response",
            )

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AIServiceError(
                "OpenAI returned invalid semantic explanation JSON.",
                status_code=502,
                error_code="openai_invalid_json",
            ) from exc

        if not isinstance(parsed, dict):
            raise AIServiceError(
                "OpenAI returned an unexpected semantic response structure.",
                status_code=502,
                error_code="openai_invalid_response_shape",
            )

        return parsed

    parsed = _execute_openai_operation(
        operation,
        operation_name="semantic_explanation",
    )

    return {
        "summary": str(parsed.get("summary", "")).strip(),
        "matched_themes": _normalise_string_list(
            parsed.get("matched_themes")
        ),
        "missing_themes": _normalise_string_list(
            parsed.get("missing_themes")
        ),
        "recommendations": _normalise_string_list(
            parsed.get("recommendations")
        ),
    }


def analyze_semantic_match(
    cv_text: str,
    job_description: str,
) -> dict[str, Any]:
    cleaned_cv_text = clean_text(cv_text)
    cleaned_job_description = clean_text(job_description)

    if not cleaned_cv_text:
        raise ValueError("CV text is required.")

    if not cleaned_job_description:
        raise ValueError("Job description is required.")

    keywords = keyword_overlap_score(
        cleaned_cv_text,
        cleaned_job_description,
    )
    semantic = semantic_score(
        cleaned_cv_text,
        cleaned_job_description,
    )

    keyword_score_value = int(keywords["keyword_score"])
    combined_score = round(
        (semantic * 0.7) + (keyword_score_value * 0.3)
    )

    explanation = explain_semantic_match(
        cv_text=cleaned_cv_text,
        job_description=cleaned_job_description,
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


def get_semantic_resilience_status() -> dict[str, object]:
    return OPENAI_SEMANTIC_RESILIENCE.circuit_breaker.snapshot()
