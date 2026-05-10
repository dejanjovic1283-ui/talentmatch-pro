import json
import os

from openai import OpenAI

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


def _normalise_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def _get_client() -> tuple[OpenAI, str]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    return OpenAI(api_key=api_key), model


def analyze_cv_with_ai(cv_text: str, job_description: str) -> dict:
    client, model = _get_client()

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

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)

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
    client, model = _get_client()

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

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        temperature=0.3,
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    raw = response.choices[0].message.content or "{}"
    data = json.loads(raw)

    return {
        "headline": str(data.get("headline", "")).strip(),
        "rewritten_summary": str(data.get("rewritten_summary", "")).strip(),
        "rewritten_bullets": _normalise_list(data.get("rewritten_bullets")),
        "ats_keywords_to_add": _normalise_list(data.get("ats_keywords_to_add")),
        "cautions": _normalise_list(data.get("cautions")),
    }