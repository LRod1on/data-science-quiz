"""Тесты эндпоинтов /start, /evaluate, /skip через FastAPI TestClient.

llm_service замокан — здесь проверяется логика маршрутов и переходы состояния
сессии, а не само поведение LLM (для него есть test_llm_parsing.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from llm_service import EvaluationResult, StartResult
from session_manager import SessionManager

SESSION_ID = "test-session-abc"
TOPIC = "python"

START_RESULT = StartResult(
    first_question="What is the GIL?",
    pronounce_text="Вопрос: What is the GIL?",
)

EVAL_COMPLETE = EvaluationResult(
    score=8.0,
    feedback="Хороший ответ.",
    is_question_complete=True,
    next_question="Explain generators.",
    clarifying_question=None,
)

EVAL_CLARIFY = EvaluationResult(
    score=None,
    feedback="Неполный ответ.",
    is_question_complete=False,
    next_question=None,
    clarifying_question="Можешь добавить деталей?",
)


@pytest.fixture(autouse=True)
def fresh_session_manager():
    """Подменяет модульный session_manager свежим инстансом на каждый тест."""
    fresh = SessionManager()
    with patch("main.session_manager", fresh):
        yield fresh


@pytest.fixture()
def client():
    from main import app

    return TestClient(app)


def test_start_returns_question(client):
    with patch("main.start_interview", new=AsyncMock(return_value=START_RESULT)):
        resp = client.post("/start", json={"session_id": SESSION_ID, "topic": TOPIC})
    assert resp.status_code == 200
    data = resp.json()
    assert data["question"] == "What is the GIL?"
    assert "pronounce_text" in data


def test_start_sets_session_state(client, fresh_session_manager):
    with patch("main.start_interview", new=AsyncMock(return_value=START_RESULT)):
        client.post("/start", json={"session_id": SESSION_ID, "topic": TOPIC})
    session = fresh_session_manager.get_or_create(SESSION_ID)
    assert session.topic == TOPIC
    assert session.question_index == 1
    assert session.current_question == "What is the GIL?"
    assert session.asked_questions == ["What is the GIL?"]
    assert session.history_checkpoint == 0
    assert session.chat_history == [{"role": "assistant", "content": "What is the GIL?"}]


def test_start_resets_previous_topic_state(client, fresh_session_manager):
    # Заранее наполняем сессию состоянием от предыдущей темы.
    fresh_session_manager.update(
        SESSION_ID,
        topic="classical_ml",
        per_question_scores=[7.0, 8.0],
        question_index=2,
        asked_questions=["Old question"],
    )
    with patch("main.start_interview", new=AsyncMock(return_value=START_RESULT)):
        resp = client.post("/start", json={"session_id": SESSION_ID, "topic": TOPIC})
    assert resp.status_code == 200
    session = fresh_session_manager.get_or_create(SESSION_ID)
    assert session.topic == TOPIC
    assert session.per_question_scores == []
    assert session.asked_questions == ["What is the GIL?"]


def test_evaluate_continue(client, fresh_session_manager):
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=1,
        current_question="What is the GIL?",
        chat_history=[{"role": "assistant", "content": "What is the GIL?"}],
        history_checkpoint=0,
        asked_questions=["What is the GIL?"],
    )
    with patch("main.evaluate_answer", new=AsyncMock(return_value=EVAL_CLARIFY)):
        resp = client.post(
            "/evaluate", json={"session_id": SESSION_ID, "text": "I think it's a lock"}
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "CONTINUE"
    assert data["next_question"] is None
    assert data["final_scores"] is None

    # В историю должны добавиться ответ пользователя и уточнение от ассистента.
    session = fresh_session_manager.get_or_create(SESSION_ID)
    assert len(session.chat_history) == 3  # вопрос + ответ + уточнение
    assert session.chat_history[1] == {"role": "user", "content": "I think it's a lock"}
    assert session.chat_history[2]["role"] == "assistant"


def test_evaluate_continue_preserves_checkpoint(client, fresh_session_manager):
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=1,
        current_question="What is the GIL?",
        chat_history=[{"role": "assistant", "content": "What is the GIL?"}],
        history_checkpoint=0,
        asked_questions=["What is the GIL?"],
    )
    with patch("main.evaluate_answer", new=AsyncMock(return_value=EVAL_CLARIFY)):
        client.post("/evaluate", json={"session_id": SESSION_ID, "text": "partial answer"})
    session = fresh_session_manager.get_or_create(SESSION_ID)
    # На CONTINUE чекпоинт не должен двигаться — мы всё ещё на том же вопросе.
    assert session.history_checkpoint == 0


def test_evaluate_next_question(client, fresh_session_manager):
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=1,
        current_question="What is the GIL?",
        chat_history=[{"role": "assistant", "content": "What is the GIL?"}],
        history_checkpoint=0,
        asked_questions=["What is the GIL?"],
    )
    with patch("main.evaluate_answer", new=AsyncMock(return_value=EVAL_COMPLETE)):
        resp = client.post("/evaluate", json={"session_id": SESSION_ID, "text": "Full answer here"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "NEXT_QUESTION"
    assert data["next_question"] == "Explain generators."
    assert data["question_index"] == 2
    assert data["final_scores"] is None

    session = fresh_session_manager.get_or_create(SESSION_ID)
    assert session.question_index == 2
    assert session.per_question_scores == [8.0]
    assert session.current_question == "Explain generators."
    assert "Explain generators." in session.asked_questions
    # Чекпоинт должен сдвинуться за конец завершённого хода.
    assert session.history_checkpoint > 0
    # И в конце истории — следующий вопрос.
    assert session.chat_history[-1] == {"role": "assistant", "content": "Explain generators."}


def test_evaluate_topic_complete(client, fresh_session_manager):
    # На пятом вопросе уже накоплено четыре балла — пятый должен закрыть тему.
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=5,
        current_question="What is the GIL?",
        per_question_scores=[7.0, 8.0, 6.0, 9.0],
        chat_history=[{"role": "assistant", "content": "What is the GIL?"}],
        history_checkpoint=0,
        asked_questions=["What is the GIL?"],
    )
    with patch("main.evaluate_answer", new=AsyncMock(return_value=EVAL_COMPLETE)):
        resp = client.post("/evaluate", json={"session_id": SESSION_ID, "text": "Great answer"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "TOPIC_COMPLETE"
    assert data["final_scores"] is not None
    # На радар попадают все 4 темы.
    assert set(data["final_scores"].keys()) == {"python", "classical_ml", "deep_learning", "nlp_cv"}
    # У текущей темы — средний по пяти баллам.
    assert data["final_scores"]["python"] is not None
    # Остальные темы не пройдены → 0.
    assert data["final_scores"]["classical_ml"] == 0


def test_evaluate_llm_error_returns_error_action(client, fresh_session_manager):
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=1,
        current_question="What is the GIL?",
        chat_history=[{"role": "assistant", "content": "What is the GIL?"}],
        history_checkpoint=0,
        asked_questions=["What is the GIL?"],
    )
    with patch("main.evaluate_answer", new=AsyncMock(side_effect=RuntimeError("LLM down"))):
        resp = client.post("/evaluate", json={"session_id": SESSION_ID, "text": "My answer"})
    # Не 500 — сессия не сломана, пользователь может попробовать ещё раз.
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "ERROR"
    assert "feedback" in data

    # После ошибки состояние сессии не должно меняться.
    session = fresh_session_manager.get_or_create(SESSION_ID)
    assert session.question_index == 1
    assert session.per_question_scores == []


def test_evaluate_without_start_returns_400(client):
    resp = client.post("/evaluate", json={"session_id": "new-session", "text": "answer"})
    assert resp.status_code == 400


def test_skip_moves_to_next_question(client, fresh_session_manager):
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=1,
        current_question="What is the GIL?",
        per_question_scores=[],
        chat_history=[{"role": "assistant", "content": "What is the GIL?"}],
        history_checkpoint=0,
        asked_questions=["What is the GIL?"],
    )
    next_q_result = StartResult(
        first_question="Explain generators.",
        pronounce_text="Вопрос: Explain generators.",
    )
    with patch("main.start_interview", new=AsyncMock(return_value=next_q_result)):
        resp = client.post("/skip", json={"session_id": SESSION_ID})
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "NEXT_QUESTION"
    assert data["next_question"] == "Explain generators."
    assert data["question_index"] == 2
    assert data["final_scores"] is None


def test_skip_without_user_answer_records_zero(client, fresh_session_manager):
    """Пропуск вопроса без единого ответа пользователя → балл 0 (LLM не дёргается)."""
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=1,
        current_question="What is the GIL?",
        per_question_scores=[],
        chat_history=[{"role": "assistant", "content": "What is the GIL?"}],
        history_checkpoint=0,
        asked_questions=["What is the GIL?"],
    )
    next_q_result = StartResult(
        first_question="Explain generators.",
        pronounce_text="Вопрос: Explain generators.",
    )
    with patch("main.start_interview", new=AsyncMock(return_value=next_q_result)):
        client.post("/skip", json={"session_id": SESSION_ID})
    session = fresh_session_manager.get_or_create(SESSION_ID)
    assert session.per_question_scores == [0.0]


def test_skip_adds_skipped_and_new_question_to_asked(client, fresh_session_manager):
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=2,
        current_question="Q2",
        per_question_scores=[7.0],
        chat_history=[{"role": "assistant", "content": "Q2"}],
        history_checkpoint=0,
        asked_questions=["Q1", "Q2"],
    )
    next_q_result = StartResult(first_question="Q3", pronounce_text="Вопрос: Q3")
    with patch("main.start_interview", new=AsyncMock(return_value=next_q_result)):
        client.post("/skip", json={"session_id": SESSION_ID})
    session = fresh_session_manager.get_or_create(SESSION_ID)
    # И пропущенный, и новый вопросы должны попасть в asked_questions —
    # чтобы случайный выбор из банка их больше не возвращал.
    assert "Q2" in session.asked_questions
    assert "Q3" in session.asked_questions


def test_skip_updates_history_checkpoint(client, fresh_session_manager):
    existing_history = [
        {"role": "assistant", "content": "Q1"},
        {"role": "user", "content": "partial answer"},
        {"role": "assistant", "content": "clarify?"},
    ]
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=1,
        current_question="Q1",
        per_question_scores=[],
        chat_history=existing_history,
        history_checkpoint=0,
        asked_questions=["Q1"],
    )
    next_q_result = StartResult(first_question="Q2", pronounce_text="Вопрос: Q2")
    with patch("main.start_interview", new=AsyncMock(return_value=next_q_result)):
        client.post("/skip", json={"session_id": SESSION_ID})
    session = fresh_session_manager.get_or_create(SESSION_ID)
    # Чекпоинт должен встать на начало Q2 (индекс 3 = конец старой истории).
    assert session.history_checkpoint == 3
    assert session.chat_history[session.history_checkpoint] == {
        "role": "assistant",
        "content": "Q2",
    }


def test_skip_last_question_returns_topic_complete(client, fresh_session_manager):
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=5,
        current_question="Q5",
        per_question_scores=[7.0, 8.0, 9.0, 6.0],
        chat_history=[{"role": "assistant", "content": "Q5"}],
        history_checkpoint=0,
        asked_questions=["Q1", "Q2", "Q3", "Q4", "Q5"],
    )
    resp = client.post("/skip", json={"session_id": SESSION_ID})
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "TOPIC_COMPLETE"
    assert data["final_scores"] is not None
    assert set(data["final_scores"].keys()) == {"python", "classical_ml", "deep_learning", "nlp_cv"}


def test_skip_all_five_topic_score_is_zero(client, fresh_session_manager):
    """Если пропустили все 5 вопросов без ответа — итоговый балл темы 0 (среднее нулей)."""
    # Четыре уже пропущенных с нулём, пропускаем пятый.
    fresh_session_manager.update(
        SESSION_ID,
        topic=TOPIC,
        question_index=5,
        current_question="Q5",
        per_question_scores=[0.0, 0.0, 0.0, 0.0],
        chat_history=[{"role": "assistant", "content": "Q5"}],
        history_checkpoint=0,
        asked_questions=["Q1", "Q2", "Q3", "Q4", "Q5"],
    )
    resp = client.post("/skip", json={"session_id": SESSION_ID})
    data = resp.json()
    assert data["action"] == "TOPIC_COMPLETE"
    assert data["final_scores"]["python"] == 0.0
    assert data["final_scores"]["classical_ml"] == 0  # тема не пройдена → 0
