"""Тесты SessionManager: идемпотентность get_or_create, финализация темы и очистка."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from session_manager import SessionManager


@pytest.fixture()
def manager() -> SessionManager:
    return SessionManager()


def test_get_or_create_returns_same_session(manager: SessionManager) -> None:
    first = manager.get_or_create("abc")
    second = manager.get_or_create("abc")
    assert first.session_id == second.session_id == "abc"
    # get_or_create отдаёт копии — объекты разные, данные одинаковые.
    assert first is not second
    assert manager._sessions["abc"].session_id == "abc"


def test_get_or_create_new_session_has_defaults(manager: SessionManager) -> None:
    s = manager.get_or_create("xyz")
    assert s.topic is None
    assert s.question_index == 0
    assert s.per_question_scores == []
    assert s.final_scores == {}
    assert s.chat_history == []


def test_finalize_topic_computes_average(manager: SessionManager) -> None:
    manager.get_or_create("s1")
    manager.update("s1", topic="python", per_question_scores=[8.0, 6.0, 9.0, 7.0, 5.0])

    result = manager.finalize_topic("s1")

    assert "python" in result.final_scores
    assert result.final_scores["python"] == pytest.approx(7.0)
    assert result.per_question_scores == []
    assert result.question_index == 0
    assert result.current_question is None


def test_finalize_topic_accumulates_multiple_topics(manager: SessionManager) -> None:
    """Один session_id должен копить final_scores при последовательном проходе тем."""
    manager.get_or_create("s2")
    manager.update("s2", topic="python", per_question_scores=[10.0, 10.0])
    manager.finalize_topic("s2")

    manager.update("s2", topic="classical_ml", per_question_scores=[4.0, 6.0])
    result = manager.finalize_topic("s2")

    assert result.final_scores["python"] == pytest.approx(10.0)
    assert result.final_scores["classical_ml"] == pytest.approx(5.0)


def test_finalize_topic_no_scores_preserves_final_scores(manager: SessionManager) -> None:
    """Финализация без баллов (никто ничего не ответил) не должна затирать final_scores."""
    manager.get_or_create("s3")
    manager.update("s3", topic="python", per_question_scores=[])
    result = manager.finalize_topic("s3")
    assert result.final_scores == {}


def test_cleanup_stale_removes_old_session(
    manager: SessionManager, monkeypatch: pytest.MonkeyPatch
) -> None:
    manager.get_or_create("old")
    manager.get_or_create("fresh")

    # Руками искусственно состариваем сессию — обычно last_activity_at двигается через update().
    old_time = datetime.utcnow() - timedelta(minutes=90)
    manager._sessions["old"] = manager._sessions["old"].model_copy(
        update={"last_activity_at": old_time}
    )

    removed = manager.cleanup_stale(max_age_minutes=60)

    assert removed == 1
    assert "old" not in manager._sessions
    assert "fresh" in manager._sessions


def test_cleanup_stale_keeps_all_fresh(manager: SessionManager) -> None:
    manager.get_or_create("a")
    manager.get_or_create("b")

    removed = manager.cleanup_stale(max_age_minutes=60)

    assert removed == 0
    assert "a" in manager._sessions
    assert "b" in manager._sessions


def test_cleanup_stale_empty_store(manager: SessionManager) -> None:
    assert manager.cleanup_stale() == 0
