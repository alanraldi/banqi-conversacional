"""Structured JSON logging with PII masking."""

from __future__ import annotations

import json
import logging

from src.utils.pii import setup_pii_logging


class JSONFormatter(logging.Formatter):
    """Outputs log records as single-line JSON — CloudWatch friendly."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("agent_name", "session_id", "request_id", "duration_ms"):
            if hasattr(record, field):
                entry[field] = getattr(record, field)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure structured logging with PII masking."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    logging.root.handlers = [handler]
    logging.root.setLevel(level)

    # Reduce noise from external libs
    for lib in ("httpx", "urllib3", "boto3", "botocore"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    # Apply PII masking to all handlers
    setup_pii_logging()
