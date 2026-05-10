# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Голосовой квиз по Data Science для SmartApp в экосистеме Сбера (SberBox, Салют).

Пользователь голосом или кликом выбирает тему (Python / Classical ML / Deep Learning / NLP-CV), длину прохождения (5 / 10 / 20 / весь банк) и один из четырёх вариантов ответа на каждый вопрос. После ответа сразу показывается правильный вариант с пояснением. В конце — радар-чарт с долей правильных по темам.

**Текущее состояние:** офлайн-формат. Бэкенда нет, всё работает в собранном фронте без сетевых запросов — нужно для модерации SmartApp Studio.

**История изменений и спеки:** в `docs/superpowers/specs/` и `docs/superpowers/plans/`.

## Who I Am

Бэкендер/ML-инженер, не фронтендер. Фронтовые архитектурные решения принимай сам, не спрашивай. Спрашивать можно про клиентский UX-путь и про бэк/ML.

## Stack

**Frontend** (`/` корень): React (CRA, class-компонент App), `@salutejs/client`, `styled-components`.

- `chart.js` + `react-chartjs-2` — радар-чарт результатов.
- Файлы `.jsx` (не `.tsx`). TypeScript установлен, но не используется.
- Тестирование — `react-scripts test` (jest + RTL).

## Commands

```bash
yarn start        # dev-сервер на localhost:3000
yarn build        # production-билд
yarn test         # тесты в watch-режиме
yarn test --watchAll=false  # тесты одним прогоном
```

## Environment Setup

Корневой `.env` (фронт):
- `REACT_APP_TOKEN` — JWT auth token from SmartApp Studio (Profile → Service Settings → Auth Token)
- `REACT_APP_SMARTAPP` — имя приложения, оно же фраза голосового запуска
- `BROWSER=none` — отключает автоматическое открытие браузера на `yarn start`

После правки `.env` нужен полный рестарт dev-сервера (не просто hot reload).

## SmartApp Studio / Салют

- Голос пользователя → action → React через `@salutejs/client`.
- Обратно — через `assistant.sendData()` (action `SPEAK` → `.sc` отвечает через `$reactions.answer`).
- Актуальный архив сценариев — `scenario-new.zip` в корне; распакованные исходники — `smartapp-backend/src/`.

`.sc`-сценарии — тонкий NLU-слой: ловят русские формулировки и прокидывают на фронт actions:

| action.type      | Где принимается | Поля                |
|------------------|-----------------|---------------------|
| `CHOOSE_TOPIC`   | welcome         | `topic`             |
| `CHOOSE_LENGTH`  | length-pick     | `length` (число или 'all') |
| `PICK_OPTION`    | quiz            | `optionIndex` (0..3) |
| `DONT_KNOW`      | quiz            | —                   |
| `NEXT_QUESTION`  | feedback        | —                   |
| `FINISH_QUIZ`    | quiz / feedback | —                   |
| `START_AGAIN`    | results         | —                   |

Узел `Озвучить` (event `SPEAK`) остался — фронт через `speak()` отдаёт текст для TTS.

## Architecture

```
App (class component, владеет state и инстансом ассистента)
├── ErrorBoundary
├── WelcomeView         — 4 карточки тем + голосовой выбор
├── LengthPickView      — 4 карточки длины (5/10/20/Все) + голос
├── QuizView            — вопрос + 4 варианта; рисует и quiz, и feedback
└── ResultView          — радар-чарт + кнопки «Пройти ещё тему» / «Начать заново»
```

**Поток данных:**

1. `App` хранит весь state, который ведёт чистая state-машина `src/services/quizEngine.js`. Каждый action из ассистента или клика — вызов одной функции engine, результат идёт в `setState`.
2. Создание ассистента и TTS — в `src/services/assistant.js`. В `development` — `createSmartappDebugger`, в `production` — `createAssistant`.
3. Ассистент кидает `data`-события с `action`-объектами; `dispatchAssistantAction` мапит их на функции engine (CHOOSE_TOPIC → chooseTopic и т.п.).
4. `getStateForAssistant()` динамичен: отдаёт `item_selector` под текущий статус (4 темы на welcome, 4 длины на length-pick, 4 варианта ответа в quiz).
5. После каждого `setState` соответствующий handler озвучивает текст через `speak(assistant, text)` (в dev — фоллбек на `window.speechSynthesis`).

**Банк вопросов** — `src/data/questions.js`. Структура:

```js
QUESTIONS = {
  python: [{ id, text, options[4], correct (0..3), explanation }, ...],
  classical_ml:  [...],
  deep_learning: [...],
  nlp_cv:        [...],
};
```

Структурные тесты банка — `src/data/questions.test.js`. Перед коммитом новых вопросов прогнать `yarn test src/data/questions.test.js`.

**quizEngine API** (`src/services/quizEngine.js`) — чистые функции от state, без React/DOM/ассистента:

```
initial()                           → State
chooseTopic(state, topic)           → State (welcome → length-pick)
chooseLength(state, length, random?) → State (length-pick → quiz, сэмплит вопросы)
pickAnswer(state, optionIdx)        → State (quiz → feedback)
markUnknown(state)                  → State (quiz → feedback с dontKnow=true)
nextQuestion(state)                 → State (feedback → quiz | results)
finishTopic(state)                  → State (quiz/feedback → results)
restart(state)                      → State (results → welcome, радар сохраняется)
resetAll()                          → State (полный сброс)
```

Сэмплинг — Fisher-Yates с инжектируемым `random` (по умолчанию `Math.random`); тесты подменяют его на детерминированный.

## Conventions

- **Точка интеграции со Сбером — `App.jsx` + `src/services/assistant.js`.** Остальные компоненты про ассистента не знают.
- Тёмная тема, шрифты 24–32px — вывод на TV-экраны SberBox.
- `React.StrictMode` отключён в `src/index.jsx` намеренно — предотвращает двойную инициализацию ассистента.
- Ассистент инициализируется один раз в конструкторе `App` — не переносить в хуки или места с возможным ре-рендером.
- `item_selector.items` использует 1-based `number` — ассистент опирается на это для порядковых голосовых команд.
- Не коммитить `.env` (он в `.gitignore`).
- Любое изменение поведения квиза сопровождается тестом в `quizEngine.test.js`.
- Распакованные `.sc`-файлы хранятся в `smartapp-backend/src/` (коммитим), zip-пересборка — только для загрузки в SmartApp Studio.
- Общаться с пользователем нужно на русском языке.
