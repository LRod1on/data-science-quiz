import json
import logging
import time
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv(Path(__file__).resolve().parent / ".env")

import random

from session_manager import session_manager
from llm_service import start_interview, evaluate_answer, score_from_history
from questions import QUESTIONS


class _Fmt(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


_handler = logging.StreamHandler()
_handler.setFormatter(_Fmt("%(asctime)s [%(levelname)s] request_id=%(request_id)s %(message)s"))
logging.getLogger().setLevel(logging.INFO)
logging.getLogger().addHandler(_handler)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up", extra={"request_id": "-"})
    yield
    logger.info("Shutting down", extra={"request_id": "-"})


app = FastAPI(title="Interview Trainer API", lifespan=lifespan)

_cors_origins: list[str] = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
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
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info(
        "Incoming %s %s", request.method, request.url.path,
        extra={"request_id": request_id},
    )
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id: str = getattr(request.state, "request_id", "-")
    logger.error(
        "Unhandled exception: %s\n%s",
        exc,
        traceback.format_exc(),
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "request_id": request_id},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_TOPICS = ["python", "classical_ml", "deep_learning", "nlp_cv"]


def _build_final_scores(final_scores: dict[str, float], current_topic: str) -> dict:
    """Return a score for all 4 topics.

    - Completed topics: their average score
    - Current topic not in final_scores: all questions were skipped → null
    - Other topics not yet attempted: 0
    """
    result = {}
    for t in _ALL_TOPICS:
        if t in final_scores:
            result[t] = final_scores[t]
        elif t == current_topic:
            result[t] = None  # topic was attempted but all questions skipped
        else:
            result[t] = 0
    return result


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/start")
async def start(request: Request) -> JSONResponse:
    body = await request.json()
    session_id: str = body["session_id"]
    topic: str = body["topic"]

    # Reset session for this topic (preserves final_scores from previous topics)
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

    # Checkpoint = 0 (empty history), then append the first question
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

    # Slice history to current question context only
    current_history = session.chat_history[session.history_checkpoint:]

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
            "LLM error in /evaluate: %s", exc,
            extra={"request_id": request_id},
        )
        logger.info(
            json.dumps({
                "event": "evaluate",
                "session_id": session_id,
                "topic": session.topic,
                "question_index": session.question_index,
                "user_text": user_text[:100],
                "llm_latency_ms": llm_latency_ms,
                "score": None,
                "action": "ERROR",
            }),
            extra={"request_id": request_id},
        )
        return JSONResponse(content={
            "action": "ERROR",
            "feedback": "Произошла ошибка при обработке ответа, попробуй ещё раз.",
            "next_question": None,
            "question_index": session.question_index,
            "final_scores": None,
        })

    llm_latency_ms = int((time.monotonic() - t0) * 1000)

    # Build updated history: append user turn + assistant response
    assistant_content = (
        eval_result.clarifying_question
        if not eval_result.is_question_complete
        else eval_result.feedback
    )
    new_history = session.chat_history + [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": assistant_content or ""},
    ]

    action: str
    next_question: str | None = None
    final_scores: dict | None = None
    new_question_index = session.question_index

    if not eval_result.is_question_complete:
        # Still on the same question (LLM asked a clarification)
        action = "CONTINUE"
        session_manager.update(session_id, chat_history=new_history)

    else:
        # Question is complete — record score (fall back to 0 if LLM returned null)
        score = eval_result.score
        if score is None:
            logger.warning(
                "score=null despite is_question_complete=true (session=%s, q=%d), defaulting to 0",
                session_id,
                session.question_index,
            )
            score = 0.0
        new_scores = session.per_question_scores + [score]

        if session.question_index >= 5:
            # All 5 questions done — finalize topic
            session_manager.update(session_id, per_question_scores=new_scores, chat_history=new_history)
            final_session = session_manager.finalize_topic(session_id)
            action = "TOPIC_COMPLETE"
            new_question_index = 5
            final_scores = _build_final_scores(final_session.final_scores, session.topic)

        else:
            # Move to next question
            next_question = eval_result.next_question
            if not next_question:
                # LLM didn't generate a next question — fall back to the bank
                pool = [q for q in QUESTIONS[session.topic] if q not in session.asked_questions]
                if not pool:
                    pool = QUESTIONS[session.topic]
                next_question = random.choice(pool)

            new_asked = session.asked_questions + [next_question]
            new_question_index = session.question_index + 1
            # Checkpoint: after current turn, before next question
            checkpoint = len(new_history)
            new_history_with_next = new_history + [
                {"role": "assistant", "content": next_question}
            ]
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
        json.dumps({
            "event": "evaluate",
            "session_id": session_id,
            "topic": session.topic,
            "question_index": session.question_index,
            "user_text": user_text[:100],
            "llm_latency_ms": llm_latency_ms,
            "score": eval_result.score,
            "action": action,
        }),
        extra={"request_id": request_id},
    )

    return JSONResponse(content={
        "action": action,
        "feedback": eval_result.feedback,
        "next_question": next_question,
        "question_index": new_question_index,
        "final_scores": final_scores,
    })


@app.post("/finish")
async def finish(request: Request) -> JSONResponse:
    body = await request.json()
    session_id: str = body["session_id"]

    session = session_manager.get_or_create(session_id)
    if not session.topic:
        return JSONResponse(
            status_code=400,
            content={"error": "Session not started. Call /start first."},
        )

    # Score whatever the candidate said on the current question before finalizing
    current_history = session.chat_history[session.history_checkpoint:]
    score = await score_from_history(session.topic, session.current_question or "", current_history)
    session_manager.update(session_id, per_question_scores=session.per_question_scores + [score])

    final_session = session_manager.finalize_topic(session_id)
    final_scores = _build_final_scores(final_session.final_scores, session.topic)

    return JSONResponse(content={
        "action": "TOPIC_COMPLETE",
        "feedback": "Тема завершена.",
        "next_question": None,
        "question_index": session.question_index,
        "final_scores": final_scores,
    })


@app.post("/skip")
async def skip(request: Request) -> JSONResponse:
    body = await request.json()
    session_id: str = body["session_id"]

    session = session_manager.get_or_create(session_id)
    if not session.topic:
        return JSONResponse(
            status_code=400,
            content={"error": "Session not started. Call /start first."},
        )

    # Score whatever was said on the current question before skipping
    current_history = session.chat_history[session.history_checkpoint:]
    score = await score_from_history(session.topic, session.current_question or "", current_history)
    new_scores = session.per_question_scores + [score]

    # Add skipped question to asked_questions so it won't be repeated
    new_asked = list(session.asked_questions)
    if session.current_question and session.current_question not in new_asked:
        new_asked.append(session.current_question)

    new_index = session.question_index + 1

    if new_index > 5:
        # Skipped the last question — finalize with the just-scored question
        session_manager.update(session_id, asked_questions=new_asked, per_question_scores=new_scores)
        final_session = session_manager.finalize_topic(session_id)
        final_scores = _build_final_scores(final_session.final_scores, session.topic)
        return JSONResponse(content={
            "action": "TOPIC_COMPLETE",
            "feedback": "Тема завершена.",
            "next_question": None,
            "question_index": 5,
            "final_scores": final_scores,
        })

    # Pick next question from bank (not from LLM)
    result = await start_interview(topic=session.topic, asked_questions=new_asked)
    next_question = result.first_question
    new_asked.append(next_question)

    # Move the history checkpoint to the end of current history (drop skipped Q context)
    checkpoint = len(session.chat_history)
    new_history = session.chat_history + [
        {"role": "assistant", "content": next_question}
    ]

    session_manager.update(
        session_id,
        question_index=new_index,
        current_question=next_question,
        asked_questions=new_asked,
        chat_history=new_history,
        history_checkpoint=checkpoint,
        per_question_scores=new_scores,
    )

    return JSONResponse(content={
        "action": "NEXT_QUESTION",
        "feedback": "Вопрос пропущен.",
        "next_question": next_question,
        "question_index": new_index,
        "final_scores": None,
    })
