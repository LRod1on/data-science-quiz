# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Голосовой тренажёр технического интервью для Data Science, работающий как SmartApp в экосистеме Сбера (SberBox, Салют).

Пользователь голосом выбирает тему (Python / Classical ML / Deep Learning / NLP-CV), проходит 5 вопросов, в конце — радар-чарт с оценками.

**Текущее состояние:** v1 рабочая. Фронт (`src/views/{Welcome,Interview,Result}View.jsx`), бэк (`backend/`) и `.sc`-сценарии (`smartapp-backend/`) собраны и протестированы вручную.

**История изменений и спеки:** в `docs/superpowers/specs/` и `docs/superpowers/plans/`.

## Who I Am

Бэкендер/ML-инженер, не фронтендер. При ответах:
- Объясняй решения с обоснованием
- На архитектурных развилках предлагай варианты
- Не додумывай требования молча — задавай уточняющие вопросы

## Stack

**Frontend** (`/` корень): React (CRA), @salutejs/client, styled-components
- `chart.js` + `react-chartjs-2` — для радар-чарта результатов
- Файлы .jsx (не .tsx). TypeScript установлен, но не используется

**Backend** (`/backend`): Python 3.11+, FastAPI, httpx, pydantic v2.
Линтер/форматтер — `ruff` (конфиг в `backend/pyproject.toml`).

**LLM**: GigaChat (Sber). Авторизация по `GIGACHAT_AUTH_KEY` (base64 Client_ID:Client_Secret), модель — `GIGACHAT_MODEL` (`GigaChat` / `GigaChat-Pro` / `GigaChat-Max`). HTTP-клиент идёт с `verify=False` — у Сбера российский CA, не лежащий в дефолтном bundle Python.

## Commands

```bash
yarn start        # Start dev server on localhost:3000
yarn build        # Production build
yarn test         # Run tests
yarn test --watchAll=false  # Run tests once (CI mode)
```

## Environment Setup

Конфиги разнесены: фронт читает корневой `.env`, бэк — `backend/.env` (см. `load_dotenv(Path(__file__).parent / ".env")` в `backend/main.py`). Шаблоны: `.env.sample` и `backend/.env.example`.

Корневой `.env` (фронт):
- `REACT_APP_TOKEN` — JWT auth token from SmartApp Studio (Profile → Service Settings → Auth Token)
- `REACT_APP_SMARTAPP` — SmartApp name as registered in SmartApp Studio (фраза голосового запуска)
- `REACT_APP_BACKEND_URL` — куда фронт стучит за интервью (по умолчанию `http://localhost:8000`)
- `BROWSER=none` — prevents auto-opening browser on start

`backend/.env` (бэк):
- `GIGACHAT_AUTH_KEY` — base64(Client_ID:Client_Secret) для GigaChat
- `GIGACHAT_MODEL` — имя модели (`GigaChat` / `GigaChat-Pro` / `GigaChat-Max`)
- `CORS_ORIGINS` — список разрешённых origin-ов через запятую

After changing `.env`, a full restart is required (not just hot reload).

## External Integrations

**SmartApp Studio / Салют:**
- Голос пользователя → `action_id` → React через `@salutejs/client`
- Обратно — через `assistant.sendData()` (action `SPEAK` → `.sc` отвечает через `$reactions.answer`)
- Актуальный архив сценариев — `scenario-new.zip` в корне; распакованные исходники — `smartapp-backend/src/`.

**Архитектура:**
- `.sc`-сценарии — тонкий NLU-слой: ловят команды (`START_INTERVIEW`, `USER_ANSWER`, `FINISH_ANSWER`, `NEXT_QUESTION`, `GIVE_UP`, `END_INTERVIEW`, `SHOW_RESULTS`) и прокидывают сырой текст ответа как `USER_ANSWER`
- Весь mozg — в Python FastAPI (`backend/`)
- React вызывает FastAPI через `fetch` (`src/api/interviewApi.js`), FastAPI зовёт GigaChat (`backend/llm_service.py`)
- TTS-озвучка feedback — через `src/services/assistant.js` (`speak()` обёртка над `assistant.sendData({action: {action_id: 'SPEAK'}, ...})`); в .sc обрабатывается узлом `Озвучить`

## Architecture

**Data flow:**
1. `App` (class component) владеет состоянием и инстансом ассистента, хранит `sessionId` (UUID) и буфер ответа
2. Создание ассистента и TTS живут в `src/services/assistant.js`. В `development` — `createSmartappDebugger` (нужны `REACT_APP_TOKEN` + `REACT_APP_SMARTAPP`), в `production` — `createAssistant`
3. Ассистент кидает `data`-события с `action`-объектами; `dispatchAssistantAction` диспатчит их в обработчики
4. `getStateForAssistant()` отдаёт `item_selector` (только на welcome-экране) — нужен для порядковых голосовых ссылок («первый», «второй»). `ignored_words` фильтрует слова-наполнители
5. По буферу: фрагменты речи копятся в `state.answerBuffer` через `USER_ANSWER`; команда «готово» (`FINISH_ANSWER`) шлёт буфер на `/evaluate`
6. Ответ `/evaluate` декодируется чистой функцией `decodeEvaluateResponse` из `src/services/evaluationDispatch.js` в патч для `setState` и текст для озвучки
7. TTS — `speak(assistant, text)` из `services/assistant.js` (в dev — фоллбек на `window.speechSynthesis`)

**Component tree:**
```
App (sessionId, state, assistant)
├── ErrorBoundary
├── WelcomeView         — карточки 4 тем + голосовой выбор
├── InterviewView       — вопрос, буфер ответа, кнопки «Готово/Следующий/Закончить»
└── ResultView          — radar-чарт по 4 темам, кнопка «Начать заново»
```

**Бэкенд-эндпоинты** (`backend/main.py`):
- `POST /start` — начать сессию по теме (выбирает первый вопрос из банка)
- `POST /evaluate` — оценить накопленный ответ; LLM может либо задать уточняющий (`CONTINUE`), либо завершить вопрос и выдать следующий (`NEXT_QUESTION`), либо завершить тему (`TOPIC_COMPLETE`)
- `POST /skip` — пропустить вопрос, начислив балл за уже сказанное в буфере истории (через `score_from_history`)
- `POST /finish` — досрочно завершить тему, начислив балл за текущий вопрос; финализирует усреднение

Тела запросов/ответов типизированы Pydantic-схемами в `backend/schemas.py`.
Сессии in-memory (`session_manager.py`). Балл за тему — среднее по `per_question_scores` (всегда 5 значений). `final_scores` накапливаются между темами в одной сессии.

## Conventions

- **Точка интеграции со Сбером — `App.jsx` + `src/services/assistant.js`.** Остальные компоненты не знают об ассистенте
- Тёмная тема, шрифты 24–32px — вывод на TV-экраны SberBox
- `React.StrictMode` отключён в `src/index.jsx` намеренно — предотвращает двойную инициализацию ассистента
- Ассистент инициализируется один раз в конструкторе `App` — не переносить в хуки или места с возможным ре-рендером
- `item_selector.items` использует 1-based `number` — ассистент опирается на это для порядковых голосовых команд
- Не коммитить `.env` (ни корневой `.env`, ни `backend/.env` — оба в `.gitignore`)
- Актуальный архив сценариев — `scenario-new.zip`
- Распакованные .sc-файлы хранятся в `smartapp-backend/src/` (коммитим), zip-пересборка — только для загрузки в SmartApp Studio
- `session_id` — UUID, генерируется один раз в конструкторе `App` и переиспользуется между темами в одной сессии (это даёт накопление `final_scores`)
- Общаться с пользователем нужно на русском языке
