"""Small, defensive wrapper around the configured Groq chat model."""
import json
import logging
from typing import Any, Optional

try:
    from groq import Groq
except ImportError:  # Allows deterministic tests/fallback mode before dependencies are installed.
    Groq = None

from app.config import GROQ_API_KEY, GROQ_ENABLED, GROQ_MODEL

logger = logging.getLogger(__name__)
_client = None


def get_client():
    global _client
    if Groq is None or not GROQ_ENABLED or not GROQ_API_KEY:
        return None
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY, timeout=20.0, max_retries=1)
    return _client


def _json_from_text(text: str) -> dict[str, Any]:
    """Parse a JSON object, tolerating a surrounding Markdown fence."""
    text = (text or "").strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass

    # Decode from the first object opener; unlike a greedy regex this handles nested objects.
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char == "{":
            try:
                value, _ = decoder.raw_decode(text[index:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue
    raise ValueError("LLM did not return a JSON object")


def groq_json(system_prompt: str, user_prompt: str) -> Optional[dict[str, Any]]:
    """Return structured model output, or None when disabled/unavailable.

    Failure is intentionally non-fatal: deterministic business logic remains available.
    The exception is logged without logging prompts, patient text, or API credentials.
    """
    client = get_client()
    if client is None:
        return None
    try:
        result = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=1400,
            response_format={"type": "json_object"},
        )
        content = result.choices[0].message.content or "{}"
        return _json_from_text(content)
    except Exception as exc:  # Provider SDKs expose several version-specific exception types.
        logger.warning("LLM request failed (%s); using safe fallback.", type(exc).__name__)
        return None
