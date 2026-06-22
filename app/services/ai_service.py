"""AI insight generation via OpenRouter, with strict-JSON parsing and fallback.

Design goals (per the assessment):
- prompt handling      -> a system prompt that pins the exact JSON contract
- response parsing     -> parse + validate against the `InsightData` schema
- error handling       -> timeouts / non-200 / bad JSON are caught; one retry
- fallback behaviour   -> a deterministic heuristic insight so the app never breaks
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.models.enums import InsightStatus, Sentiment
from app.schemas.insight import InsightData

logger = logging.getLogger("ai_service")

SYSTEM_PROMPT = (
    "You are a customer-success analyst. Read the meeting/interaction notes and "
    "return ONLY a JSON object with exactly these keys:\n"
    '  "summary": a 1-3 sentence summary (string)\n'
    '  "sentiment": one of "positive", "neutral", "negative"\n'
    '  "action_items": array of short follow-up strings (may be empty)\n'
    '  "risks": array of short risk/blocker strings (may be empty)\n'
    "Do not include any text outside the JSON object."
)

_POSITIVE = {"great", "happy", "excited", "love", "satisfied", "renew", "win", "smooth", "thrilled"}
_NEGATIVE = {"angry", "unhappy", "frustrated", "churn", "cancel", "issue", "bug", "delay", "risk", "concern", "blocker"}


@dataclass
class InsightResult:
    data: InsightData
    status: InsightStatus
    model: str
    raw: dict | None


def _heuristic_fallback(notes: str) -> InsightResult:
    """Keyword-based insight used when no API key is set or the LLM call fails."""
    text = (notes or "").lower()
    pos = sum(w in text for w in _POSITIVE)
    neg = sum(w in text for w in _NEGATIVE)
    sentiment = (
        Sentiment.positive if pos > neg else Sentiment.negative if neg > pos else Sentiment.neutral
    )
    summary = (notes or "").strip()
    summary = (summary[:200] + "…") if len(summary) > 200 else (summary or "No notes provided.")
    return InsightResult(
        data=InsightData(summary=summary, sentiment=sentiment, action_items=[], risks=[]),
        status=InsightStatus.fallback,
        model="heuristic-fallback",
        raw=None,
    )


async def _call_llm(notes: str) -> dict:
    """Single chat/completions call to the configured OpenAI-compatible provider.

    Works with OpenRouter, Google Gemini (OpenAI-compatible endpoint), or OpenAI.
    Raises on any HTTP/transport error.
    """
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Notes:\n{notes}"},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{settings.ai_base_url}/chat/completions", headers=headers, json=payload
        )
        resp.raise_for_status()
        return resp.json()


async def generate_insights(notes: str) -> InsightResult:
    """Generate structured insights. Always returns a result — never raises."""
    if not notes or not notes.strip():
        return InsightResult(
            data=InsightData(summary="No notes provided.", sentiment=Sentiment.neutral),
            status=InsightStatus.fallback,
            model="none",
            raw=None,
        )

    if not settings.ai_api_key:
        logger.info("No AI_API_KEY set; using heuristic fallback.")
        return _heuristic_fallback(notes)

    last_error: Exception | None = None
    for attempt in range(2):  # one retry
        try:
            raw = await _call_llm(notes)
            content = raw["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            data = InsightData.model_validate(parsed)
            return InsightResult(
                data=data, status=InsightStatus.success, model=settings.ai_model, raw=raw
            )
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError) as exc:
            last_error = exc
            logger.warning("AI generation attempt %d failed: %s", attempt + 1, exc)

    logger.error("AI generation failed after retries (%s); using fallback.", last_error)
    return _heuristic_fallback(notes)
