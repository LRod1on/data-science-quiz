# PLAN.md — Voice Interview Simulator

План разработки для переделки SmartApp-стартера to-do в голосовой симулятор технического интервью по Data Science. Рассчитан на MLE без опыта фронтенда.

## Как пользоваться этим файлом

Каждая фаза содержит:
- **Цель** — что получим на выходе
- **Инструмент** — обычный промпт Claude Code или `/feature-dev`
- **Промпт** — копипаста готовая
- **Проверка** — как убедиться что фаза прошла
- **Коммит** — что зафиксировать в git

Отмечай пройденные фазы галочкой. Не переходи к следующей, пока не проверил текущую.

## Архитектура (принято)

```
Голос → Сбер ASR → .sc (тонкий NLU) → React (view + fetch)
                                         ↓
                                   FastAPI /evaluate
                                         ↓
                                   OpenRouter (Qwen или др.)
                                         ↓
                                   JSON → React → sendData → .sc TTS → Сбер → колонка
```

**Обоснование:** `.sc` остаётся минимальным NLU-слоем (старт, следующий, сдаюсь, прокидка сырого ответа). Вся логика интервью — в FastAPI. React — тонкий view. Это даёт MLE максимум времени на Python-часть, где он силён.

---

## Фаза 0 — Подготовка и контекст ✅ ~15 мин

**Цель:** поправить CLAUDE.md под принятое решение, доставить недостающие зависимости, зафиксировать стартовую точку в git.

### 0.1 Обновить CLAUDE.md вручную

Открой `CLAUDE.md` в редакторе и внеси три изменения:

1. В разделе **External Integrations** замени блок "Открытый вопрос" на:
   ```
   **Архитектура (решение зафиксировано в PLAN.md):**
   - `.sc`-сценарии — тонкий NLU-слой: ловят команды (START_INTERVIEW, NEXT_QUESTION, GIVE_UP, END_INTERVIEW) и прокидывают сырой текст ответа как USER_ANSWER
   - Весь mozg — в Python FastAPI (папка `backend/`)
   - React вызывает FastAPI через fetch, FastAPI зовёт OpenRouter
   - TTS-озвучка feedback — через `sendData` обратно в `.sc`
   ```

2. В разделе **Conventions** замени строку *"Не трогать scenario-example.zip без явной команды"* на:
   ```
   - `scenario-example.zip` переписывается в фазе 1 на новый набор action-ов
   - Распакованные .sc-файлы хранятся в `smartapp-backend/` (коммитим), zip-пересборка — только для загрузки в SmartApp Studio
   ```

3. В разделе **Stack** замени подраздел про Frontend на:
   ```
   **Frontend** (`/` корень): React (CRA), @salutejs/client, styled-components
   - `chart.js` + `react-chartjs-2` — для радар-чарта результатов (установить в фазе 0.2)
   - Файлы .jsx (не .tsx). TypeScript установлен, но не используется
   ```

### 0.2 Доставить зависимости и распаковать сценарий

Запусти в терминале:

```bash
yarn add chart.js react-chartjs-2
unzip scenario-example.zip -d smartapp-backend
git add CLAUDE.md package.json yarn.lock smartapp-backend/
git commit -m "chore: prep for interview simulator rebuild"
```

### Проверка

- [+] CLAUDE.md больше не содержит слова "Открытый вопрос"
- [+] `yarn start` запускается (приложение всё ещё показывает to-do, это норма)
- [+] Папка `smartapp-backend/` существует и содержит `src/entryPoint.sc`

---

## Фаза 1 — Переписать .sc-сценарии ~30 мин

**Цель:** заменить to-do команды (`addNote`, `doneNote`, `deleteNote`) на сценарий интервью.

**Инструмент:** обычный Claude Code (не `/feature-dev` — код небольшой, агентам нечего исследовать).

### Промпт

```
Перепиши .sc-сценарии в smartapp-backend/ под голосовой симулятор технического
интервью по Data Science. Сейчас там to-do логика — её нужно полностью заменить.

Контекст работы сценариев:
- Пользователь говорит фразу
- Сбер распознаёт, .sc матчит паттерн, формирует action через addAction()
- React получает action через @salutejs/client assistant.on('data')
- Обратно React шлёт sendData(), .sc ловит через event!: <name>

Нужные action-команды для React (все обрабатываются через addAction из reply.js):

1. START_INTERVIEW { topic: "python" | "classical_ml" | "deep_learning" | "nlp_cv" }
   Ловится фразами типа: "начни интервью по питону", "давай классический ML",
   "начнём Deep Learning", "проверь меня по NLP". Тема распознаётся через паттерны.

2. USER_ANSWER { text: "<сырой текст того что сказал пользователь>" }
   Это дефолтный обработчик в состоянии активного интервью — ловит ЛЮБОЙ
   свободный текст, кроме явных управляющих команд ниже.
   Используй $AnyText::anyText как в старом addNote.sc, прокинь в action.

3. NEXT_QUESTION {} — фразы "следующий вопрос", "дальше", "пропусти"
4. GIVE_UP {} — фразы "сдаюсь", "не знаю", "пас"
5. END_INTERVIEW {} — фразы "закончим", "хватит", "стоп"
6. SHOW_RESULTS {} — фраза "покажи результаты"

Обратные события от React через sendData():
- event! SPEAK — React просит Сбер озвучить текст (в eventData.text).
  .sc должен сделать $reactions.answer({value: eventData.text})

Что конкретно сделать:
1. Удали src/sc/addNote.sc, deleteNote.sc, doNote.sc, noteDone.sc
2. Удали старые функции addNote/doneNote/deleteNote из src/js/actions.js,
   замени на startInterview/userAnswer/nextQuestion/giveUp/endInterview/showResults
3. Создай src/sc/interview.sc со всеми вышеописанными состояниями
4. Обнови entryPoint.sc: убери require старых файлов, подключи interview.sc.
   Замени фразу запуска "my canvas test" на "симулятор интервью"
   (или попроси меня указать точное имя смартапа).
5. Приветственный ответ в state: Start сделай:
   "Привет! Я проведу с тобой интервью по Data Science.
    Выбери тему: Python, Classical ML, Deep Learning или NLP и Computer Vision."

Файлы reply.js и getters.js НЕ трогай — они универсальные.

Я не знаком с JAICP/.sc синтаксисом — если по ходу увидишь, что какой-то из
action-ов технически нереализуем из-за ограничений языка, останови меня
и объясни проблему словами, а не гадай.
```

### Проверка

- [ ] Файлы `smartapp-backend/src/sc/interview.sc` и обновлённый `actions.js` существуют
- [ ] Старые `addNote.sc`, `deleteNote.sc`, `doNote.sc`, `noteDone.sc` удалены
- [ ] В `entryPoint.sc` нет `require` удалённых файлов

### Коммит

```bash
git add smartapp-backend/
git commit -m "feat(smartapp): rewrite .sc scenarios for interview flow"
```

**Важно:** код на SmartApp Studio мы зальём позже, в фазе 5. Пока просто фиксируем исходники в репозитории.

---

## Фаза 2 — Переделка фронтенда (feature-dev) ~1.5 часа

**Цель:** заменить to-do UI на три экрана интервью, обновить `dispatchAssistantAction` под новые команды, добавить fetch к будущему FastAPI.

**Инструмент:** `/feature-dev`. Это та фаза где плагин реально полезен — нужно сохранить интеграцию с `@salutejs/client`, а ты в ней плавать.

### Запуск

```
claude
/plugin install feature-dev@claude-plugin-directory
/feature-dev
```

Когда попросит описать фичу, вставь:

### Промпт для feature-dev

```
Переделать существующий to-do стартер в голосовой симулятор технического
интервью для Data Science. Сохранить интеграцию с @salutejs/client в App.jsx,
полностью переписать UI и логику.

СОСТОЯНИЕ (в App state):
- status: 'welcome' | 'interview' | 'results'
- currentTopic: 'python' | 'classical_ml' | 'deep_learning' | 'nlp_cv' | null
- questionIndex: number (0..4), questionText: string
- isLoading: boolean (ждём ответ FastAPI)
- isListening: boolean (ассистент слушает ответ)
- radarScores: { python, classical_ml, deep_learning, nlp_cv } со значениями 0..10
- lastError: string | null

ВХОДЯЩИЕ action-ы от .sc (обновить dispatchAssistantAction):
- START_INTERVIEW { topic } → status='interview', обнулить индекс, запросить
  первый вопрос у FastAPI через POST /start
- USER_ANSWER { text } → отправить POST /evaluate { session_id, topic, text },
  обработать ответ: обновить questionText или перейти в results
- NEXT_QUESTION → POST /next
- GIVE_UP → POST /skip
- END_INTERVIEW → status='welcome'
- SHOW_RESULTS → status='results'

ИНТЕГРАЦИЯ С FASTAPI:
- Базовый URL из env: process.env.REACT_APP_BACKEND_URL (добавить в .env.sample)
- Все вызовы — через простой fetch с JSON. Обработчик ошибок: если fetch
  упал, показать lastError и вернуть статус welcome, не падать молча
- session_id — генерируется один раз при монтировании App (uuid или
  crypto.randomUUID), хранится в state

ОБРАТНЫЙ КАНАЛ К АССИСТЕНТУ:
- Когда FastAPI вернул feedback_text, React вызывает
  this.assistant.sendData({ action: { action_id: 'SPEAK' }, eventData: { text: feedback_text } })
  чтобы Сбер озвучил. Это уже настроено в .sc через event!: SPEAK
- getStateForAssistant должен возвращать item_selector с темами 1..4
  (Python, Classical ML, Deep Learning, NLP/CV) когда status='welcome',
  чтобы можно было сказать "выбери вторую"

ЭКРАНЫ:
- WelcomeView: заголовок + 4 большие кнопки-карточки тем. По клику отправляет
  sendData с action START_INTERVIEW
- InterviewView: бейдж "Deep Learning • 2/5" сверху, крупный текст вопроса
  по центру (мин. 28px), пульсирующий кружок-индикатор микрофона внизу
  (анимация через styled-components), резервные кнопки "Следующий" и "Сдаюсь"
  которые дублируют голосовые команды через sendData
- ResultView: радар-чарт через react-chartjs-2 (компонент Radar), 4 оси,
  шкала 0..10, тёмный фон (rgba сетка белая), кнопка "Начать заново"

ОГРАНИЧЕНИЯ:
- Тёмная тема: фон #292929 (уже есть в App.css), шрифты 24–32px — вывод на TV
- Файлы .jsx (не .tsx)
- Не ломать логику инициализации ассистента в конструкторе App — она одноразовая
- StrictMode намеренно отключён в index.jsx (чтобы ассистент не создавался дважды) — не включать обратно
- Удалить старые файлы: src/pages/TaskList.jsx, src/components/AddTask.jsx,
  TaskItemList.jsx, TaskItem.jsx
- ErrorBoundary на уровне App, чтобы краш компонента не убивал ассистента

Я не фронтендер — на фазе Discovery задавай уточняющие вопросы,
на Architecture предлагай 2-3 варианта с trade-offs, не угадывай молча.
Если на каком-то шаге заметишь, что это конфликтует с @salutejs/client API —
останови и объясни.
```

### Проверка

- [ ] `yarn start` запускается без ошибок в консоли (ошибки `fetch failed` к бэкенду — ок, бэкенда ещё нет)
- [ ] На welcome экране видны 4 темы
- [ ] В DevTools Network видны попытки POST на `REACT_APP_BACKEND_URL`
- [ ] Старые компоненты to-do удалены
- [ ] `.env.sample` содержит `REACT_APP_BACKEND_URL=`

### Коммит

```bash
git add .
git commit -m "feat: rebuild frontend as interview simulator"
```

---

## Фаза 3 — Бэкенд-скелет ~30 мин

**Цель:** создать FastAPI-каркас и менеджер сессий.

**Инструмент:** обычный Claude Code. Кода ещё нет, feature-dev здесь бесполезен.

### Подготовка

```bash
mkdir backend
cd backend
claude
```

### Промпт 3.1 — каркас

```
Инициализируй Python-проект для FastAPI-бэкенда в текущей папке.

requirements.txt:
- fastapi
- uvicorn[standard]
- pydantic>=2
- httpx
- openai (через него ходим в OpenRouter по совместимому API)
- python-dotenv
- pytest
- pytest-asyncio

.env.example:
- OPENROUTER_API_KEY=
- OPENROUTER_MODEL=qwen/qwen-2.5-72b-instruct
- CORS_ORIGINS=http://localhost:3000

.gitignore: .env, __pycache__, .pytest_cache, *.pyc, .venv

main.py:
- FastAPI app с CORS middleware (origins из CORS_ORIGINS)
- Базовый логер (logging, level INFO, формат с timestamp и request_id)
- POST /health → {"status": "ok"}
- Заглушки (возвращают 501 Not Implemented пока): POST /start, POST /evaluate,
  POST /next, POST /skip
- Глобальный exception handler, который логирует трейс и возвращает
  {"error": str, "request_id": str} с кодом 500

README.md:
- Как создать venv и поставить зависимости
- Как скопировать .env.example в .env и заполнить
- Команда запуска: uvicorn main:app --reload --port 8000

Python 3.11+. Тайпхинты везде. Проверь синтаксис, не запускай.
```

### Коммит

```bash
git add .
git commit -m "feat(backend): scaffold FastAPI app"
```

### Промпт 3.2 — сессии

```
Создай session_manager.py в текущей папке.

Pydantic-модель SessionState (pydantic v2):
- session_id: str
- topic: Literal["python", "classical_ml", "deep_learning", "nlp_cv"] | None
- question_index: int (0..4), default 0
- current_question: str | None
- per_question_scores: list[float]  # 0..10, заполняется по мере ответов
- final_scores: dict[str, float]  # среднее по каждой пройденной теме
- chat_history: list[dict]  # формат OpenAI messages: {"role", "content"}
- started_at: datetime, last_activity_at: datetime

Класс SessionManager:
- In-memory dict[str, SessionState] (single-instance, потокобезопасность не нужна)
- Методы: get_or_create(session_id), update(session_id, **fields),
  reset_topic(session_id), finalize_topic(session_id) — считает среднее и
  кладёт в final_scores
- Метод cleanup_stale(max_age_minutes=60) — удаляет сессии без активности
  больше часа (вызывается из фонового таска или вручную, реализацию фона
  пока не добавляй — только метод)

pytest-тесты в tests/test_session.py:
1. Создание сессии возвращает новую, повторный вызов get_or_create
   с тем же id — ту же
2. finalize_topic правильно считает среднее и очищает per_question_scores
3. cleanup_stale удаляет старую сессию и не трогает свежую (патч datetime
   через monkeypatch)

Запустить не надо — только напиши код. Проверю pytest сам.
```

### Проверка

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполни OPENROUTER_API_KEY
uvicorn main:app --reload --port 8000
# в другом терминале:
curl http://localhost:8000/health
# должно вернуть {"status": "ok"}
pytest
# тесты сессий должны пройти
```

- [ ] `/health` отвечает 200
- [ ] `pytest` зелёный
- [ ] `/start`, `/evaluate` пока возвращают 501 — это ок

### Коммит

```bash
git add .
git commit -m "feat(backend): session manager with in-memory storage"
```

---

## Фаза 4 — LLM + вебхук (feature-dev) ~1.5 часа

**Цель:** подключить OpenRouter, реализовать эндпоинты `/start` и `/evaluate`, собрать всё вместе.

**Инструмент:** `/feature-dev`. Сейчас в `backend/` уже есть код, `code-explorer` будет его читать.

### Запуск

```bash
cd backend
claude
/feature-dev
```

### Промпт

```
Реализовать LLM-слой и логику интервью в существующем FastAPI-бэкенде.

LLM-СЕРВИС (новый файл llm_service.py):

async def start_interview(topic, session_id) -> StartResult
async def evaluate_answer(topic, question, user_answer, history) -> EvaluationResult

Где StartResult:
- first_question: str
- pronounce_text: str  # что сказать голосом ("Отлично, начинаем. Вопрос 1...")

EvaluationResult:
- score: float | None  # 0..10 если вопрос завершён, иначе None
- feedback: str  # что озвучить пользователю
- is_question_complete: bool  # переходим к следующему
- next_question: str | None  # если is_question_complete=True
- clarifying_question: str | None  # если is_question_complete=False

OpenRouter через openai SDK:
- base_url="https://openrouter.ai/api/v1", api_key из env
- Модель из env (OPENROUTER_MODEL)
- Таймаут 30 сек
- System prompt: "Ты Senior Data Scientist, проводишь техническое интервью
  по теме {topic}. Вопросы уровня senior. Оценивай ответы по шкале 0-10
  где 10 это идеальный senior-ответ. Если ответ неполный — задай один
  уточняющий вопрос. Если ответ исчерпывающий или кандидат сдался —
  оцени и переходи к следующему. Отвечай СТРОГО валидным JSON без
  markdown-ограждений."

НАДЁЖНЫЙ ПАРСИНГ JSON (критично):
Qwen и некоторые модели OpenRouter не гарантируют валидный JSON и иногда
заворачивают его в ```json ... ```. Стратегия:
1. Попробовать json.loads
2. Если упало — regex-экстракт первого {...} блока, json.loads
3. Если упало — один retry вызова LLM с system "верни ТОЛЬКО JSON,
   никакого markdown, никаких пояснений"
4. Если опять упало — вернуть fallback EvaluationResult со score=None,
   is_question_complete=False, feedback="Извини, я не расслышал,
   повтори ответ", clarifying_question="Можешь переформулировать?"
5. Результат валидировать через pydantic перед возвратом

БАНК ВОПРОСОВ (новый файл questions.py):
Плоский dict[topic, list[str]] с 15-20 senior-вопросами на каждую из 4 тем.
Используется только в start_interview — LLM берёт оттуда первый вопрос,
дальнейшие генерирует сам на основе ответов. Темы и качество вопросов —
сделай разнообразными (теория, практика, edge cases).

ЭНДПОИНТЫ (обнови main.py):

POST /start { session_id, topic } → { question, pronounce_text }
- get_or_create сессия, установить topic, вызвать llm_service.start_interview
- Обновить current_question в сессии, сбросить question_index

POST /evaluate { session_id, text } → {
    action: "CONTINUE" | "NEXT_QUESTION" | "TOPIC_COMPLETE" | "ERROR",
    feedback: str,
    next_question: str | null,
    question_index: int,
    final_scores: dict | null  # только когда action=TOPIC_COMPLETE
  }
- Достать сессию, вызвать evaluate_answer с историей
- Если is_question_complete: сохранить score в per_question_scores,
  увеличить question_index
- Если question_index == 5: finalize_topic, вернуть action=TOPIC_COMPLETE
  с final_scores (объект со всеми 4 темами, непройденные = 0)
- Иначе CONTINUE (если ещё уточняется текущий) или NEXT_QUESTION
- Обновить chat_history в сессии
- ВСЕ ошибки LLM ловить и возвращать action=ERROR с дружелюбным feedback,
  сессию не ломать

POST /skip { session_id } — эквивалент "сдаюсь": ставит score=0 текущему
вопросу и переходит к следующему через ту же логику что /evaluate

ЛОГИРОВАНИЕ (критично для дебага интеграции):
Каждый /evaluate логировать: session_id, topic, question_index,
user_text (первые 100 символов), llm_latency_ms, score, action.
Формат: single-line JSON в stdout.

ТЕСТЫ (tests/):
- test_llm_parsing.py: фиктивные ответы LLM (валидный JSON, JSON в markdown,
  мусор) → проверить что парсер корректно извлекает или возвращает fallback.
  LLM замокать через monkeypatch
- test_endpoints.py: /start и /evaluate через FastAPI TestClient,
  с замоканным llm_service. Проверить что состояние сессии меняется
  правильно и ответ соответствует схеме

Я MLE, с FastAPI знаком. На фазе Discovery уточняй про формат истории
сообщений и структуру банка вопросов. На Architecture предложи варианты
работы с rate-лимитами OpenRouter — нужен backoff или достаточно таймаута.
```

### Проверка

Мануальный тест через curl:

```bash
# старт
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-1", "topic": "python"}'

# ответ
curl -X POST http://localhost:8000/evaluate \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-1", "text": "декоратор это функция которая оборачивает другую функцию"}'
```

- [ ] `/start` возвращает вопрос
- [ ] `/evaluate` возвращает feedback + либо follow-up либо новый вопрос
- [ ] В логах видно llm_latency_ms < 30000
- [ ] `pytest` зелёный

### Коммит

```bash
git add .
git commit -m "feat(backend): LLM service and interview endpoints"
```

---

## Фаза 5 — Интеграция и загрузка в Сбер ~1 час

**Цель:** проверить весь стек вместе, залить `.sc` в SmartApp Studio, отладить через дебаггер.

**Инструмент:** руки.

### 5.1 Проверка локально

Терминал 1:
```bash
cd backend && source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

Терминал 2:
```bash
# в корне проекта — REACT_APP_BACKEND_URL=http://localhost:8000 уже в .env
yarn start
```

Откроется SmartApp Debugger от `@salutejs/client`. Скажи в него "начни Python" — должен прийти action `START_INTERVIEW`, React дёрнуть `/start`, показать вопрос.

### 5.2 Залить сценарий в SmartApp Studio

```bash
cd smartapp-backend
zip -r ../scenario-new.zip . -x "*.DS_Store"
```

В SmartApp Studio → твой проект → Code → загрузи `scenario-new.zip`. Дождись билда.

### 5.3 FastAPI наружу через ngrok

```bash
ngrok http 8000
# скопируй https:// URL
```

Положи этот URL в `REACT_APP_BACKEND_URL` и перезапусти `yarn start`.

### 5.4 Тест с устройства

Открой приложение на SberBox или в эмуляторе в Studio. Запусти фразой "Запусти симулятор интервью". Пройди один вопрос.

### Чеклист интеграции

- [ ] Голосовая команда старта доходит до React (action `START_INTERVIEW` в консоли)
- [ ] React дёргает FastAPI (в логах бэкенда виден POST /start)
- [ ] Вопрос отображается в UI
- [ ] Ответ голосом прилетает как `USER_ANSWER` с непустым text
- [ ] Feedback озвучивается Сбером (через event SPEAK)
- [ ] После 5 вопросов показывается радар-чарт

### Коммит

```bash
git add .
git commit -m "chore: integration verified"
git tag v0.1.0-mvp
```

---

## Что дальше (не в этом плане)

- Персистентность сессий (Redis / sqlite) — сейчас in-memory
- Деплой FastAPI (Railway / Fly / свой VPS) — ngrok только для теста
- Расширение банка вопросов
- Защита эндпоинтов (API-key от Сбера в заголовке)
- Аналитика: какие темы и вопросы заваливают чаще

---

## Памятки

**Если застрял на фазе с feature-dev:** в Discovery-фазе плагин задаёт вопросы. Нормальные ответы: "не знаю, предложи варианты", "опиши trade-offs", "покажи пример". Плохой ответ — молчать или гадать.

**Если Claude Code что-то ломает:** `git diff` → если страшно, `git restore .`. Каждая фаза заканчивается коммитом специально для этого.

**Если `.sc` не матчит голосовые команды:** проблема почти всегда в regex-паттернах. В Studio есть "Тестирование" — там видно какое состояние сработало.

**Если OpenRouter возвращает мусор:** попробуй другую модель в `OPENROUTER_MODEL`. `anthropic/claude-3.5-sonnet` стабильнее в JSON, но дороже. `meta-llama/llama-3.1-70b-instruct` дешевле Qwen.