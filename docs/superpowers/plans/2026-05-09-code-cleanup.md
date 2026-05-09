# Чистка кода — план реализации

> **Для агентов-исполнителей:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** привести рабочий учебный проект к виду «кода, написанного человеком»:
аккуратные типы, осмысленные русские комментарии, читаемые границы модулей.
Поведение приложения и сценариев Салюта не меняется.

**Architecture:** идём послойно (backend → frontend → docs), внутри каждого
слоя — три прохода (формат/линт → типы+комменты → локальный рефакторинг).
Каждый проход = один коммит. Никакой смены архитектуры (классовый `App`
остаётся классовым, FastAPI — без роутеров).

**Tech Stack:** Python 3.11+ (FastAPI, Pydantic v2, httpx, pytest); React 18 (CRA, styled-components, chart.js); ruff для Python.

**Связанный спек:** `docs/superpowers/specs/2026-05-09-code-cleanup-design.md`.

---

## Карта файлов

**Создаются:**
- `backend/pyproject.toml` — конфиг ruff
- `.editorconfig` — общие правила отступов
- `backend/logging_config.py` — извлечённый setup логирования
- `backend/schemas.py` — Pydantic-модели для запросов/ответов FastAPI
- `src/services/assistant.js` — голая интеграция с Салютом (без React)
- `src/services/evaluationDispatch.js` — чистый декодер ответа `/evaluate`

**Меняются:**
- `backend/main.py` — переход на Pydantic-схемы, извлечения, русские комменты
- `backend/llm_service.py` — типы, русские докстринги, ruff
- `backend/session_manager.py` — `datetime.utcnow()` → `datetime.now(UTC)`, типы
- `backend/questions.py` — минимально
- `backend/tests/*.py` — русские докстринги, ruff
- `src/App.jsx` — убрать debug-логи, использовать сервисы, объединить handlers
- `src/api/interviewApi.js` — JSDoc-типы
- `src/views/*.jsx`, `src/components/ErrorBoundary.jsx`, `src/constants/topics.js` — комменты, мелочи
- `README.md` — фактическая сверка
- `CLAUDE.md` — убрать ссылки на удалённые файлы (`scenario-example.zip`, `PLAN.md`)

---

## Задачи

### Task 0: Тулинг — ruff и .editorconfig

**Files:**
- Create: `backend/pyproject.toml`
- Create: `.editorconfig`

- [ ] **Step 1: Создать `backend/pyproject.toml` с конфигом ruff**

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "UP",  # pyupgrade (модернизирует синтаксис под target-version)
    "SIM", # flake8-simplify
    "RUF", # ruff-specific
]
ignore = [
    "E501", # длину строк ловит форматтер
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["B011"]  # asserts в тестах — это ок
```

- [ ] **Step 2: Создать `.editorconfig` в корне репозитория**

```editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.py]
indent_style = space
indent_size = 4

[*.{js,jsx,ts,tsx,json,css}]
indent_style = space
indent_size = 2

[*.md]
trim_trailing_whitespace = false
```

- [ ] **Step 3: Установить ruff (если не установлен) и проверить, что конфиг валиден**

```bash
# Если ruff отсутствует:
pipx install ruff
# Или через pip в активном venv:
pip install ruff

# Проверка конфига:
cd backend && ruff check --no-fix . 
```

Expected: ruff не падает на парсинге конфига; либо находит проблемы (нормально), либо проходит чисто.

- [ ] **Step 4: Коммит**

```bash
git add backend/pyproject.toml .editorconfig
git commit -m "chore: add ruff config and .editorconfig"
```

---

### Task 1: Backend pass 1 — формат и линтер

**Files:**
- Modify: все `.py` в `backend/` и `backend/tests/`

- [ ] **Step 1: Зафиксировать текущее состояние тестов (baseline)**

```bash
cd backend && pytest -q
```

Expected: все тесты зелёные. Если что-то красное до начала — сначала разобраться, потом продолжать.

- [ ] **Step 2: Прогнать форматтер**

```bash
cd backend && ruff format .
```

Expected: ruff форматирует файлы; список изменённых выводит на stdout.

- [ ] **Step 3: Прогнать линтер с автофиксом**

```bash
cd backend && ruff check --fix .
```

Expected: часть проблем чинится автоматом (импорты, deprecated синтаксис под `UP`-правила). Что не починилось — выводится в stdout.

- [ ] **Step 4: Прогнать линтер ещё раз для отчёта**

```bash
cd backend && ruff check .
```

Если остались предупреждения — пройтись по ним руками. Чаще всего это:
- Неиспользованные импорты (удалить)
- Длинные строки в тестах с длинными ожидаемыми сообщениями (можно `# noqa: E501` если оправдано — но мы их игнорируем по умолчанию, не должно быть)
- Variable shadowing → переименовать

- [ ] **Step 5: Прогнать тесты — должны быть зелёные**

```bash
cd backend && pytest -q
```

Expected: все тесты зелёные. Если красные — `git diff` чтобы понять, что ruff поменял неудачно. Чаще всего это переупорядочивание импортов, ломающее side-effects (например, `load_dotenv` до импорта). В нашем `main.py` есть такое: `load_dotenv` стоит ДО `from session_manager import ...`. Если ruff переставит — придётся вернуть руками или вынести `load_dotenv` в отдельный helper.

- [ ] **Step 6: Коммит**

```bash
git add backend/
git commit -m "style(backend): apply ruff format and autofix"
```

---

### Task 2: Backend pass 2 — типы и русские комментарии

**Files:**
- Modify: `backend/session_manager.py`, `backend/llm_service.py`, `backend/main.py`, `backend/questions.py`, `backend/tests/*.py`

**Принципы для всего прохода:**
- Все public-функции имеют полные type hints на параметрах и возвращаемом значении.
- Докстринги — на русском. Стиль: одна строка для очевидных, многострочный с описанием параметров — только для нетривиальных функций.
- Английские banner-комментарии вида `# ----- Helpers -----` УБРАТЬ. Это AI-стайл, в человеческом коде так не пишут.
- Комментарии оставлять только там, где **зачем** не очевидно из кода. Не комментировать **что** делает код.
- Под капотом: где есть `from __future__ import annotations` — оставить (это не вред); если ruff удалил — норм.

- [ ] **Step 1: `session_manager.py` — типы и докстринги**

Файл уже типизирован хорошо. Нужно:
- Удалить banner-комментарии `# ----` (их там нет, проверить).
- Все методы получают однострочные русские докстринги, объясняющие смысл (не **что**, а **зачем** существуют).
- Метод `get_or_create` — пояснить **почему** возвращается `model_copy()` (защита от внешних мутаций состояния).

Пример итогового вида ключевого метода:

```python
def get_or_create(self, session_id: str) -> SessionState:
    """Вернуть копию состояния сессии. Создаст пустую, если её ещё нет.

    Возвращается копия, а не сам объект из словаря — чтобы вызывающий код
    не мог случайно мутировать внутреннее состояние манагера в обход update().
    """
    if session_id not in self._sessions:
        self._sessions[session_id] = SessionState(session_id=session_id)
    return self._sessions[session_id].model_copy()
```

- [ ] **Step 2: `questions.py` — минимально**

Файл — словарь данных. Добавить однострочный модульный докстринг:

```python
"""Банк вопросов по темам интервью. По 15 вопросов на тему."""
```

Больше ничего не делать.

- [ ] **Step 3: `llm_service.py` — докстринги и комменты на русском**

- Модульный докстринг уже есть на английском — перевести.
- `_get_access_token`, `_call_llm`, `_parse_llm_json` — однострочные русские докстринги.
- `evaluate_answer`, `score_from_history`, `start_interview` — короткий русский докстринг с пояснением **зачем** (роли в системе), не **что** (видно по сигнатуре).
- Английский комментарий `# Suppress SSL warning — Sber uses a Russian CA...` → перевести.
- Banner-комментарии `# ---` УБРАТЬ.

Пример:

```python
"""Слой работы с LLM: выбор вопросов и оценка ответов через GigaChat."""

# GigaChat использует российский CA, которого нет в дефолтном bundle
# Python — отключаем проверку SSL и заодно глушим warning от httpx.
warnings.filterwarnings("ignore", message="Unverified HTTPS request")
```

- [ ] **Step 4: `main.py` — докстринги, русские комменты, banner-комментарии**

- Удалить ВСЕ `# -------- Helpers --------`, `# -------- Routes --------` и подобные.
- Все английские inline-комменты внутри `/evaluate`, `/skip`, `/finish` (`# Reset session...`, `# Slice history...`, `# Question is complete — record score...` и т.д.) — перевести.
- Эндпоинты получают русские докстринги: одна строка, что делает, и если есть нетривиальный side-effect — отдельная строка про него.

Пример для `/start`:

```python
@app.post("/start")
async def start(request: Request) -> JSONResponse:
    """Начать новую тему интервью.

    Сбрасывает состояние сессии для текущей темы, но сохраняет накопленные
    final_scores из ранее пройденных тем (один session_id живёт между темами).
    """
    ...
```

Пример для `/evaluate` (внутреннее ветвление):

```python
if not eval_result.is_question_complete:
    # LLM попросила уточнение — буфер ответа очищаем (новый виток),
    # но question_index не двигаем.
    action = "CONTINUE"
    ...
else:
    # Вопрос засчитан — записываем балл. Если LLM прислала null при
    # is_question_complete=true (нарушение контракта промпта) —
    # ставим 0 и логируем warning, но не падаем.
    score = eval_result.score
    if score is None:
        logger.warning(...)
        score = 0.0
```

- [ ] **Step 5: `backend/tests/*.py` — русские докстринги тестов и фикстур**

- Модульные докстринги в каждом тестовом файле — на русском.
- Banner-комментарии `# ---- /start ----` — убрать. Тесты группируются по
  именам функций (`test_start_*`, `test_evaluate_*`), баннеры избыточны.
- Тесты с english-докстрингами (`"""Skipping a question with no user turn → score 0..."""`) — перевести.

Пример:

```python
"""Эндпоинт-тесты /start, /evaluate, /skip через FastAPI TestClient.

llm_service замокан — проверяется логика маршрутов и переходы состояния
сессии, а не поведение LLM."""
```

- [ ] **Step 6: Прогнать ruff format и тесты**

```bash
cd backend && ruff format . && ruff check . && pytest -q
```

Expected: всё зелёное.

- [ ] **Step 7: Коммит**

```bash
git add backend/
git commit -m "docs(backend): translate comments to Russian, polish docstrings and types"
```

---

### Task 3: Backend pass 3 — локальный рефакторинг

**Files:**
- Create: `backend/logging_config.py`
- Create: `backend/schemas.py`
- Modify: `backend/main.py`, `backend/session_manager.py`, `backend/tests/test_session.py`

Работа делится на 4 относительно независимых под-шага. Каждый — отдельный
коммит, чтобы откатывать при поломке точечно.

#### 3a. Извлечь конфиг логирования

- [ ] **Step 1: Создать `backend/logging_config.py`**

```python
"""Конфигурация логирования для бэкенда.

Все логи получают префикс с request_id, который проставляется
middleware на каждый HTTP-запрос. Записи без request_id (на старте
приложения, в фоновых задачах) показываются с прочерком.
"""

import logging


class _RequestIdFormatter(logging.Formatter):
    """Подставляет '-' вместо отсутствующего request_id, чтобы формат не падал."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    """Настроить root logger один раз на старте приложения."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        _RequestIdFormatter(
            "%(asctime)s [%(levelname)s] request_id=%(request_id)s %(message)s"
        )
    )
    root = logging.getLogger()
    root.setLevel(level)
    # Защита от двойной инициализации при reload в uvicorn
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
```

- [ ] **Step 2: Использовать `setup_logging` в `main.py`**

Удалить из `main.py` классы `_Fmt`, переменную `_handler`, явные `addHandler` и `setLevel`. Вместо этого вверху файла:

```python
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)
```

- [ ] **Step 3: Прогнать тесты**

```bash
cd backend && pytest -q
```

Expected: зелёное.

- [ ] **Step 4: Коммит**

```bash
git add backend/logging_config.py backend/main.py
git commit -m "refactor(backend): extract logging setup to logging_config.py"
```

#### 3b. Pydantic-схемы запросов/ответов

- [ ] **Step 1: Создать `backend/schemas.py`**

```python
"""Pydantic-схемы запросов и ответов FastAPI-эндпоинтов.

Типизация тел запросов даёт автоматическую валидацию (422 на кривое тело)
и сразу получаем интерактивную доку на /docs.
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
    action: Action
    feedback: str
    next_question: str | None = None
    question_index: int
    final_scores: dict[str, float | None] | None = None
```

- [ ] **Step 2: Переписать эндпоинты в `main.py` под схемы**

Сейчас:

```python
@app.post("/start")
async def start(request: Request) -> JSONResponse:
    body = await request.json()
    session_id: str = body["session_id"]
    topic: str = body["topic"]
    ...
```

Станет:

```python
@app.post("/start", response_model=StartResponse)
async def start(req: StartRequest) -> StartResponse:
    ...
    return StartResponse(question=question, pronounce_text=result.pronounce_text)
```

То же самое для `/evaluate`, `/finish`, `/skip`. **Внимание:** request_id всё ещё нужен для логов — берётся из `request: Request` параметра, который можно оставить как **второй** параметр функции:

```python
@app.post("/evaluate", response_model=EvaluateResponse)
async def evaluate(req: EvaluateRequest, request: Request) -> EvaluateResponse:
    request_id: str = getattr(request.state, "request_id", "-")
    ...
```

- [ ] **Step 3: Проверить, что тесты не сломались на изменении формата ошибки 400 → 422**

В `test_endpoints.py` есть `test_evaluate_without_start_returns_400`. Сейчас 400 возвращается руками внутри хендлера, когда `not session.topic`. После Pydantic-схем — 422 возвращается ТОЛЬКО на невалидном теле запроса (неправильные типы, отсутствующие поля). Логика «сессия не стартовала» — это всё ещё 400 руками. Поэтому тест должен продолжать работать.

```bash
cd backend && pytest -q
```

Expected: зелёное.

Если что-то красное — внимательно прочитать вывод и поправить либо схему, либо хендлер.

- [ ] **Step 4: Коммит**

```bash
git add backend/schemas.py backend/main.py
git commit -m "refactor(backend): use Pydantic schemas for request/response"
```

#### 3c. Извлечь хелпер «продвинуть вопрос или финализировать тему»

- [ ] **Step 1: Найти и понять текущий блок в `/evaluate`**

В `main.py` внутри `/evaluate` есть ветка `else:` (после `if not eval_result.is_question_complete:`), которая занимает ~40 строк. Это и есть кандидат на извлечение.

- [ ] **Step 2: Извлечь приватный хелпер в том же `main.py`**

Над эндпоинтами (рядом с `_build_final_scores`):

```python
async def _advance_or_finalize(
    session_id: str,
    session: SessionState,
    eval_result: EvaluationResult,
    new_history: list[dict[str, str]],
    user_text: str,  # noqa: ARG001 — пока не используется, но согласует сигнатуру
) -> tuple[str, str | None, dict | None, int]:
    """Записать балл за текущий вопрос и продвинуть сессию.

    Возвращает кортеж (action, next_question, final_scores, new_question_index).
    Если был последний (5-й) вопрос — финализирует тему и возвращает final_scores.
    Иначе — берёт следующий вопрос (из ответа LLM или из банка) и обновляет сессию.
    """
    score = eval_result.score
    if score is None:
        logger.warning(
            "score=null при is_question_complete=true (session=%s, q=%d), пишем 0",
            session_id, session.question_index,
        )
        score = 0.0
    new_scores = session.per_question_scores + [score]

    if session.question_index >= 5:
        session_manager.update(session_id, per_question_scores=new_scores, chat_history=new_history)
        final_session = session_manager.finalize_topic(session_id)
        return "TOPIC_COMPLETE", None, _build_final_scores(final_session.final_scores, session.topic), 5

    next_question = eval_result.next_question
    if not next_question:
        pool = [q for q in QUESTIONS[session.topic] if q not in session.asked_questions]
        if not pool:
            pool = QUESTIONS[session.topic]
        next_question = random.choice(pool)

    new_asked = session.asked_questions + [next_question]
    new_question_index = session.question_index + 1
    checkpoint = len(new_history)
    new_history_with_next = new_history + [{"role": "assistant", "content": next_question}]
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
```

Импортировать `SessionState` из `session_manager` если ещё не импортирован.

- [ ] **Step 3: Заменить блок в `/evaluate` на вызов хелпера**

В `/evaluate` после ветки `if not eval_result.is_question_complete:` (CONTINUE) ветка `else:` сжимается до:

```python
else:
    action, next_question, final_scores, new_question_index = await _advance_or_finalize(
        session_id, session, eval_result, new_history, user_text,
    )
```

- [ ] **Step 4: Прогнать тесты**

```bash
cd backend && pytest -q
```

Expected: зелёное. Особое внимание `test_evaluate_next_question` и `test_evaluate_topic_complete` — они проверяют именно эту ветку.

- [ ] **Step 5: Коммит**

```bash
git add backend/main.py
git commit -m "refactor(backend): extract _advance_or_finalize from /evaluate"
```

#### 3d. `datetime.utcnow()` → `datetime.now(UTC)`

- [ ] **Step 1: Найти все вызовы**

```bash
grep -rn 'datetime.utcnow' backend/
```

Ожидается: `session_manager.py` (3 вхождения), `tests/test_session.py` (1 вхождение).

- [ ] **Step 2: Заменить в `session_manager.py`**

Импорты:
```python
from datetime import UTC, datetime, timedelta
```

Все три места:
```python
# было
started_at: datetime = Field(default_factory=datetime.utcnow)
last_activity_at: datetime = Field(default_factory=datetime.utcnow)
# стало
started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
last_activity_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

```python
# в update():
update={**fields, "last_activity_at": datetime.now(UTC)}
# в cleanup_stale():
cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
```

- [ ] **Step 3: Заменить в `tests/test_session.py`**

```python
# было
old_time = datetime.utcnow() - timedelta(minutes=90)
# стало
from datetime import UTC
old_time = datetime.now(UTC) - timedelta(minutes=90)
```

- [ ] **Step 4: Прогнать тесты**

```bash
cd backend && pytest -q
```

Expected: зелёное. Если `test_cleanup_stale_removes_old_session` упадёт с ошибкой про сравнение naive и aware datetime — это значит где-то осталось старое `utcnow()`. Проверить grep ещё раз.

- [ ] **Step 5: Коммит**

```bash
git add backend/session_manager.py backend/tests/test_session.py
git commit -m "refactor(backend): use timezone-aware datetime.now(UTC)"
```

---

### Task 4: Frontend pass 1 — eslint и debug-логи

**Files:**
- Modify: `src/App.jsx`

- [ ] **Step 1: Зафиксировать baseline сборки**

```bash
yarn build 2>&1 | tail -30
```

Запомнить, есть ли warnings и какие. Дальше сравниваем с этим baseline.

- [ ] **Step 2: Удалить debug `console.log` из `App.jsx`**

Удалить:
- `console.log('constructor');` (строка 36)
- `console.log('assistant.on(data)', event);` (строка 59)
- `console.log(`assistant.on(data): character: "${event?.character?.id}"`);` (строка 61)
- `console.log('dispatchAssistantAction', action);` (строка 110)
- `console.log('sendData SPEAK ack:', data);` (строка 144)
- `console.log('componentDidMount');` (строка 89) → вместе с пустым `componentDidMount` методом
- `console.log('render');` (строка 293)
- `assistant.on('start', ...)` callback с `console.log` — целиком убрать (нет смысла без логов)
- `assistant.on('command', ...)` — то же самое, удалить целиком
- `assistant.on('tts', ...)` — то же самое

**Оставить:**
- `assistant.on('error', (event) => console.warn('assistant error:', event));` — переименовать `console.log` → `console.warn`, изменить текст. Этот лог нужен (ошибки ассистента полезны при отладке прода).
- `console.warn('Unknown action type:', action.type);` — оставить, это валидный warn.
- `console.warn('_speakText sendData error:', err);` → текст оставить или поправить, удалять не надо.
- `console.error('ErrorBoundary caught:', error, info);` — оставить.

- [ ] **Step 3: Запустить eslint --fix**

```bash
yarn eslint --fix src/
```

Если в `package.json` нет такого скрипта — использовать:

```bash
npx eslint --fix src/
```

Expected: либо чистый прогон, либо несколько мелких автофиксов.

- [ ] **Step 4: Запустить yarn build, сравнить с baseline**

```bash
yarn build 2>&1 | tail -30
```

Expected: warnings не появилось новых (могло уменьшиться).

- [ ] **Step 5: Коммит**

```bash
git add src/App.jsx
git commit -m "chore(frontend): drop debug console.logs and empty lifecycle hooks"
```

---

### Task 5: Frontend pass 2 — JSDoc-типы и русские комментарии

**Files:**
- Modify: `src/api/interviewApi.js`, `src/App.jsx`, `src/views/*.jsx`, `src/components/ErrorBoundary.jsx`, `src/constants/topics.js`

**Принципы:**
- Комментарии — на русском.
- В JS нет typeshints как в Python, но JSDoc даёт автокомплит в WebStorm/VSCode и читателю — контракт. Применяем точечно: к API-функциям и к нетривиальным хелперам.
- Английские комменты с реальной информацией (например, про `createSmartappDebugger initPhrase`) — перевести, не выкинуть.

- [ ] **Step 1: `src/api/interviewApi.js` — JSDoc-типы**

```javascript
/**
 * @typedef {'CONTINUE' | 'NEXT_QUESTION' | 'TOPIC_COMPLETE' | 'ERROR'} Action
 *
 * @typedef {Object} EvaluateResponse
 * @property {Action} action
 * @property {string} feedback
 * @property {string|null} next_question
 * @property {number} question_index
 * @property {Object<string, number|null>|null} final_scores
 *
 * @typedef {Object} StartResponse
 * @property {string} question
 * @property {string} pronounce_text
 */

const BASE_URL = process.env.REACT_APP_BACKEND_URL ?? 'http://localhost:8000';
const TIMEOUT_MS = 35000;

// Внутренний хелпер: POST с таймаутом и человеческими сообщениями об ошибках.
async function apiFetch(path, body) { ... }

/**
 * @param {string} sessionId
 * @param {string} topic
 * @returns {Promise<StartResponse>}
 */
export async function startInterview(sessionId, topic) { ... }

/** @returns {Promise<EvaluateResponse>} */
export async function evaluateAnswer(sessionId, text) { ... }

/** @returns {Promise<EvaluateResponse>} */
export async function skipQuestion(sessionId) { ... }

/** @returns {Promise<EvaluateResponse>} */
export async function finishInterview(sessionId) { ... }
```

- [ ] **Step 2: `src/App.jsx` — русские комменты, без переписывания логики**

- Английский комментарий про `initPhrase` (строки 222-223) — перевести:
  ```javascript
  // Защита от того, что initPhrase из createSmartappDebugger
  // приходит как голосовое событие с задержкой и попадает в USER_ANSWER.
  // Команды запуска начинаются с «запусти/открой/вруби».
  if (/^(запусти|открой|вруби)\s/i.test(text)) return;
  ```
- Комментарий `// LLM asked a clarifying question — feedback IS the clarifying question` → перевести.
- Комментарий `// ERROR or unknown action — keep the buffer so the user can retry "готово"` → перевести.
- Inline-комментарии у полей `state` (строки 41-53) — оставить, перевести то что на английском (там почти всё на английском):
  ```javascript
  this.state = {
    status: 'welcome',       // 'welcome' | 'interview' | 'results'
    currentTopic: null,      // 'python' | 'classical_ml' | 'deep_learning' | 'nlp_cv'
    questionIndex: 0,        // 1..5 во время интервью, 0 на welcome
    questionText: '',
    answerBuffer: '',        // фрагменты речи, склеенные пробелами; чистится по FINISH_ANSWER
    isLoading: false,
    radarScores: {
      python: null,
      classical_ml: null,
      deep_learning: null,
      nlp_cv: null,
    },
    lastError: null,
  };
  ```

- [ ] **Step 3: `src/views/InterviewView.jsx`, `WelcomeView.jsx`, `ResultView.jsx`**

В этих файлах сейчас почти нет комментариев. Главное:
- Если где-то есть английский inline-комментарий — перевести.
- НЕ добавлять комментарии «по делу» к каждому styled-component. Они и так понятны по имени.
- В `ResultView.jsx`: над `CHART_OPTIONS` короткий русский комментарий вида:
  ```javascript
  // Конфиг chart.js: радар 0..10, без анимации, тёмная тема под TV-экран SberBox.
  const CHART_OPTIONS = { ... };
  ```

- [ ] **Step 4: `src/components/ErrorBoundary.jsx`, `src/constants/topics.js`**

- `topics.js` — добавить однострочный JSDoc-комментарий в начале файла:
  ```javascript
  // Темы интервью: ключи синхронизированы с backend/questions.py.
  ```
- `ErrorBoundary.jsx` — `console.error` оставить как есть, без комментариев.

- [ ] **Step 5: yarn build**

```bash
yarn build 2>&1 | tail -30
```

Expected: warnings не появилось.

- [ ] **Step 6: Коммит**

```bash
git add src/
git commit -m "docs(frontend): translate comments to Russian, add JSDoc types to API"
```

---

### Task 6: Frontend pass 3 — извлечение сервисов и подчистка App.jsx

**Files:**
- Create: `src/services/assistant.js`
- Create: `src/services/evaluationDispatch.js`
- Modify: `src/App.jsx`

#### 6a. Извлечь `src/services/assistant.js`

- [ ] **Step 1: Создать файл**

```javascript
// Тонкая обёртка над @salutejs/client.
// Вынесена из App.jsx, чтобы вся интеграция с Салютом жила в одном месте
// и компонент не знал про различия dev/prod.

import { createAssistant, createSmartappDebugger } from '@salutejs/client';

/**
 * Создать инстанс ассистента.
 * В development подключается createSmartappDebugger (нужны токены из .env);
 * в production — createAssistant, который уже работает в окружении SberBox/Салют.
 *
 * @param {() => object} getState — функция, возвращающая item_selector для голосовых команд.
 * @returns ассистент @salutejs/client.
 */
export function createAssistantInstance(getState) {
  if (process.env.NODE_ENV === 'development') {
    return createSmartappDebugger({
      token: process.env.REACT_APP_TOKEN ?? '',
      initPhrase: `Запусти ${process.env.REACT_APP_SMARTAPP}`,
      getState,
      nativePanel: {
        defaultText: 'начни интервью по питону',
        screenshotMode: false,
        tabIndex: -1,
      },
    });
  }
  return createAssistant({ getState });
}

/**
 * Озвучить текст через TTS Салюта (action SPEAK), а в dev — через Web Speech API,
 * потому что в режиме createSmartappDebugger TTS прода недоступно.
 *
 * @param {object} assistant — инстанс из createAssistantInstance.
 * @param {string} text
 */
export function speak(assistant, text) {
  if (!text) return;

  if (process.env.NODE_ENV === 'development') {
    window.speechSynthesis?.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ru-RU';
    window.speechSynthesis?.speak(utterance);
    return;
  }

  try {
    const unsubscribe = assistant.sendData(
      { action: { action_id: 'SPEAK' }, eventData: { text } },
      () => { if (typeof unsubscribe === 'function') unsubscribe(); }
    );
  } catch (err) {
    console.warn('assistant.sendData(SPEAK) failed:', err);
  }
}
```

- [ ] **Step 2: Использовать в `App.jsx`**

В импорты:
```javascript
import { createAssistantInstance, speak } from './services/assistant';
```

Удалить из `App.jsx`:
- функцию `initializeAssistant` (строки 16-31)
- метод `_speakText` (строки 131-151)

Заменить:
- `this.assistant = initializeAssistant(...)` → `this.assistant = createAssistantInstance(...)`
- ВСЕ вызовы `this._speakText(text)` → `speak(this.assistant, text)`

- [ ] **Step 3: yarn build**

```bash
yarn build 2>&1 | tail -30
```

Expected: чисто.

- [ ] **Step 4: Коммит**

```bash
git add src/services/assistant.js src/App.jsx
git commit -m "refactor(frontend): extract Salut integration to services/assistant.js"
```

#### 6b. Извлечь `src/services/evaluationDispatch.js`

- [ ] **Step 1: Создать файл с чистой функцией**

```javascript
// Декодирование ответа /evaluate: преобразует ответ бэка в патч для setState
// и текст для озвучки. Чистая функция — так проще читать и тестировать,
// чем имея этот же switch внутри классового компонента с setState внутри.

/**
 * @param {import('../api/interviewApi').EvaluateResponse} data
 * @param {string|null} currentTopic — для записи балла в радар при TOPIC_COMPLETE.
 * @returns {{ stateUpdate: object, speechText: string }}
 */
export function decodeEvaluateResponse(data, currentTopic) {
  const { action, feedback, next_question: nextQ, question_index, final_scores } = data;

  if (action === 'TOPIC_COMPLETE') {
    return {
      stateUpdate: (prev) => ({
        status: 'results',
        isLoading: false,
        lastError: null,
        answerBuffer: '',
        radarScores: {
          ...prev.radarScores,
          [currentTopic]: final_scores?.[currentTopic] ?? null,
        },
      }),
      speechText: feedback,
    };
  }

  if (action === 'NEXT_QUESTION') {
    return {
      stateUpdate: {
        questionText: nextQ,
        questionIndex: question_index,
        isLoading: false,
        lastError: null,
        answerBuffer: '',
      },
      speechText: feedback,
    };
  }

  if (action === 'CONTINUE') {
    // Уточняющий вопрос от LLM: feedback и есть текст уточнения.
    return {
      stateUpdate: {
        questionText: feedback,
        isLoading: false,
        lastError: null,
        answerBuffer: '',
      },
      speechText: feedback,
    };
  }

  // ERROR или неизвестный action — буфер не трогаем, чтобы пользователь
  // мог повторить «готово» с тем же ответом.
  return {
    stateUpdate: { isLoading: false, lastError: feedback || 'Ошибка сервера' },
    speechText: feedback,
  };
}
```

- [ ] **Step 2: Заменить `_handleEvaluateResponse` в `App.jsx`**

Удалить метод `_handleEvaluateResponse` целиком. Вместо него — приватный метод-обёртка:

```javascript
import { decodeEvaluateResponse } from './services/evaluationDispatch';

// в классе:
applyEvaluateResponse(data) {
  const { stateUpdate, speechText } = decodeEvaluateResponse(data, this.state.currentTopic);
  // setState принимает и объект, и функцию-апдейтер — отдаём как есть.
  this.setState(stateUpdate);
  speak(this.assistant, speechText);
}
```

И заменить все три вызова `this._handleEvaluateResponse(data)` → `this.applyEvaluateResponse(data)`.

- [ ] **Step 3: yarn build**

```bash
yarn build 2>&1 | tail -30
```

Expected: чисто.

- [ ] **Step 4: Коммит**

```bash
git add src/services/evaluationDispatch.js src/App.jsx
git commit -m "refactor(frontend): extract /evaluate response decoder to pure function"
```

#### 6c. Объединить async-handlers в App.jsx

- [ ] **Step 1: Добавить приватный хелпер в класс**

```javascript
// Общий код для всех async-обработчиков, дёргающих API:
// показать загрузку → вызвать api → применить ответ или показать ошибку.
async runApi(apiCall) {
  this.setState({ isLoading: true, lastError: null, answerBuffer: '' });
  try {
    const data = await apiCall();
    this.applyEvaluateResponse(data);
  } catch (err) {
    this.setState({ isLoading: false, lastError: err.message });
  }
}
```

- [ ] **Step 2: Переписать handlers**

```javascript
handleFinishAnswer() {
  if (this.state.status !== 'interview' || this.state.isLoading) return;
  const buffered = this.state.answerBuffer.trim();
  if (!buffered) {
    speak(this.assistant, 'Я не услышал ответ. Скажите его и затем «готово».');
    return;
  }
  return this.runApi(() => evaluateAnswer(this.sessionId, buffered));
}

handleNextQuestion() {
  if (this.state.isLoading) return;
  return this.runApi(() => skipQuestion(this.sessionId));
}

handleFinishInterview() {
  if (this.state.status !== 'interview' || this.state.isLoading) return;
  return this.runApi(() => finishInterview(this.sessionId));
}
```

**Важно:** `handleStartInterview` НЕ объединяется с этим хелпером — у него другая логика (меняет status, currentTopic, не использует applyEvaluateResponse). Оставить его как есть, только если в нём есть debug-log — убрать.

- [ ] **Step 3: yarn build**

```bash
yarn build 2>&1 | tail -30
```

Expected: чисто.

- [ ] **Step 4: Ручная проверка**

Запустить фронт и бэк:
```bash
# терминал 1
cd backend && uvicorn main:app --reload

# терминал 2
yarn start
```

Пройти один цикл: выбор темы → ответ голосом или текстом «готово» → должен прийти фидбек и следующий вопрос.

Если проверка успешна — продолжаем. Если что-то отвалилось — `git diff` и разбираемся, либо `git revert HEAD` и переделываем.

- [ ] **Step 5: Коммит**

```bash
git add src/App.jsx
git commit -m "refactor(frontend): consolidate async handlers via runApi helper"
```

---

### Task 7: README.md — фактическая сверка

**Files:**
- Modify: `README.md`

README в текущем виде в целом нормальный — структурированный, на русском, без AI-маркетинга. Задача — пройтись и проверить, что **факты в нём актуальны**.

- [ ] **Step 1: Сверить структуру проекта в README с реальностью**

В README есть блок «Структура проекта» (строки 257-286). Проверить, что:
- Все упомянутые файлы существуют.
- Не упомянуты несуществующие (например, `scenario-example.zip` — точно нет, проверить).
- Если в плане появились новые файлы (`backend/schemas.py`, `backend/logging_config.py`, `src/services/`) — добавить их в раздел.

Обновить блок:

```
├── src/                          # React-приложение (CRA)
│   ├── App.jsx                   # Корневой компонент: состояние и интеграция с Салютом
│   ├── api/interviewApi.js       # Вызовы FastAPI-бэкенда
│   ├── services/
│   │   ├── assistant.js          # Обёртка над @salutejs/client
│   │   └── evaluationDispatch.js # Декодер ответов /evaluate
│   ├── components/ErrorBoundary.jsx
│   ├── constants/topics.js
│   └── views/
│       ├── WelcomeView.jsx       # Экран выбора темы
│       ├── InterviewView.jsx     # Экран вопроса и ответа
│       └── ResultView.jsx        # Радар-чарт результатов
│
├── backend/                      # FastAPI-бэкенд
│   ├── main.py                   # Маршруты и middleware
│   ├── schemas.py                # Pydantic-модели запросов/ответов
│   ├── logging_config.py         # Настройка логирования
│   ├── llm_service.py            # Интеграция с GigaChat
│   ├── session_manager.py        # In-memory хранилище сессий
│   ├── questions.py              # Банк вопросов
│   ├── pyproject.toml            # Конфиг ruff
│   ├── requirements.txt
│   └── tests/
│
├── smartapp-backend/src/         # .sc-сценарии для SmartApp Code
├── scenario-new.zip              # Архив для загрузки в SmartApp Studio
├── docs/superpowers/             # Спеки и планы по итерациям проекта
├── .editorconfig
├── .env.sample                   # Шаблон фронт-переменных
├── backend/.env.example          # Шаблон бэк-переменных
└── CLAUDE.md
```

- [ ] **Step 2: Проверить эндпоинты**

В README перечислены `/start`, `/evaluate`, `/skip`, `/finish` — все есть в `main.py`. ОК.

Формат ответа `/evaluate` — должен совпасть с `EvaluateResponse` в `schemas.py`. Проверить ключи: `action`, `feedback`, `next_question`, `question_index`, `final_scores` — всё совпадает.

- [ ] **Step 3: Проверить голосовые команды**

В README перечислены команды («готово», «дальше», «сдаюсь», «закончить» и т.д.). Сверить с `smartapp-backend/src/sc/interview.sc` (НЕ менять .sc файлы — только сверить, что в README не упомянуто несуществующих команд).

```bash
grep -i 'готово\|дальше\|пропустить\|сдаюсь\|пас\|закончить\|хватит\|итоги' smartapp-backend/src/sc/*.sc | head -20
```

Если что-то в README не находится в .sc — пометить себе и убрать из README.

- [ ] **Step 4: Проверить раздел `Устранение проблем`**

Все четыре пункта актуальны (TTS, npm install, source maps, GigaChat SSL) — оставить.

- [ ] **Step 5: Коммит**

```bash
git add README.md
git commit -m "docs: sync README structure section with actual files"
```

---

### Task 8: CLAUDE.md — убрать ссылки на удалённые файлы

**Files:**
- Modify: `CLAUDE.md`

CLAUDE.md в целом свежий, но в нём остались ссылки на удалённые сущности.

- [ ] **Step 1: Найти и удалить упоминания `scenario-example.zip`**

В CLAUDE.md две строчки:
1. В разделе SmartApp Studio: «`scenario-example.zip` — наследие стартера, не используется.»
2. В разделе Conventions: «Актуальный архив сценариев — `scenario-new.zip`. `scenario-example.zip` — мёртвый артефакт стартера, можно удалить.»

Поскольку файл уже удалён (см. `git status`: `D scenario-example.zip`), эти упоминания устарели. Оставить только утверждение про `scenario-new.zip`:
- В первой строчке — убрать упоминание про `scenario-example.zip` целиком.
- Во второй — оставить только «Актуальный архив сценариев — `scenario-new.zip`.»

- [ ] **Step 2: Найти и удалить упоминание `PLAN.md`**

В CLAUDE.md в разделе «Текущее состояние»: «PLAN.md — устарел, не использовать как источник истины.»

`PLAN.md` тоже удалён (`D PLAN.md` в git status). Эту строчку убрать целиком — нет смысла говорить про несуществующий файл.

- [ ] **Step 3: Добавить ссылку на текущие спеки/планы**

В разделе «Текущее состояние» добавить:

```
**История изменений и спеки:** в `docs/superpowers/specs/` и `docs/superpowers/plans/`.
```

- [ ] **Step 4: Сверить остальные claims**

Прочитать CLAUDE.md целиком ещё раз. Особенно проверить:
- «Бэкенд-эндпоинты» — соответствуют `main.py` после рефакторинга.
- «Component tree» — после извлечения сервисов добавить упоминание `src/services/`.
- «Точка интеграции со Сбером — только App.jsx» — теперь корректнее «через `App.jsx` + `src/services/assistant.js`».

Подправить эти места.

- [ ] **Step 5: Коммит**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md — remove stale refs, reflect refactored services"
```

---

## Финальная проверка после всех задач

- [ ] **Step 1: Все тесты бэка зелёные**

```bash
cd backend && pytest -q
```

- [ ] **Step 2: Сборка фронта без ошибок**

```bash
yarn build
```

- [ ] **Step 3: Ручной end-to-end**

Поднять бэк (`uvicorn main:app --reload`) и фронт (`yarn start`).
Пройти полный цикл одной темы: 5 вопросов с ответами + финальный экран с радаром.

- [ ] **Step 4: Просмотреть git log**

```bash
git log --oneline main..
```

Должно быть ~12-13 коммитов с понятными сообщениями (`chore`, `style`, `docs`, `refactor`).
Если что-то намешано — НЕ rebase для учебного проекта (риск > польза).

---

## Открытые вопросы и принятые компромиссы

- `_advance_or_finalize` принимает `user_text`, который сейчас не используется — оставлен в сигнатуре на случай будущих логов с фрагментами ответа. Если жалко `noqa` — убрать.
- `runApi` хелпер во фронте сбрасывает `answerBuffer` всегда, даже если запрос упадёт. Это оставлено намеренно: если ошибка — пользователь начинает заново; если успех — буфер всё равно очищается.
- README не сокращали — он адекватный по объёму. Если в процессе сверки выяснится, что часть инструкций по SmartApp Studio устарела — обновить, а не удалять (ценная инфа для возврата к проекту через полгода).
