"""Конфигурация логирования для бэкенда.

Все сообщения получают префикс с request_id, который проставляется
middleware на каждый HTTP-запрос. Логи без request_id (старт приложения,
фоновые задачи) выводятся с прочерком — иначе формат-строка падает на
отсутствующем поле.
"""

import logging


class _RequestIdFormatter(logging.Formatter):
    """Подставляет '-' вместо отсутствующего request_id в записи лога."""

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return super().format(record)


def setup_logging(level: int = logging.INFO) -> None:
    """Настроить root logger один раз на старте приложения.

    Идемпотентна: при повторном вызове (например, после reload в uvicorn)
    второй handler не добавляется, чтобы каждое сообщение не дублировалось.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(
        _RequestIdFormatter("%(asctime)s [%(levelname)s] request_id=%(request_id)s %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        root.addHandler(handler)
