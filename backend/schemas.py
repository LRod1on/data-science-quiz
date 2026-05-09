"""Pydantic-схемы запросов и ответов FastAPI.

Зачем: типизация тел даёт автоматическую валидацию (422 на кривое тело)
и одновременно — рабочую интерактивную доку на /docs без отдельного описания.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

Topic = Literal["python", "classical_ml", "deep_learning", "nlp_cv"]
Action = Literal["CONTINUE", "NEXT_QUESTION", "TOPIC_COMPLETE", "ERROR"]


class StartRequest(BaseModel):
    session_id: str
    topic: Topic


class StartResponse(BaseModel):
    question: str
    pronounce_text: str


class EvaluateRequest(BaseModel):
    session_id: str
    text: str


class FinishRequest(BaseModel):
    session_id: str


class SkipRequest(BaseModel):
    session_id: str


class EvaluateResponse(BaseModel):
    """Универсальная форма ответа /evaluate, /skip, /finish.

    next_question заполнен только при action=NEXT_QUESTION.
    final_scores заполнен только при action=TOPIC_COMPLETE
    (значения внутри: float — пройдено, None — все вопросы пропустили,
    0 — тема в этой сессии не открывалась).
    """

    action: Action
    feedback: str
    next_question: str | None = None
    question_index: int
    final_scores: dict[str, float | None] | None = None
