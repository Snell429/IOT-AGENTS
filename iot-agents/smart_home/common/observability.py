from __future__ import annotations

import json
import logging
import sys
from collections import deque
from datetime import UTC, datetime
from typing import Any


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict):
            payload.update(event_data)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


class InMemoryLogHandler(logging.Handler):
    def __init__(self, max_entries: int = 200) -> None:
        super().__init__()
        self.records: deque[dict[str, Any]] = deque(maxlen=max_entries)

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event_data = getattr(record, "event_data", None)
        if isinstance(event_data, dict):
            entry.update(event_data)
        self.records.appendleft(entry)


def log_event(logger: logging.Logger, event: str, **fields: Any) -> None:
    logger.info(event, extra={"event_data": {"event": event, **fields}})


def configure_logging(service_name: str) -> InMemoryLogHandler:
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False

    stream_handler = next((handler for handler in root_logger.handlers if isinstance(handler, logging.StreamHandler)), None)
    if stream_handler is None:
        stream_handler = logging.StreamHandler(sys.stdout)
        root_logger.addHandler(stream_handler)
    stream_handler.setFormatter(JsonFormatter())

    memory_handler = next((handler for handler in root_logger.handlers if isinstance(handler, InMemoryLogHandler)), None)
    if memory_handler is None:
        memory_handler = InMemoryLogHandler()
        root_logger.addHandler(memory_handler)

    log_event(logging.getLogger(service_name), "service.logging_configured", service=service_name)
    return memory_handler
