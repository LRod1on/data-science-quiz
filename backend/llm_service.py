"""LLM service: question selection and answer evaluation via OpenRouter."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re

from openai import AsyncOpenAI, RateLimitError
from pydantic import BaseModel, ValidationError

from questions import QUESTIONS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Client (module singleton, reused across requests)
# ---------------------------------------------------------------------------

_api_key = os.getenv("OPENROUTER_API_KEY", "")
if not _api_key:
    logger.warning("OPENROUTER_API_KEY is not set")

client = AsyncOpenAI(
    api_key=_api_key or "dummy",
    base_url="https://openrouter.ai/api/v1",
    timeout=30.0,
)
MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
Ты Senior Data Scientist, проводишь техническое интервью по теме {topic}.
Вопросы уровня senior. Оценивай ответы по шкале 0-10, где 10 — идеальный senior-ответ.
Если ответ неполный — задай один уточняющий вопрос.
Если ответ исчерпывающий или кандидат сдался — оцени и переходи к следующему.
Уже заданные вопросы (не повторяй): {asked}.
Отвечай СТРОГО валидным JSON без markdown-ограждений.

Формат ответа — только этот JSON, без пояснений:
{{"score": <число 0-10 или null>, "feedback": "<фидбек на русском, 2-3 предложения>", \
"is_question_complete": <true|false>, \
"next_question": "<следующий вопрос или null>", \
"clarifying_question": "<уточняющий вопрос или null>"}}"""

_RETRY_PROMPT = (
    "Верни ТОЛЬКО валидный JSON без markdown и без пояснений. "
    "Ничего кроме JSON-объекта."
)

# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class EvaluationResult(BaseModel):
    score: float | None
    feedback: str
    is_question_complete: bool
    next_question: str | None = None
    clarifying_question: str | None = None


class StartResult(BaseModel):
    first_question: str
    pronounce_text: str


_FALLBACK = EvaluationResult(
    score=None,
    feedback="Извини, я не расслышал, повтори ответ.",
    is_question_complete=False,
    next_question=None,
    clarifying_question="Можешь переформулировать?",
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_llm_json(raw: str) -> dict | None:
    """4-step JSON extraction from LLM output.

    1. Direct json.loads
    2. Regex-extract first {...} block (handles ```json ... ``` wrappers)
    3. Returns None — caller does one retry with a stricter prompt
    """
    # Step 1
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 2
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except (json.JSONDecodeError, ValueError):
            pass

    return None


async def _call_llm(messages: list[dict]) -> str:
    """Call OpenRouter with a single retry on RateLimitError.

    TODO(phase-5-hardening): if transient 429s are frequent, consider using
    OpenRouter's `models` parameter for automatic fallback to a secondary model
    (e.g. models=[PRIMARY, FALLBACK]). This handles provider outages without
    increasing latency on the happy path.
    """
    for attempt in range(2):
        try:
            resp = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.3,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError:
            if attempt == 0:
                logger.warning("RateLimitError, retrying after 2 s")
                await asyncio.sleep(2)
                continue
            raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def start_interview(topic: str, asked_questions: list[str]) -> StartResult:
    """Pick a random question from the bank, excluding already-asked questions."""
    pool = [q for q in QUESTIONS[topic] if q not in asked_questions]
    if not pool:
        logger.warning(
            "Question bank for topic '%s' exhausted (%d asked), reusing full bank",
            topic,
            len(asked_questions),
        )
        pool = QUESTIONS[topic]
    question = random.choice(pool)
    pronounce_text = f"Вопрос: {question}"
    return StartResult(first_question=question, pronounce_text=pronounce_text)


async def evaluate_answer(
    topic: str,
    question: str,
    user_answer: str,
    history: list[dict[str, str]],
    asked_questions: list[str],
) -> EvaluationResult:
    """Evaluate a user's answer.

    Args:
        history: chat_history[checkpoint:] — contains the current question as
                 the first {role:assistant} message, followed by any prior
                 clarification turns for this question.
        user_answer: the latest user message (not yet in history).

    Returns EvaluationResult. Raises on LLM communication errors (caller
    should catch and return action=ERROR).
    """
    asked_str = ", ".join(asked_questions) if asked_questions else "нет"
    system = _SYSTEM_PROMPT.format(topic=topic, asked=asked_str)

    messages: list[dict] = [
        {"role": "system", "content": system},
        *history,
        {"role": "user", "content": user_answer},
    ]

    # LLM call — may raise RateLimitError / TimeoutError / etc.
    raw = await _call_llm(messages)

    parsed = _parse_llm_json(raw)

    # Step 3: one retry with strict prompt
    if parsed is None:
        retry_messages = messages + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": _RETRY_PROMPT},
        ]
        try:
            raw2 = await _call_llm(retry_messages)
            parsed = _parse_llm_json(raw2)
        except Exception as exc:
            logger.warning("Retry LLM call failed: %s", exc)

    # Step 4: fallback
    if parsed is None:
        logger.warning("JSON parsing failed after retry, returning fallback")
        return _FALLBACK

    try:
        return EvaluationResult.model_validate(parsed)
    except ValidationError as exc:
        logger.warning("EvaluationResult validation failed: %s", exc)
        return _FALLBACK
