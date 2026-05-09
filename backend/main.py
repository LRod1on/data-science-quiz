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
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# llm_service читает GIGACHAT_* на импорте — load_dotenv должен выполниться
# раньше следующих локальных импортов, поэтому E402 здесь подавлен намеренно.
load_dotenv(Path(__file__).resolve().parent / ".env")

from llm_service import evaluate_answer, score_from_history, start_interview  # noqa: E402
from questions import QUESTIONS  # noqa: E402
from session_manager import session_manager  # noqa: E402


class _RequestIdFormatter(logging.Formatter):
    """Подставляет '-' вместо отсутствующего request_id, чтобы строка лога не падала."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


_handler = logging.StreamHandler()
_handler.setFormatter(
    _RequestIdFormatter("%(asctime)s [%(levelname)s] request_id=%(request_id)s %(message)s")
)
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(_handler)
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
    """Каждому HTTP-запросу присваивается UUID, который потом виден во всех логах и в X-Request-Id."""
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


def _build_final_scores(final_scores: dict[str, float], current_topic: str) -> dict:
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


@app.post("/start")
async def start(request: Request) -> JSONResponse:
    """Начать новую тему интервью.

    Сбрасывает контекст темы (вопросы, история, баллы), но сохраняет
    final_scores из ранее пройденных тем — один session_id живёт между темами.
    """
    body = await request.json()
    session_id: str = body["session_id"]
    topic: str = body["topic"]

    session_manager.update(
        session_id,
        topic=topic,
        question_index=0,
        per_question_scores=[],
        chat_history=[],
        asked_questions=[],
        history_checkpoint=0,
        current_question=None,
    )

    result = await start_interview(topic=topic, asked_questions=[])
    question = result.first_question

    # Чекпоинт = 0 (история пустая), сразу за ним идёт первый вопрос ассистента.
    session_manager.update(
        session_id,
        current_question=question,
        question_index=1,
        asked_questions=[question],
        history_checkpoint=0,
        chat_history=[{"role": "assistant", "content": question}],
    )

    return JSONResponse(content={"question": question, "pronounce_text": result.pronounce_text})


@app.post("/evaluate")
async def evaluate(request: Request) -> JSONResponse:
    """Оценить очередной ход кандидата.

    LLM возвращает один из трёх вариантов: попросить уточнения (CONTINUE),
    засчитать вопрос и выдать следующий (NEXT_QUESTION), или засчитать пятый
    подряд и завершить тему (TOPIC_COMPLETE). Если LLM упала — отдаём ERROR
    с человеческим сообщением, состояние сессии при этом не трогаем.
    """
    body = await request.json()
    session_id: str = body["session_id"]
    user_text: str = body["text"]
    request_id: str = getattr(request.state, "request_id", "-")

    session = session_manager.get_or_create(session_id)
    if not session.topic or not session.current_question:
        return JSONResponse(
            status_code=400,
            content={"error": "Session not started. Call /start first."},
        )

    # Контекст для LLM — только текущий вопрос, без истории предыдущих,
    # чтобы модель не теряла фокус и не путала темы.
    current_history = session.chat_history[session.history_checkpoint :]

    t0 = time.monotonic()
    try:
        eval_result = await evaluate_answer(
            topic=session.topic,
            question=session.current_question,
            user_answer=user_text,
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
                    "session_id": session_id,
                    "topic": session.topic,
                    "question_index": session.question_index,
                    "user_text": user_text[:100],
                    "llm_latency_ms": llm_latency_ms,
                    "score": None,
                    "action": "ERROR",
                }
            ),
            extra={"request_id": request_id},
        )
        return JSONResponse(
            content={
                "action": "ERROR",
                "feedback": "Произошла ошибка при обработке ответа, попробуй ещё раз.",
                "next_question": None,
                "question_index": session.question_index,
                "final_scores": None,
            }
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
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_content or ""},
    ]

    action: str
    next_question: str | None = None
    final_scores: dict | None = None
    new_question_index = session.question_index

    if not eval_result.is_question_complete:
        # Остаёмся на том же вопросе — LLM попросила уточнение.
        action = "CONTINUE"
        session_manager.update(session_id, chat_history=new_history)

    else:
        # Вопрос засчитан. Если LLM при этом прислала score=null
        # (нарушение контракта в _SYSTEM_PROMPT) — пишем 0 и логируем,
        # чтобы не падать и видеть факт нарушения в логах.
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
            session_manager.update(
                session_id, per_question_scores=new_scores, chat_history=new_history
            )
            final_session = session_manager.finalize_topic(session_id)
            action = "TOPIC_COMPLETE"
            new_question_index = 5
            final_scores = _build_final_scores(final_session.final_scores, session.topic)

        else:
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
            action = "NEXT_QUESTION"

    logger.info(
        json.dumps(
            {
                "event": "evaluate",
                "session_id": session_id,
                "topic": session.topic,
                "question_index": session.question_index,
                "user_text": user_text[:100],
                "llm_latency_ms": llm_latency_ms,
                "score": eval_result.score,
                "action": action,
            }
        ),
        extra={"request_id": request_id},
    )

    return JSONResponse(
        content={
            "action": action,
            "feedback": eval_result.feedback,
            "next_question": next_question,
            "question_index": new_question_index,
            "final_scores": final_scores,
        }
    )


@app.post("/finish")
async def finish(request: Request) -> JSONResponse:
    """Досрочно завершить тему: ставим балл за текущий вопрос и финализируем."""
    body = await request.json()
    session_id: str = body["session_id"]

    session = session_manager.get_or_create(session_id)
    if not session.topic:
        return JSONResponse(
            status_code=400,
            content={"error": "Session not started. Call /start first."},
        )

    # Балл за текущий вопрос ставим по тому, что кандидат уже успел сказать.
    current_history = session.chat_history[session.history_checkpoint :]
    score = await score_from_history(session.topic, session.current_question or "", current_history)
    session_manager.update(session_id, per_question_scores=[*session.per_question_scores, score])

    final_session = session_manager.finalize_topic(session_id)
    final_scores = _build_final_scores(final_session.final_scores, session.topic)

    return JSONResponse(
        content={
            "action": "TOPIC_COMPLETE",
            "feedback": "Тема завершена.",
            "next_question": None,
            "question_index": session.question_index,
            "final_scores": final_scores,
        }
    )


@app.post("/skip")
async def skip(request: Request) -> JSONResponse:
    """Пропустить текущий вопрос. Балл ставится по тому, что успели сказать (или 0)."""
    body = await request.json()
    session_id: str = body["session_id"]

    session = session_manager.get_or_create(session_id)
    if not session.topic:
        return JSONResponse(
            status_code=400,
            content={"error": "Session not started. Call /start first."},
        )

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
            session_id, asked_questions=new_asked, per_question_scores=new_scores
        )
        final_session = session_manager.finalize_topic(session_id)
        final_scores = _build_final_scores(final_session.final_scores, session.topic)
        return JSONResponse(
            content={
                "action": "TOPIC_COMPLETE",
                "feedback": "Тема завершена.",
                "next_question": None,
                "question_index": 5,
                "final_scores": final_scores,
            }
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
        session_id,
        question_index=new_index,
        current_question=next_question,
        asked_questions=new_asked,
        chat_history=new_history,
        history_checkpoint=checkpoint,
        per_question_scores=new_scores,
    )

    return JSONResponse(
        content={
            "action": "NEXT_QUESTION",
            "feedback": "Вопрос пропущен.",
            "next_question": next_question,
            "question_index": new_index,
            "final_scores": None,
        }
    )
