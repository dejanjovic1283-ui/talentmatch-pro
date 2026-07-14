from __future__ import annotations

import json
import logging
import os
from typing import Any

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

from resilience import (
    CircuitBreakerOpenError,
    ExternalServiceError,
    ExternalServiceTimeoutError,
    ExternalServiceUnavailableError,
    build_resilience_executor,
    get_float_setting,
)


LOGGER = logging.getLogger("talentmatch.openai")

OPENAI_SERVICE_NAME = "OpenAI"
OPENAI_CONFIGURATION_PREFIX = "OPENAI"

SYSTEM_PROMPT = (
    "You are an expert recruitment analyst. "
    "Return ONLY valid JSON with these keys: "
    "score (integer 0-100), summary (string), strengths (array of strings), "
    "weaknesses (array of strings), recommendations (array of strings)."
)

REWRITE_SYSTEM_PROMPT = (
    "You are an expert CV writer and recruiter. "
    "Return ONLY valid JSON with these keys: "
    "headline (string), rewritten_summary (string), "
    "rewritten_bullets (array of strings), "
    "ats_keywords_to_add (array of strings), cautions (array of strings). "
    "Do not invent fake experience. Only improve wording based on the provided CV."
)


class AIServiceError(ExternalServiceError):
    """
    Public OpenAI service exception used by the API layer.

    The existing ``message`` and ``status_code`` attributes are preserved for
    compatibility with the current FastAPI endpoints, while the central
    resilience layer also receives structured service/error metadata.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        *,
        error_code: str = "ai_service_error",
        retryable: bool = False,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(
            service=OPENAI_SERVICE_NAME,
            message=message,
            error_code=error_code,
            status_code=status_code,
            retryable=retryable,
            retry_after_seconds=retry_after_seconds,
        )


OPENAI_RESILIENCE = build_resilience_executor(
    service=OPENAI_SERVICE_NAME,
    prefix=OPENAI_CONFIGURATION_PREFIX,
    logger=LOGGER,
)


def _normalise_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [
        str(item).strip()
        for item in value
        if str(item).strip()
    ]


def _get_openai_timeout_seconds() -> float:
    return get_float_setting(
        "OPENAI_TIMEOUT_SECONDS",
        90.0,
        minimum=1.0,
        maximum=300.0,
    )


def _get_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

    if not api_key:
        raise AIServiceError(
            "OPENAI_API_KEY is missing.",
            status_code=500,
            error_code="openai_configuration_error",
        )

    if not model:
        raise AIServiceError(
            "OPENAI_MODEL is missing.",
            status_code=500,
            error_code="openai_configuration_error",
        )

    client = OpenAI(
        api_key=api_key,
        timeout=_get_openai_timeout_seconds(),
        max_retries=0,
    )
    return client, model


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
        return status_code == 408 or status_code == 409 or status_code == 429 or status_code >= 500

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
            service=OPENAI_SERVICE_NAME,
            message="OpenAI request timed out. Please try again.",
        )
        return AIServiceError(
            timeout_error.message,
            status_code=timeout_error.status_code,
            error_code=timeout_error.error_code,
            retryable=True,
        )

    if isinstance(exc, APIConnectionError):
        unavailable_error = ExternalServiceUnavailableError(
            service=OPENAI_SERVICE_NAME,
            message="OpenAI is temporarily unreachable. Please try again.",
        )
        return AIServiceError(
            unavailable_error.message,
            status_code=unavailable_error.status_code,
            error_code=unavailable_error.error_code,
            retryable=True,
        )

    if isinstance(exc, RateLimitError):
        message = _extract_openai_message(exc)
        return AIServiceError(
            f"OpenAI rate limit or quota exceeded: {message}",
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
            f"OpenAI request was denied: {_extract_openai_message(exc)}",
            status_code=403,
            error_code="openai_permission_denied",
        )

    if isinstance(exc, BadRequestError):
        return AIServiceError(
            f"OpenAI rejected the request: {_extract_openai_message(exc)}",
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
                "OpenAI is temporarily unavailable. Please try again.",
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
        "AI analysis failed because of an unexpected service error.",
        status_code=500,
        error_code="openai_unexpected_error",
    )


def _parse_json_response(raw: str) -> dict[str, Any]:
    if not raw.strip():
        raise AIServiceError(
            "OpenAI returned an empty response.",
            status_code=502,
            error_code="openai_empty_response",
        )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIServiceError(
            "OpenAI returned invalid JSON.",
            status_code=502,
            error_code="openai_invalid_json",
        ) from exc

    if not isinstance(parsed, dict):
        raise AIServiceError(
            "OpenAI returned an unexpected JSON structure.",
            status_code=502,
            error_code="openai_invalid_response_shape",
        )

    return parsed


def _chat_json_completion(
    *,
    system_prompt: str,
    user_prompt: str,
) -> dict[str, Any]:
    client, model = _get_client()

    def operation() -> dict[str, Any]:
        response = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        if not response.choices:
            raise AIServiceError(
                "OpenAI returned no completion choices.",
                status_code=502,
                error_code="openai_empty_choices",
            )

        raw = response.choices[0].message.content or ""
        return _parse_json_response(raw)

    try:
        return OPENAI_RESILIENCE.execute(
            operation,
            operation_name="chat_json_completion",
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


def get_openai_resilience_status() -> dict[str, object]:
    """Return a secret-free circuit-breaker snapshot for observability."""
    return OPENAI_RESILIENCE.circuit_breaker.snapshot()


def analyze_cv_with_ai(cv_text: str, job_description: str) -> dict[str, Any]:
    truncated_cv = cv_text[:15000]
    truncated_job = job_description[:6000]

    user_prompt = f"""
Compare the CV to the job description.

Return practical, concise output.

JOB DESCRIPTION:
{truncated_job}

CV TEXT:
{truncated_cv}
""".strip()

    data = _chat_json_completion(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    try:
        score = max(0, min(100, int(data.get("score", 0))))
    except (TypeError, ValueError):
        score = 0

    summary = (
        str(data.get("summary", "")).strip()
        or "Model did not return a summary."
    )

    return {
        "score": score,
        "summary": summary,
        "strengths": _normalise_list(data.get("strengths")),
        "weaknesses": _normalise_list(data.get("weaknesses")),
        "recommendations": _normalise_list(data.get("recommendations")),
    }


def rewrite_cv_with_ai(
    cv_text: str,
    job_description: str,
) -> dict[str, Any]:
    truncated_cv = cv_text[:15000]
    truncated_job = job_description[:6000]

    user_prompt = f"""
Rewrite the CV content to better match the job description.

Rules:
- Do not invent jobs, tools, companies, degrees, metrics, or seniority.
- Improve clarity, action verbs, and ATS alignment.
- Keep bullets realistic and concise.
- Add keywords only when supported by the CV.

JOB DESCRIPTION:
{truncated_job}

CV TEXT:
{truncated_cv}
""".strip()

    data = _chat_json_completion(
        system_prompt=REWRITE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    return {
        "headline": str(data.get("headline", "")).strip(),
        "rewritten_summary": str(
            data.get("rewritten_summary", "")
        ).strip(),
        "rewritten_bullets": _normalise_list(
            data.get("rewritten_bullets")
        ),
        "ats_keywords_to_add": _normalise_list(
            data.get("ats_keywords_to_add")
        ),
        "cautions": _normalise_list(data.get("cautions")),
    }
