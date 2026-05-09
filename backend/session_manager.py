"""In-memory хранилище сессий интервью.

Сессии живут в памяти процесса. После перезапуска uvicorn всё стирается —
для учебного проекта это ок. На несколько недель прод-нагрузки сюда понадобится
вытеснение по TTL (см. cleanup_stale) или внешнее хранилище.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

Topic = Literal["python", "classical_ml", "deep_learning", "nlp_cv"]


class SessionState(BaseModel):
    """Состояние одной сессии интервью.

    Один session_id переиспользуется между темами в рамках одной поездки
    пользователя — поэтому final_scores накапливаются, а остальные поля
    сбрасываются при старте каждой темы (см. /start и finalize_topic).
    """

    session_id: str
    topic: Topic | None = None
    question_index: int = 0
    current_question: str | None = None
    per_question_scores: list[float] = Field(default_factory=list)
    final_scores: dict[str, float] = Field(default_factory=dict)
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    asked_questions: list[str] = Field(default_factory=list)
    # Индекс в chat_history, начиная с которого считается контекст текущего вопроса.
    # При переходе на следующий вопрос двигается вперёд, чтобы LLM не видела
    # историю предыдущих вопросов и не теряла фокус.
    history_checkpoint: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)


class SessionManager:
    """Простой in-memory словарь session_id → SessionState с парой удобных операций."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        """Вернуть копию состояния сессии, создав пустую при необходимости.

        Возвращается копия, а не сам объект из словаря — чтобы вызывающий код
        случайно не мутировал внутреннее состояние в обход update().
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id].model_copy()

    def update(self, session_id: str, **fields: Any) -> SessionState:
        """Обновить указанные поля сессии и вернуть новое состояние."""
        session = self.get_or_create(session_id)
        updated = session.model_copy(update={**fields, "last_activity_at": datetime.utcnow()})
        self._sessions[session_id] = updated
        return updated

    def reset_topic(self, session_id: str) -> SessionState:
        """Сбросить всё, кроме final_scores — готовим сессию к новой теме."""
        return self.update(
            session_id,
            topic=None,
            question_index=0,
            current_question=None,
            per_question_scores=[],
            chat_history=[],
            asked_questions=[],
            history_checkpoint=0,
        )

    def finalize_topic(self, session_id: str) -> SessionState:
        """Завершить тему: записать средний балл в final_scores и почистить контекст темы.

        Если за тему не было ни одного балла (например, все вопросы пропустили без
        ответа) — final_scores не меняется. Усреднение делается по тому, что
        фактически записано в per_question_scores (для интервью это всегда 5 значений).
        """
        session = self.get_or_create(session_id)
        if session.topic and session.per_question_scores:
            avg = sum(session.per_question_scores) / len(session.per_question_scores)
            new_final = {**session.final_scores, session.topic: round(avg, 2)}
        else:
            new_final = session.final_scores

        return self.update(
            session_id,
            final_scores=new_final,
            per_question_scores=[],
            question_index=0,
            current_question=None,
            chat_history=[],
            asked_questions=[],
            history_checkpoint=0,
        )

    def cleanup_stale(self, max_age_minutes: int = 60) -> int:
        """Удалить сессии без активности дольше max_age_minutes. Возвращает их количество."""
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        stale = [sid for sid, s in self._sessions.items() if s.last_activity_at < cutoff]
        for sid in stale:
            del self._sessions[sid]
        return len(stale)


session_manager = SessionManager()
