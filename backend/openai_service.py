import json
import os
import time
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)


SYSTEM_PROMPT = (
    "You are an expert recruitment analyst. "
    "Return ONLY valid JSON with these keys: "
    "score (integer 0-100), summary (string), strengths (array of strings), "
    "weaknesses (array of strings), recommendations (array of strings)."
)

REWRITE_SYSTEM_PROMPT = (
    "You are an expert CV writer and recruiter. "
    "Return ONLY valid JSON with these keys: "
    "headline (string), rewritten_summary (string), rewritten_bullets (array of strings), "
    "ats_keywords_to_add (array of strings), cautions (array of strings). "
    "Do not invent fake experience. Only improve wording based on the provided CV."
)


class AIServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _normalise_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _get_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

    if not api_key:
        raise AIServiceError("OPENAI_API_KEY is missing.", status_code=500)

    return OpenAI(api_key=api_key, timeout=90), model


def _extract_openai_message(exc: Exception) -> str:
    message = str(exc)

    try:
        response = getattr(exc, "response", None)
        if response is not None:
            body = response.json()
            error = body.get("error", {})
            if isinstance(error, dict):
                return error.get("message") or message
    except Exception:
        pass

    return message


def _chat_json_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_retries: int = 2,
) -> dict:
    client, model = _get_client()

    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )

            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)

        except RateLimitError as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(2 + attempt * 3)
                continue

            message = _extract_openai_message(exc)
            raise AIServiceError(
                f"OpenAI rate limit or quota exceeded: {message}",
                status_code=429,
            ) from exc

        except (APITimeoutError, APIConnectionError) as exc:
            last_error = exc
            if attempt < max_retries:
                time.sleep(2 + attempt * 2)
                continue

            raise AIServiceError(
                "OpenAI connection timeout. Please try again.",
                status_code=503,
            ) from exc

        except APIStatusError as exc:
            message = _extract_openai_message(exc)
            status_code = getattr(exc, "status_code", 500) or 500

            if status_code == 429:
                raise AIServiceError(
                    f"OpenAI rate limit or quota exceeded: {message}",
                    status_code=429,
                ) from exc

            raise AIServiceError(
                f"OpenAI API error: {message}",
                status_code=status_code,
            ) from exc

        except APIError as exc:
            message = _extract_openai_message(exc)
            raise AIServiceError(
                f"OpenAI API error: {message}",
                status_code=502,
            ) from exc

        except json.JSONDecodeError as exc:
            raise AIServiceError(
                "OpenAI returned invalid JSON.",
                status_code=502,
            ) from exc

        except Exception as exc:
            last_error = exc
            raise AIServiceError(
                f"AI analysis failed: {exc}",
                status_code=500,
            ) from exc

    raise AIServiceError(
        f"AI analysis failed: {last_error}",
        status_code=500,
    )


def analyze_cv_with_ai(cv_text: str, job_description: str) -> dict:
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
        temperature=0.2,
    )

    score = max(0, min(100, int(data.get("score", 0))))
    summary = str(data.get("summary", "")).strip() or "Model did not return a summary."

    return {
        "score": score,
        "summary": summary,
        "strengths": _normalise_list(data.get("strengths")),
        "weaknesses": _normalise_list(data.get("weaknesses")),
        "recommendations": _normalise_list(data.get("recommendations")),
    }


def rewrite_cv_with_ai(cv_text: str, job_description: str) -> dict:
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
        temperature=0.3,
    )

    return {
        "headline": str(data.get("headline", "")).strip(),
        "rewritten_summary": str(data.get("rewritten_summary", "")).strip(),
        "rewritten_bullets": _normalise_list(data.get("rewritten_bullets")),
        "ats_keywords_to_add": _normalise_list(data.get("ats_keywords_to_add")),
        "cautions": _normalise_list(data.get("cautions")),
    }