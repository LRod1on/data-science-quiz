import logging
import traceback
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from dotenv import load_dotenv
import os

load_dotenv()

class _RequestIdFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] request_id=%(request_id)s %(message)s",
)
logging.getLogger().addFilter(_RequestIdFilter())
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
# Routes
# ---------------------------------------------------------------------------


@app.post("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/start")
async def start(request: Request) -> JSONResponse:
    return JSONResponse(status_code=501, content={"error": "Not Implemented"})


@app.post("/evaluate")
async def evaluate(request: Request) -> JSONResponse:
    return JSONResponse(status_code=501, content={"error": "Not Implemented"})


@app.post("/next")
async def next_question(request: Request) -> JSONResponse:
    return JSONResponse(status_code=501, content={"error": "Not Implemented"})


@app.post("/skip")
async def skip(request: Request) -> JSONResponse:
    return JSONResponse(status_code=501, content={"error": "Not Implemented"})
