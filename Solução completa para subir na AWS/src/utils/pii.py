"""PII masking para logs — conformidade LGPD.

Preferimos falsos positivos (mascarar demais) a falsos negativos (vazar PII).
"""

from __future__ import annotations

import logging
import re

_PII_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b\d{3}[.\s]?\d{3}[.\s]?\d{3}[-.\s]?\d{2}\b"), "***.***.***-**"),
    (re.compile(r"\b\+?\d{1,3}[\s-]?\(?\d{2}\)?[\s-]?\d{4,5}[-.\s]?\d{4}\b"), "***-****-****"),
    (re.compile(r"\b\d{10,13}\b"), "****-****"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "***@***.***"),
    (re.compile(r"\b\d{5}-?\d{3}\b"), "*****-***"),
    (re.compile(r"\bagencia[:\s]+\d{4,6}(-\d)?\b", re.IGNORECASE), "agencia: ****"),
    (re.compile(r"\bconta[:\s]+\d{4,12}-?\d\b", re.IGNORECASE), "conta: ****-*"),
]


def mask_cpf(cpf: str) -> str:
    """Mascara CPF deixando apenas os últimos 3 dígitos visíveis."""
    digits = re.sub(r"\D", "", cpf)
    if len(digits) != 11:
        return "***.***.***-**"
    return f"***.***.*{digits[8:10]}-{digits[10:]}"


def mask_phone(phone: str) -> str:
    """Mascara número de telefone, mantendo apenas o código do país."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 2:
        return f"+{digits[:2]}-***-****-****"
    return "***-****-****"


def mask_email(email: str) -> str:
    """Mascara email preservando apenas o domínio."""
    match = re.match(r"[^@]+@(.+)", email)
    if match:
        return f"***@{match.group(1)}"
    return "***@***.***"


def mask_bank_account(account: str) -> str:
    """Mascara número de conta bancária, preservando últimos 4 dígitos."""
    digits = re.sub(r"[-\s]", "", account)
    if len(digits) > 4:
        return f"****{digits[-4:]}"
    return "****"


def mask_all(text: str) -> str:
    """Mascara todos os padrões de PII em um texto."""
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class PIIMaskingFilter(logging.Filter):
    """Logging filter que mascara PII antes de gravar em qualquer handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_all(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: mask_all(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, tuple):
                record.args = tuple(mask_all(str(a)) for a in record.args)
        return True


def setup_pii_logging() -> None:
    """Aplica PIIMaskingFilter em todos os handlers do root logger."""
    pii_filter = PIIMaskingFilter()
    for handler in logging.root.handlers:
        handler.addFilter(pii_filter)
