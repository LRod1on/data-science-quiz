"""FastAPI-приложение тренажёра интервью.

Здесь живут middleware (request-id, CORS, глобальный обработчик исключений),
эндпоинты /start, /evaluate, /skip, /finish и логика связки между сессиями
и LLM. Сами вызовы GigaChat и хранилище сессий вынесены в отдельные модули.
"""

import json
import logging
import os
import random
import time
import traceback
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# llm_service читает GIGACHAT_* на импорте — load_dotenv должен выполниться
# раньше следующих локальных импортов, поэтому E402 здесь подавлен намеренно.
load_dotenv(Path(__file__).resolve().parent / ".env")

from llm_service import (  # noqa: E402
    EvaluationResult,
    evaluate_answer,
    score_from_history,
    start_interview,
)
from logging_config import setup_logging  # noqa: E402
from questions import QUESTIONS  # noqa: E402
from schemas import (  # noqa: E402
    EvaluateRequest,
    EvaluateResponse,
    FinishRequest,
    SkipRequest,
    StartRequest,
    StartResponse,
)
from session_manager import SessionState, session_manager  # noqa: E402

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Старт приложения", extra={"request_id": "-"})
    yield
    logger.info("Остановка приложения", extra={"request_id": "-"})


app = FastAPI(title="Interview Trainer API", lifespan=lifespan)

_cors_origins: list[str] = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def attach_request_id(request: Request, call_next):
    """Каждый HTTP-запрос получает UUID — он виден во всех логах и в заголовке X-Request-Id."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info(
        "Входящий %s %s",
        request.method,
        request.url.path,
        extra={"request_id": request_id},
    )
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Перехватывает всё, что не поймали хендлеры, и отдаёт 500 с request_id для отладки."""
    request_id: str = getattr(request.state, "request_id", "-")
    logger.error(
        "Необработанное исключение: %s\n%s",
        exc,
        traceback.format_exc(),
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "request_id": request_id},
    )


_ALL_TOPICS = ["python", "classical_ml", "deep_learning", "nlp_cv"]


def _advance_or_finalize(
    session_id: str,
    session: SessionState,
    eval_result: EvaluationResult,
    new_history: list[dict[str, str]],
) -> tuple[str, str | None, dict[str, float | None] | None, int]:
    """Записать балл за текущий вопрос и продвинуть сессию вперёд.

    Возвращает (action, next_question, final_scores, new_question_index).
    Если завершён пятый вопрос — финализирует тему. Иначе берёт следующий
    вопрос (из ответа LLM или из локального банка) и сдвигает чекпоинт.
    """
    score = eval_result.score
    if score is None:
        logger.warning(
            "score=null при is_question_complete=true (session=%s, q=%d), пишем 0",
            session_id,
            session.question_index,
        )
        score = 0.0
    new_scores = [*session.per_question_scores, score]

    if session.question_index >= 5:
        # Пятый засчитанный вопрос — финализируем тему.
        session_manager.update(session_id, per_question_scores=new_scores, chat_history=new_history)
        final_session = session_manager.finalize_topic(session_id)
        return (
            "TOPIC_COMPLETE",
            None,
            _build_final_scores(final_session.final_scores, session.topic),
            5,
        )

    # Двигаемся на следующий вопрос. Если LLM не прислала свой —
    # берём из локального банка, чтобы интервью не зависло.
    next_question = eval_result.next_question
    if not next_question:
        pool = [q for q in QUESTIONS[session.topic] if q not in session.asked_questions]
        if not pool:
            pool = QUESTIONS[session.topic]
        next_question = random.choice(pool)

    new_asked = [*session.asked_questions, next_question]
    new_question_index = session.question_index + 1
    # Чекпоинт двигаем сразу за завершённый ход — следующий вопрос
    # будет оцениваться в чистом контексте.
    checkpoint = len(new_history)
    new_history_with_next = [*new_history, {"role": "assistant", "content": next_question}]
    session_manager.update(
        session_id,
        per_question_scores=new_scores,
        chat_history=new_history_with_next,
        history_checkpoint=checkpoint,
        current_question=next_question,
        question_index=new_question_index,
        asked_questions=new_asked,
    )
    return "NEXT_QUESTION", next_question, None, new_question_index


def _build_final_scores(
    final_scores: dict[str, float], current_topic: str | None
) -> dict[str, float | None]:
    """Собрать словарь баллов сразу по всем 4 темам для радар-чарта.

    - пройденные темы: их фактический средний балл из final_scores
    - текущая тема, которая в final_scores не попала (все вопросы пропустили без
      ответа): None — на радаре отрисуется как «не отвечал»
    - остальные темы: 0 — на радаре будет точка в центре
    """
    result: dict[str, float | None] = {}
    for t in _ALL_TOPICS:
        if t in final_scores:
            result[t] = final_scores[t]
        elif t == current_topic:
            result[t] = None
        else:
            result[t] = 0
    return result


@app.post("/health")
async def health() -> dict[str, str]:
    """Простейший liveness-чек."""
    return {"status": "ok"}


@app.post("/start", response_model=StartResponse)
async def start(req: StartRequest) -> StartResponse:
    """Начать новую тему интервью.

    Сбрасывает контекст темы (вопросы, история, баллы), но сохраняет
    final_scores из ранее пройденных тем — один session_id живёт между темами.
    """
    session_manager.update(
        req.session_id,
        topic=req.topic,
        question_index=0,
        per_question_scores=[],
        chat_history=[],
        asked_questions=[],
        history_checkpoint=0,
        current_question=None,
    )

    result = await start_interview(topic=req.topic, asked_questions=[])
    question = result.first_question

    # Чекпоинт = 0 (история пустая), сразу за ним идёт первый вопрос ассистента.
    session_manager.update(
        req.session_id,
        current_question=question,
        question_index=1,
        asked_questions=[question],
        history_checkpoint=0,
        chat_history=[{"role": "assistant", "content": question}],
    )

    return StartResponse(question=question, pronounce_text=result.pronounce_text)


@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest, request: Request) -> EvaluateResponse:
    """Оценить очередной ход кандидата.

    LLM возвращает один из трёх вариантов: попросить уточнения (CONTINUE),
    засчитать вопрос и выдать следующий (NEXT_QUESTION), или засчитать пятый
    подряд и завершить тему (TOPIC_COMPLETE). Если LLM упала — отдаём ERROR
    с человеческим сообщением, состояние сессии при этом не трогаем.
    """
    request_id: str = getattr(request.state, "request_id", "-")

    session = session_manager.get_or_create(req.session_id)
    if not session.topic or not session.current_question:
        raise HTTPException(status_code=400, detail="Session not started. Call /start first.")

    # Контекст для LLM — только текущий вопрос, без истории предыдущих,
    # чтобы модель не теряла фокус и не путала темы.
    current_history = session.chat_history[session.history_checkpoint :]

    t0 = time.monotonic()
    try:
        eval_result = await evaluate_answer(
            topic=session.topic,
            question=session.current_question,
            user_answer=req.text,
            history=current_history,
            asked_questions=session.asked_questions,
        )
    except Exception as exc:
        llm_latency_ms = int((time.monotonic() - t0) * 1000)
        logger.error(
            "Ошибка LLM в /evaluate: %s",
            exc,
            extra={"request_id": request_id},
        )
        logger.info(
            json.dumps(
                {
                    "event": "evaluate",
                    "session_id": req.session_id,
                    "topic": session.topic,
                    "question_index": session.question_index,
                    "user_text": req.text[:100],
                    "llm_latency_ms": llm_latency_ms,
                    "score": None,
                    "action": "ERROR",
                }
            ),
            extra={"request_id": request_id},
        )
        return EvaluateResponse(
            action="ERROR",
            feedback="Произошла ошибка при обработке ответа, попробуй ещё раз.",
            next_question=None,
            question_index=session.question_index,
            final_scores=None,
        )

    llm_latency_ms = int((time.monotonic() - t0) * 1000)

    # В историю кладём ответ пользователя и реакцию ассистента — это либо
    # уточняющий вопрос (если is_question_complete=False), либо финальный фидбек.
    assistant_content = (
        eval_result.clarifying_question
        if not eval_result.is_question_complete
        else eval_result.feedback
    )
    new_history = [
        *session.chat_history,
        {"role": "user", "content": req.text},
        {"role": "assistant", "content": assistant_content or ""},
    ]

    action: str
    next_question: str | None = None
    final_scores: dict[str, float | None] | None = None
    new_question_index = session.question_index

    if not eval_result.is_question_complete:
        # Остаёмся на том же вопросе — LLM попросила уточнение.
        action = "CONTINUE"
        session_manager.update(req.session_id, chat_history=new_history)
    else:
        action, next_question, final_scores, new_question_index = _advance_or_finalize(
            req.session_id, session, eval_result, new_history
        )

    logger.info(
        json.dumps(
            {
                "event": "evaluate",
                "session_id": req.session_id,
                "topic": session.topic,
                "question_index": session.question_index,
                "user_text": req.text[:100],
                "llm_latency_ms": llm_latency_ms,
                "score": eval_result.score,
                "action": action,
            }
        ),
        extra={"request_id": request_id},
    )

    return EvaluateResponse(
        action=action,
        feedback=eval_result.feedback,
        next_question=next_question,
        question_index=new_question_index,
        final_scores=final_scores,
    )


@app.post("/finish", response_model=EvaluateResponse)
async def finish(req: FinishRequest) -> EvaluateResponse:
    """Досрочно завершить тему: ставим балл за текущий вопрос и финализируем."""
    session = session_manager.get_or_create(req.session_id)
    if not session.topic:
        raise HTTPException(status_code=400, detail="Session not started. Call /start first.")

    # Балл за текущий вопрос ставим по тому, что кандидат уже успел сказать.
    current_history = session.chat_history[session.history_checkpoint :]
    score = await score_from_history(session.topic, session.current_question or "", current_history)
    session_manager.update(
        req.session_id, per_question_scores=[*session.per_question_scores, score]
    )

    final_session = session_manager.finalize_topic(req.session_id)
    final_scores = _build_final_scores(final_session.final_scores, session.topic)

    return EvaluateResponse(
        action="TOPIC_COMPLETE",
        feedback="Тема завершена.",
        next_question=None,
        question_index=session.question_index,
        final_scores=final_scores,
    )


@app.post("/skip", response_model=EvaluateResponse)
async def skip(req: SkipRequest) -> EvaluateResponse:
    """Пропустить текущий вопрос. Балл ставится по тому, что успели сказать (или 0)."""
    session = session_manager.get_or_create(req.session_id)
    if not session.topic:
        raise HTTPException(status_code=400, detail="Session not started. Call /start first.")

    current_history = session.chat_history[session.history_checkpoint :]
    score = await score_from_history(session.topic, session.current_question or "", current_history)
    new_scores = [*session.per_question_scores, score]

    # Пропущенный вопрос помечаем как заданный, чтобы /skip → /skip → ... не повторял его.
    new_asked = list(session.asked_questions)
    if session.current_question and session.current_question not in new_asked:
        new_asked.append(session.current_question)

    new_index = session.question_index + 1

    if new_index > 5:
        # Пропустили пятый — тема всё равно завершена, считаем средний.
        session_manager.update(
            req.session_id, asked_questions=new_asked, per_question_scores=new_scores
        )
        final_session = session_manager.finalize_topic(req.session_id)
        final_scores = _build_final_scores(final_session.final_scores, session.topic)
        return EvaluateResponse(
            action="TOPIC_COMPLETE",
            feedback="Тема завершена.",
            next_question=None,
            question_index=5,
            final_scores=final_scores,
        )

    # Следующий вопрос берём из банка (а не у LLM) — у LLM просили только оценить ответ.
    result = await start_interview(topic=session.topic, asked_questions=new_asked)
    next_question = result.first_question
    new_asked.append(next_question)

    # Чекпоинт двигаем в конец текущей истории — новый вопрос начинается
    # «с чистого листа», без контекста пропущенного.
    checkpoint = len(session.chat_history)
    new_history = [*session.chat_history, {"role": "assistant", "content": next_question}]

    session_manager.update(
        req.session_id,
        question_index=new_index,
        current_question=next_question,
        asked_questions=new_asked,
        chat_history=new_history,
        history_checkpoint=checkpoint,
        per_question_scores=new_scores,
    )

    return EvaluateResponse(
        action="NEXT_QUESTION",
        feedback="Вопрос пропущен.",
        next_question=next_question,
        question_index=new_index,
        final_scores=None,
    )
