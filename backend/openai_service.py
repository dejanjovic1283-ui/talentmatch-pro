import json
import os

from openai import OpenAI

# The system prompt forces a machine-readable JSON response.
SYSTEM_PROMPT = (
    "You are an expert recruitment analyst. "
    "Return ONLY valid JSON with these keys: "
    "score (integer 0-100), summary (string), strengths (array of strings), "
    "weaknesses (array of strings), recommendations (array of strings)."
)


def _normalise_list(value) -> list[str]:
    """Convert model output into a clean list of non-empty strings."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def analyze_cv_with_ai(cv_text: str, job_description: str) -> dict:
    """Send the CV and job description to OpenAI and return a structured result."""
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)

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
    strengths = _normalise_list(data.get("strengths"))
    weaknesses = _normalise_list(data.get("weaknesses"))
    recommendations = _normalise_list(data.get("recommendations"))

    return {
        "score": score,
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations,
    }
