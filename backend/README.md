# Interview Trainer — Backend

FastAPI-сервис для голосового тренажёра технических интервью.

## Установка

```bash
python3.11 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка окружения

```bash
cp .env.example .env
```

Заполнить `.env`:

| Переменная | Описание |
|---|---|
| `OPENROUTER_API_KEY` | API-ключ OpenRouter |
| `OPENROUTER_MODEL` | Модель (по умолчанию `qwen/qwen-2.5-72b-instruct`) |
| `CORS_ORIGINS` | Разрешённые origins через запятую (по умолчанию `http://localhost:3000`) |

## Запуск

```bash
uvicorn main:app --reload --port 8000
```

API будет доступно на `http://localhost:8000`.

## Тесты

```bash
pytest
```
