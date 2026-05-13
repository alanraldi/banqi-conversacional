"""Logging estruturado JSON com PII masking — CloudWatch friendly."""

from __future__ import annotations

import json
import logging

from src.utils.pii import setup_pii_logging


class JSONFormatter(logging.Formatter):
    """Formata log records como JSON de uma linha — compatível com CloudWatch Logs Insights."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("agent_name", "session_id", "request_id", "duration_ms", "user_id", "step"):
            if hasattr(record, field):
                entry[field] = getattr(record, field)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Configura logging estruturado com PII masking."""
    numeric_level = getattr(logging, level.upper(), logging.INFO) if isinstance(level, str) else level

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    logging.root.handlers = [handler]
    logging.root.setLevel(numeric_level)

    for lib in ("httpx", "urllib3", "boto3", "botocore", "strands", "bedrock_agentcore"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    setup_pii_logging()
