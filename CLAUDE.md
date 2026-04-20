# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Goal

Голосовой тренажёр технического интервью для Data Science, работающий как SmartApp в экосистеме Сбера (SberBox, Салют).

Пользователь голосом выбирает тему (Python / Classical ML / Deep Learning / NLP-CV), проходит 5 вопросов, в конце — радар-чарт с оценками.

**Текущее состояние:** кодовая база — to-do-стартер, переделывается под новую задачу с нуля.

## Who I Am

Бэкендер/ML-инженер, не фронтендер. При ответах:
- Объясняй решения с обоснованием
- На архитектурных развилках предлагай варианты
- Не додумывай требования молча — задавай уточняющие вопросы

## Stack

**Frontend** (существующий): React (CRA), `@salutejs/client`, `styled-components`, `chart.js` + `react-chartjs-2`
- Файлы `.jsx` (не `.tsx`). TypeScript установлен, но не используется — не менять без явной задачи

**Backend** (планируется в `/backend`): Python 3.11+, FastAPI, httpx

**LLM**: Qwen через OpenRouter, модель задаётся через env-переменную (может меняться)

## Commands

```bash
yarn start        # Start dev server on localhost:3000
yarn build        # Production build
yarn test         # Run tests
yarn test --watchAll=false  # Run tests once (CI mode)
```

## Environment Setup

Copy `.env.sample` to `.env` before running. Required variables:
- `REACT_APP_TOKEN` — JWT auth token from SmartApp Studio (Profile → Service Settings → Auth Token)
- `REACT_APP_SMARTAPP` — SmartApp name as registered in SmartApp Studio (used as the voice launch phrase)
- `BROWSER=none` — prevents auto-opening browser on start

After changing `.env`, a full restart is required (not just hot reload).

## External Integrations

**SmartApp Studio / Салют:**
- Голос пользователя → `action_id` → React через `@salutejs/client`
- Обратно — через `assistant.sendData()`
- `scenario-example.zip` в корне — `.sc`-сценарии на серверах Сбера

**Открытый вопрос:** `.sc`-сценарии переписываются или остаются тонким роутером к FastAPI — решается в фазе 1 (см. `PLAN.md`).

## Architecture

**Data flow:**
1. `App` (class component) owns all state and the assistant instance
2. In `development`, uses `createSmartappDebugger` (requires token + smartapp name from `.env`); in `production` — `createAssistant`
3. The assistant fires `data` events with `action` objects that `dispatchAssistantAction` routes to state-mutating methods
4. `getStateForAssistant()` feeds current state back to the assistant as `item_selector` — enables ordinal voice references ("удали вторую"). The `ignored_words` list prevents content words from being misread as commands
5. `_send_action_value` / `sendData` sends feedback back to the assistant backend

**Component tree (стартовый, будет меняться):**
```
App (state + assistant logic)
└── TaskList (page layout)
    ├── AddTask (controlled form, local state for input)
    └── TaskItemList → TaskItem (checkbox toggles done state)
```

## Conventions

- **Точка интеграции со Сбером — только `App.jsx`.** Остальные компоненты не знают об ассистенте
- Тёмная тема, шрифты 24–32px — вывод на TV-экраны SberBox
- `React.StrictMode` отключён в `src/index.jsx` намеренно — предотвращает двойную инициализацию ассистента
- Ассистент инициализируется один раз в конструкторе `App` — не переносить в хуки или места с возможным ре-рендером
- `item_selector.items` использует 1-based `number` — ассистент опирается на это для порядковых голосовых команд
- Не коммитить `.env`
- Не трогать `scenario-example.zip` без явной команды
