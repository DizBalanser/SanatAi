import json
import logging
import os
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You analyze user tasks and assign importance and urgency.

Definitions:
- Importance = impact if completed
- Urgency = time sensitivity or deadline pressure

Return JSON ONLY:

{
  "importance": 1,
  "urgency": 1,
  "reason": "explain briefly the scores"
}
""".strip()

DEFAULT_RESPONSE = {"importance": 3, "urgency": 3, "reason": "ai_fallback"}


def analyze_task(task_title: str, details: str, deadline: Optional[str]) -> Dict[str, Any]:
    """
    Calls OpenAI and returns task scoring metadata.
    Retries once on JSON failure before falling back.
    """
    payload = {
        "title": task_title,
        "details": details,
        "deadline": deadline,
    }

    attempts = 0
    last_error: Optional[Exception] = None

    while attempts < 2:
        attempts += 1
        try:
            response = _call_openai(payload)
            parsed = json.loads(response)
            return _normalize(parsed)
        except Exception as exc:
            last_error = exc
            logger.warning("Task analysis attempt %s failed: %s", attempts, exc)

    logger.error("Task analysis failed after retries: %s", last_error)
    return DEFAULT_RESPONSE.copy()


def _call_openai(payload: Dict[str, Any]) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model="gpt-4.1",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    )

    text = _extract_text(response)
    if not text:
        raise ValueError("OpenAI returned empty analysis payload.")
    return text


def _extract_text(response: Any) -> Optional[str]:
    output = getattr(response, "output", None)
    if output:
        for block in output:
            for content in getattr(block, "content", []) or []:
                text_value = getattr(content, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    return text_value.strip()
                if isinstance(text_value, list):
                    combined = "".join(part for part in text_value if isinstance(part, str)).strip()
                    if combined:
                        return combined

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    if isinstance(output_text, list):
        combined = "".join(part for part in output_text if isinstance(part, str)).strip()
        if combined:
            return combined

    serializer = getattr(response, "model_dump", None)
    if callable(serializer):
        data = serializer()
    else:
        json_serializer = getattr(response, "json", None)
        data = json.loads(json_serializer()) if callable(json_serializer) else None

    if isinstance(data, dict):
        for block in data.get("output", []):
            for content in block.get("content", []):
                text_value = content.get("text")
                if isinstance(text_value, str) and text_value.strip():
                    return text_value.strip()

    return None


def _normalize(payload: Dict[str, Any]) -> Dict[str, Any]:
    importance = _clamp_score(payload.get("importance"))
    urgency = _clamp_score(payload.get("urgency"))
    reason = payload.get("reason") or "No reason provided."
    return {"importance": importance, "urgency": urgency, "reason": reason}


def _clamp_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 3
    return max(1, min(score, 5))
