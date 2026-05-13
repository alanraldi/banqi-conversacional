"""WhatsApp Business API client — send messages and typing indicators.

Uses urllib.request (stdlib) — zero external dependencies for Lambda.
PII is masked in logs by the global PIIMaskingFilter.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error

from config import WhatsAppConfig

logger = logging.getLogger(__name__)


class WhatsAppClient:
    """HTTP client for WhatsApp Business API."""

    def __init__(self, config: WhatsAppConfig) -> None:
        self._config = config
        self._base_url = config.base_url
        self._headers = {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }
        self._timeout = config.timeout

    def send_message(self, to: str, text: str) -> bool:
        """Send text message. Returns True on success."""
        return self._post("/messages", {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        })

    def send_typing_indicator(self, to: str, message_id: str) -> None:
        """Mark as read + send typing indicator."""
        self._post("/messages", {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
            "typing_indicator": {"type": "text"},
        })

    def _post(self, path: str, payload: dict) -> bool:
        """POST JSON to WhatsApp API. Returns True on success."""
        url = f"{self._base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return 200 <= resp.status < 300
        except urllib.error.HTTPError as e:
            logger.error("WhatsApp API error: %s %s", e.code, e.reason)
            return False
        except Exception as e:
            logger.error("WhatsApp API request failed: %s", e)
            return False

    def close(self) -> None:
        """No-op — urllib doesn't need explicit cleanup."""
        pass
