"""Unit tests for src/channels/whatsapp/signature.py — zero AWS dependencies."""

from __future__ import annotations

import hashlib
import hmac

from src.channels.whatsapp.signature import validate_webhook_signature


def _make_signature(payload: bytes, secret: str) -> str:
    sig = hmac.HMAC(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


class TestValidateWebhookSignature:
    """C7: HMAC-SHA256 webhook signature validation."""

    def test_valid_signature(self):
        payload = b'{"test": true}'
        secret = "my-secret"
        header = _make_signature(payload, secret)
        assert validate_webhook_signature(payload, header, secret) is True

    def test_missing_header(self):
        assert validate_webhook_signature(b"data", None, "secret") is False

    def test_empty_secret(self):
        assert validate_webhook_signature(b"data", "sha256=abc", "") is False

    def test_invalid_format(self):
        assert validate_webhook_signature(b"data", "md5=abc", "secret") is False

    def test_wrong_signature(self):
        assert validate_webhook_signature(b"data", "sha256=wrong", "secret") is False

    def test_tampered_payload(self):
        secret = "my-secret"
        header = _make_signature(b"original", secret)
        assert validate_webhook_signature(b"tampered", header, secret) is False
