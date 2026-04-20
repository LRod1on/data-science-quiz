from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field


Topic = Literal["python", "classical_ml", "deep_learning", "nlp_cv"]


class SessionState(BaseModel):
    session_id: str
    topic: Topic | None = None
    question_index: int = 0
    current_question: str | None = None
    per_question_scores: list[float] = Field(default_factory=list)
    final_scores: dict[str, float] = Field(default_factory=dict)
    chat_history: list[dict[str, str]] = Field(default_factory=list)
    asked_questions: list[str] = Field(default_factory=list)
    history_checkpoint: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionState(session_id=session_id)
        return self._sessions[session_id].model_copy()

    def update(self, session_id: str, **fields: Any) -> SessionState:
        session = self.get_or_create(session_id)
        updated = session.model_copy(
            update={**fields, "last_activity_at": datetime.utcnow()}
        )
        self._sessions[session_id] = updated
        return updated

    def reset_topic(self, session_id: str) -> SessionState:
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
        cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        stale = [
            sid
            for sid, s in self._sessions.items()
            if s.last_activity_at < cutoff
        ]
        for sid in stale:
            del self._sessions[sid]
        return len(stale)


session_manager = SessionManager()
