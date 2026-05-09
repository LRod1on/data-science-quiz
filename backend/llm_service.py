"""Слой работы с LLM: выбор вопросов и оценка ответов через GigaChat.

Здесь же живёт токен-кеш и парсер ответа модели — у GigaChat нет structured
output, поэтому JSON приходит текстом и его приходится извлекать вручную.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
import uuid
import warnings

import httpx
from pydantic import BaseModel, ValidationError

from questions import QUESTIONS

logger = logging.getLogger(__name__)

# GigaChat использует российский CA, которого нет в дефолтном bundle Python.
# Отключаем проверку SSL и одновременно глушим предупреждение httpx —
# иначе на каждый запрос к GigaChat в логах будет шум.
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

_AUTH_KEY = os.getenv("GIGACHAT_AUTH_KEY", "")
if not _AUTH_KEY:
    logger.warning("GIGACHAT_AUTH_KEY не задан")

MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat")

_TOKEN_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
_CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"

# Кеш access-токена: модульная переменная, обновляется по истечении срока.
# Lock — потому что несколько корутин могут параллельно дёрнуть refresh.
_access_token: str = ""
_token_expires_at: float = 0.0
_token_lock = asyncio.Lock()


async def _get_access_token() -> str:
    """Вернуть валидный access-токен GigaChat, обновив его при необходимости."""
    global _access_token, _token_expires_at
    async with _token_lock:
        # Запас 60 секунд — чтобы не словить просрочку прямо во время запроса.
        if _access_token and time.time() < _token_expires_at - 60:
            return _access_token

        async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "RqUID": str(uuid.uuid4()),
                    "Authorization": f"Basic {_AUTH_KEY}",
                },
                data={"scope": "GIGACHAT_API_PERS"},
            )
            resp.raise_for_status()
            data = resp.json()

        _access_token = data["access_token"]
        _token_expires_at = data["expires_at"] / 1000  # API отдаёт миллисекунды
        logger.debug("Токен GigaChat обновлён, действителен ~30 минут")
        return _access_token


_SYSTEM_PROMPT = """\
Ты Senior Data Scientist, проводишь техническое интервью по теме {topic}.
Вопросы уровня senior. Оценивай ответы по шкале 0-10, где 10 — идеальный senior-ответ.
Если ответ неполный — задай один уточняющий вопрос (is_question_complete=false, score=null).
Если ответ исчерпывающий или кандидат сдался — поставь оценку и переходи к следующему (is_question_complete=true, score=ОБЯЗАТЕЛЬНОЕ число 0-10, НЕ null).
Уже заданные вопросы (не повторяй): {asked}.
Отвечай СТРОГО валидным JSON без markdown-ограждений.

Правило: если is_question_complete=true, то score ВСЕГДА должен быть числом 0-10, никогда не null.

Формат ответа — только этот JSON, без пояснений:
{{"score": <число 0-10 если вопрос завершён, null если задаёшь уточняющий вопрос>, \
"feedback": "<фидбек на русском, 2-3 предложения>", \
"is_question_complete": <true|false>, \
"next_question": "<следующий вопрос или null>", \
"clarifying_question": "<уточняющий вопрос или null>"}}"""

_RETRY_PROMPT = (
    "Верни ТОЛЬКО валидный JSON без markdown и без пояснений. Ничего кроме JSON-объекта."
)

_SCORE_FROM_HISTORY_PROMPT = """\
Ты оцениваешь ответ кандидата на техническое интервью по теме {topic}.
Вопрос: {question}

Оцени знания кандидата на основании диалога выше по шкале 0-10, где 10 — идеальный senior-ответ.
Если кандидат не дал содержательного ответа или сдался — ставь низкую оценку.
Верни ТОЛЬКО число от 0 до 10 (можно дробное, например 6.5). Без пояснений, без текста."""


class EvaluationResult(BaseModel):
    """Результат оценки одного хода в диалоге.

    Если is_question_complete=False — LLM хочет уточнения, score=null,
    clarifying_question содержит сам уточняющий вопрос. Иначе — вопрос засчитан,
    score обязан быть числом 0..10, а next_question может быть None (тогда
    следующий вопрос берётся из локального банка).
    """

    score: float | None
    feedback: str
    is_question_complete: bool
    next_question: str | None = None
    clarifying_question: str | None = None


class StartResult(BaseModel):
    """Первый вопрос темы и его озвучиваемая форма."""

    first_question: str
    pronounce_text: str


# Возвращается, если LLM сломалась настолько, что даже после ретрая JSON не парсится.
# Просим повторить ответ — для пользователя это выглядит как обычное уточнение.
_FALLBACK = EvaluationResult(
    score=None,
    feedback="Извини, я не расслышал, повтори ответ.",
    is_question_complete=False,
    next_question=None,
    clarifying_question="Можешь переформулировать?",
)


def _parse_llm_json(raw: str) -> dict | None:
    """Распарсить JSON из ответа LLM.

    Сначала пробуем как есть, потом достаём первую JSON-фигуру regex'ом —
    это покрывает случаи markdown-обрамления и сопутствующего текста,
    которые модель иногда подмешивает несмотря на инструкции в промпте.
    """
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass

    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except (json.JSONDecodeError, ValueError):
            pass

    return None


async def _call_llm(messages: list[dict]) -> str:
    """Вызвать GigaChat с одним ретраем на 429 (rate limit)."""
    for attempt in range(2):
        token = await _get_access_token()
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                resp = await client.post(
                    _CHAT_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "temperature": 0.3,
                    },
                )
                if resp.status_code == 429:
                    if attempt == 0:
                        logger.warning("GigaChat вернул 429, повторяем через 2 секунды")
                        await asyncio.sleep(2)
                        continue
                    resp.raise_for_status()
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"] or ""
        except httpx.HTTPStatusError:
            raise
    return ""


async def start_interview(topic: str, asked_questions: list[str]) -> StartResult:
    """Выбрать случайный вопрос из банка, исключив уже заданные.

    Если все 15 вопросов уже задавали в рамках сессии — берём из полного банка
    с повтором (чтобы /skip продолжал работать), но логируем warning.
    """
    pool = [q for q in QUESTIONS[topic] if q not in asked_questions]
    if not pool:
        logger.warning(
            "Банк вопросов по теме '%s' исчерпан (%d задано), переиспользуем полный список",
            topic,
            len(asked_questions),
        )
        pool = QUESTIONS[topic]
    question = random.choice(pool)
    return StartResult(first_question=question, pronounce_text=f"Вопрос: {question}")


async def evaluate_answer(
    topic: str,
    question: str,
    user_answer: str,
    history: list[dict[str, str]],
    asked_questions: list[str],
) -> EvaluationResult:
    """Оценить ответ пользователя через GigaChat.

    Если первый ответ модели не парсится — делаем один ретрай с напоминанием
    про чистый JSON. Если и после этого мусор — возвращаем _FALLBACK, чтобы
    интервью не падало, а просто попросило повторить ответ.
    """
    asked_str = ", ".join(asked_questions) if asked_questions else "нет"
    system = _SYSTEM_PROMPT.format(topic=topic, asked=asked_str)

    messages: list[dict] = [
        {"role": "system", "content": system},
        *history,
        {"role": "user", "content": user_answer},
    ]

    raw = await _call_llm(messages)
    parsed = _parse_llm_json(raw)

    if parsed is None:
        retry_messages = [
            *messages,
            {"role": "assistant", "content": raw},
            {"role": "user", "content": _RETRY_PROMPT},
        ]
        try:
            raw2 = await _call_llm(retry_messages)
            parsed = _parse_llm_json(raw2)
        except Exception as exc:
            logger.warning("Ретрай LLM-вызова упал: %s", exc)

    if parsed is None:
        logger.warning("JSON не распарсился даже после ретрая, отдаём fallback")
        return _FALLBACK

    try:
        return EvaluationResult.model_validate(parsed)
    except ValidationError as exc:
        logger.warning("EvaluationResult не прошёл валидацию: %s", exc)
        return _FALLBACK


async def score_from_history(
    topic: str,
    question: str,
    history: list[dict[str, str]],
) -> float:
    """Оценить вопрос по тому, что кандидат успел сказать в его рамках.

    Используется в /skip и /finish — там нужно поставить балл за частичный ответ
    (или 0, если кандидат вообще ничего не сказал). Не пробрасывает исключения:
    при любых проблемах с LLM возвращаем 0, чтобы пропуск/завершение прошли.
    """
    if not any(m["role"] == "user" for m in history):
        return 0.0

    system = _SCORE_FROM_HISTORY_PROMPT.format(topic=topic, question=question)
    messages: list[dict] = [
        {"role": "system", "content": system},
        *history,
    ]

    try:
        raw = await _call_llm(messages)
    except Exception as exc:
        logger.warning("Не удалось получить оценку из истории через LLM: %s", exc)
        return 0.0

    m = re.search(r"\d+(?:[.,]\d+)?", raw)
    if not m:
        logger.warning("score_from_history: не нашёл число в ответе %r", raw[:100])
        return 0.0

    try:
        score = float(m.group().replace(",", "."))
        return max(0.0, min(10.0, score))
    except ValueError:
        return 0.0
