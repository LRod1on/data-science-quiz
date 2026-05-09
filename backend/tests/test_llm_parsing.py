"""Тесты парсинга JSON-ответов LLM и общей логики evaluate_answer.

Сетевой слой замокан через _call_llm — здесь проверяется только то,
что мы корректно вытаскиваем JSON и валидируем его в EvaluationResult.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from llm_service import (
    _FALLBACK,
    EvaluationResult,
    _parse_llm_json,
    evaluate_answer,
)


def test_parse_valid_json():
    raw = '{"score": 8.0, "feedback": "Good", "is_question_complete": true, "next_question": "Q2", "clarifying_question": null}'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["score"] == 8.0
    assert result["is_question_complete"] is True


def test_parse_json_wrapped_in_markdown():
    raw = '```json\n{"score": 7, "feedback": "Ok", "is_question_complete": false, "next_question": null, "clarifying_question": "Can you elaborate?"}\n```'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["score"] == 7
    assert result["clarifying_question"] == "Can you elaborate?"


def test_parse_json_with_extra_text_before():
    raw = 'Sure, here is my evaluation:\n{"score": 5.0, "feedback": "Partial", "is_question_complete": false, "next_question": null, "clarifying_question": "What about X?"}'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["score"] == 5.0


def test_parse_json_with_extra_text_after():
    raw = '{"score": 9, "feedback": "Excellent", "is_question_complete": true, "next_question": "Next Q", "clarifying_question": null}\nHope that helps!'
    result = _parse_llm_json(raw)
    assert result is not None
    assert result["score"] == 9


def test_parse_pure_garbage_returns_none():
    result = _parse_llm_json("This is not JSON at all, sorry!")
    assert result is None


def test_parse_empty_string_returns_none():
    result = _parse_llm_json("")
    assert result is None


def test_parse_partial_json_returns_none():
    result = _parse_llm_json('{"score": 8, "feedback":')
    assert result is None


VALID_RESPONSE = json.dumps(
    {
        "score": 8.5,
        "feedback": "Хороший ответ, но не упомянул GIL.",
        "is_question_complete": True,
        "next_question": "Как работает __slots__?",
        "clarifying_question": None,
    }
)

MARKDOWN_RESPONSE = f"```json\n{VALID_RESPONSE}\n```"

CLARIFY_RESPONSE = json.dumps(
    {
        "score": None,
        "feedback": "Ответ неполный.",
        "is_question_complete": False,
        "next_question": None,
        "clarifying_question": "Можешь описать поподробнее?",
    }
)


@pytest.fixture()
def base_args():
    return dict(
        topic="python",
        question="Объясни GIL.",
        user_answer="GIL это мьютекс.",
        history=[{"role": "assistant", "content": "Объясни GIL."}],
        asked_questions=["Объясни GIL."],
    )


@pytest.mark.asyncio
async def test_evaluate_valid_json(base_args):
    with patch("llm_service._call_llm", new=AsyncMock(return_value=VALID_RESPONSE)):
        result = await evaluate_answer(**base_args)
    assert isinstance(result, EvaluationResult)
    assert result.score == pytest.approx(8.5)
    assert result.is_question_complete is True
    assert result.next_question == "Как работает __slots__?"


@pytest.mark.asyncio
async def test_evaluate_markdown_wrapped_json(base_args):
    with patch("llm_service._call_llm", new=AsyncMock(return_value=MARKDOWN_RESPONSE)):
        result = await evaluate_answer(**base_args)
    assert result.score == pytest.approx(8.5)
    assert result.is_question_complete is True


@pytest.mark.asyncio
async def test_evaluate_clarification_response(base_args):
    with patch("llm_service._call_llm", new=AsyncMock(return_value=CLARIFY_RESPONSE)):
        result = await evaluate_answer(**base_args)
    assert result.score is None
    assert result.is_question_complete is False
    assert result.clarifying_question == "Можешь описать поподробнее?"


@pytest.mark.asyncio
async def test_evaluate_garbage_first_retry_valid(base_args):
    """Первый вызов возвращает мусор, ретрай — валидный JSON; результат — из ретрая."""
    call_results = iter(["not json at all", VALID_RESPONSE])
    with patch("llm_service._call_llm", new=AsyncMock(side_effect=call_results)):
        result = await evaluate_answer(**base_args)
    assert result.score == pytest.approx(8.5)


@pytest.mark.asyncio
async def test_evaluate_garbage_both_calls_returns_fallback(base_args):
    """И первый вызов, и ретрай — мусор: возвращаем _FALLBACK, не падаем."""
    with patch("llm_service._call_llm", new=AsyncMock(return_value="not json")):
        result = await evaluate_answer(**base_args)
    assert result.score is None
    assert result.is_question_complete is False
    assert result.feedback == _FALLBACK.feedback


@pytest.mark.asyncio
async def test_evaluate_llm_exception_propagates(base_args):
    """Сетевые ошибки LLM пробрасываются — /evaluate сам поймает их и вернёт action=ERROR."""
    exc = RuntimeError("simulated LLM connection error")
    with (
        patch("llm_service._call_llm", new=AsyncMock(side_effect=[exc, exc])),
        pytest.raises(RuntimeError),
    ):
        await evaluate_answer(**base_args)
