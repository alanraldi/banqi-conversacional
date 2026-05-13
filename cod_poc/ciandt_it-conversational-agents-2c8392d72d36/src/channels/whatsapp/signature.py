"""WhatsApp webhook signature validation — Fix C7.

Validates X-Hub-Signature-256 header using HMAC-SHA256.
NEVER returns True unconditionally.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)


def validate_webhook_signature(
    payload_body: bytes,
    signature_header: str | None,
    app_secret: str,
) -> bool:
    """Validate Meta webhook X-Hub-Signature-256 header.

    Uses hmac.compare_digest for timing-safe comparison.
    Returns False (rejects) if any validation step fails.
    """
    if not signature_header:
        logger.warning("Webhook rejected: missing X-Hub-Signature-256 header")
        return False

    if not app_secret:
        logger.error("Webhook rejected: WHATSAPP_APP_SECRET not configured")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("Webhook rejected: invalid signature format")
        return False

    expected_sig = signature_header[7:]
    computed_sig = hmac.HMAC(
        app_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed_sig, expected_sig):
        logger.warning("Webhook rejected: HMAC signature mismatch")
        return False

    return True
