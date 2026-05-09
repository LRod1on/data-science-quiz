"""Общая настройка pytest для тестов бэкенда."""

import os
import sys
from pathlib import Path

# Кладём backend/ в sys.path, чтобы `from session_manager import ...` работал
# независимо от того, откуда запускают pytest (из корня репо или из backend/).
sys.path.insert(0, str(Path(__file__).parent.parent))

# llm_service на импорте читает GIGACHAT_*, в тестах их подменяем заглушками.
os.environ.setdefault("GIGACHAT_AUTH_KEY", "test-key")
os.environ.setdefault("GIGACHAT_MODEL", "GigaChat")
