"""Validação HMAC-SHA256 de assinaturas de webhooks.

Usa comparação timing-safe (hmac.compare_digest) para evitar timing attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def validate_webhook_signature(
    body: bytes,
    signature_header: str | None,
    app_secret: str,
) -> bool:
    """Valida assinatura X-Hub-Signature-256 do WhatsApp.

    Args:
        body: Corpo raw da requisição (bytes).
        signature_header: Valor do header X-Hub-Signature-256.
        app_secret: App secret do WhatsApp Business API.

    Returns:
        True se assinatura válida, False caso contrário.
    """
    if not signature_header:
        logger.warning("validate_signature: header ausente")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("validate_signature: formato inválido '%s'", signature_header[:20])
        return False

    received = signature_header[len("sha256="):]

    expected = hmac.new(
        app_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    # timing-safe compare — não vazar informação via tempo de resposta
    if hmac.compare_digest(expected, received):
        return True

    logger.warning("validate_signature: assinatura não confere")
    return False
