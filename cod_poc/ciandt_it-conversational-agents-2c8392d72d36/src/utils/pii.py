"""PII masking for logs — Fix C6 (LGPD compliance).

DESIGN DECISION: We prefer false positives (masking too much) over false negatives
(leaking PII). An 11-digit number that is actually a protocol ID will be masked —
this is inconvenient for debugging but acceptable. A leaked CPF is a legal violation.
If you need to debug masked values, use the original data source (DB, API), not logs.
"""

from __future__ import annotations

import logging
import re

# Patterns: CPF, phone, email
# NOTE: CPF pattern may match non-CPF 11-digit sequences — see docstring above.
_PII_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}\b"), "***.***.***-**"),
    (re.compile(r"\b\+?\d{1,3}[\s-]?\(?\d{2}\)?[\s-]?\d{4,5}[-.\s]?\d{4}\b"), "***-****-****"),
    (re.compile(r"\b\d{10,13}\b"), "****-****"),  # unformatted phone (e.g. 5511999999999)
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "***@***.***"),
]


def mask_pii(text: str) -> str:
    """Mask CPF, phone and email in text."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class PIIMaskingFilter(logging.Filter):
    """Logging filter that masks PII before writing to any handler.

    Converts ALL args to string before masking to catch numeric PII
    (e.g., account numbers passed as int).
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_pii(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: mask_pii(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(mask_pii(str(a)) for a in record.args)
        return True


def setup_pii_logging() -> None:
    """Apply PII masking filter to all root logger handlers.

    Must be called AFTER setup_logging() — depends on handlers being configured.
    """
    pii_filter = PIIMaskingFilter()
    for handler in logging.root.handlers:
        handler.addFilter(pii_filter)
