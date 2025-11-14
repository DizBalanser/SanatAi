import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

SCHEMA_EXAMPLE = json.dumps(
    {
        "type": "task | idea | note",
        "task": {
            "title": "",
            "details": "",
            "deadline": "YYYY-MM-DD or null",
            "tags": [],
            "estimated_minutes": None,
        },
        "idea": {
            "title": "",
            "details": "",
            "tags": [],
        },
        "note": {
            "title": "",
            "content": "",
            "tags": [],
        },
    },
    indent=2,
)

def _get_system_prompt() -> str:
    """Generate system prompt with current date context."""
    today = datetime.now().strftime("%Y-%m-%d")
    return f"""You are an expert productivity assistant. Classify a single Telegram message as a task, idea, or note.

Today is {today}. Use this date when interpreting relative dates like "tomorrow", "Sunday", "next week".

Rules:
- TASK = user intends to do something (an action, plan, or deadline). Examples: "I need to buy a present by Sunday", "Call mom tomorrow", "Finish homework this evening".
- IDEA = concept, inspiration, project, or improvement that is not yet actionable.
- NOTE = information, observations, or reminders without action intent (meeting notes, text dumps, etc.).
- The classic message "I buy present by Sunday" must ALWAYS be classified as a TASK.
- Output STRICT JSON only (no markdown, prose, or code fences).
- The JSON MUST follow this exact schema and field names:
{SCHEMA_EXAMPLE}
- Fill only the object that matches `type`. The other two objects must be null.
- Use ISO format for deadlines (YYYY-MM-DD) or null when unknown.
- Always provide a concise title for tasks/ideas; default tags to [] when you have no tags.""".strip()


def classify_message(text: str) -> Dict[str, Any]:
    """
    Sends the message to OpenAI for classification and returns the structured JSON.
    Falls back to wrapping the text as a note only when JSON parsing fails.
    """
    clean_text = (text or "").strip()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")

    client = OpenAI(api_key=api_key)

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": _get_system_prompt()},
            {"role": "user", "content": clean_text},
        ],
    )

    payload_text = _extract_text(response)
    if not payload_text:
        raise ValueError("OpenAI returned an empty payload.")

    try:
        parsed = json.loads(payload_text)
    except json.JSONDecodeError:
        logger.warning("OpenAI returned invalid JSON; wrapping as note.")
        return _note_fallback(clean_text)

    return _normalize_payload(parsed)


def _extract_text(response: Any) -> Optional[str]:
    output = getattr(response, "output", None)
    if output:
        for block in output:
            for content in getattr(block, "content", []) or []:
                text_value = getattr(content, "text", None)
                if isinstance(text_value, str) and text_value.strip():
                    return text_value.strip()
                if isinstance(text_value, list):
                    combined = "".join(
                        piece for piece in text_value if isinstance(piece, str)
                    ).strip()
                    if combined:
                        return combined

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()
    if isinstance(output_text, list):
        combined = "".join(piece for piece in output_text if isinstance(piece, str)).strip()
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


def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    result_type = payload.get("type")
    if result_type not in {"task", "idea", "note"}:
        raise ValueError(f"Invalid classification type: {result_type}")

    task = payload.get("task")
    idea = payload.get("idea")
    note = payload.get("note")

    normalized = {
        "type": result_type,
        "task": _normalize_task(task) if result_type == "task" else None,
        "idea": _normalize_idea(idea) if result_type == "idea" else None,
        "note": _normalize_note(note) if result_type == "note" else None,
    }

    for key in ("task", "idea", "note"):
        if normalized[key] is not None:
            normalized[key]["tags"] = normalized[key].get("tags") or []

    return normalized


def _normalize_task(section: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    section = section or {}
    return {
        "title": section.get("title") or "",
        "details": section.get("details") or "",
        "deadline": section.get("deadline"),
        "tags": section.get("tags") or [],
        "estimated_minutes": section.get("estimated_minutes"),
    }


def _normalize_idea(section: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    section = section or {}
    return {
        "title": section.get("title") or "",
        "details": section.get("details") or "",
        "tags": section.get("tags") or [],
    }


def _normalize_note(section: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    section = section or {}
    return {
        "title": section.get("title"),
        "content": section.get("content") or "",
        "tags": section.get("tags") or [],
    }


def _note_fallback(text: str) -> Dict[str, Any]:
    return {
        "type": "note",
        "task": None,
        "idea": None,
        "note": {
            "title": None,
            "content": text,
            "tags": [],
        },
    }
