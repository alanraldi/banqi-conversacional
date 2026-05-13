"""Cliente HTTP para a API WhatsApp Cloud.

Encapsula o envio de mensagens e typing indicator via WhatsApp Business API.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = 10
_WPP_API_URL = "https://graph.facebook.com/v19.0"


class WhatsAppClient:
    """Cliente reutilizável para WhatsApp Business API (singleton por Lambda warm start)."""

    def __init__(self, token: str, phone_number_id: str) -> None:
        self._token = token
        self._phone_number_id = phone_number_id
        self._base = f"{_WPP_API_URL}/{phone_number_id}"

    def send_message(self, to: str, text: str) -> None:
        """Envia mensagem de texto para o cliente."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        self._post("/messages", payload)

    def send_typing_indicator(self, to: str, message_id: str) -> None:
        """Envia indicador de digitação (read receipt + typing)."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        self._post("/messages", payload)

    def _post(self, path: str, payload: dict) -> None:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        try:
            with httpx.Client(timeout=_TIMEOUT) as client:
                resp = client.post(f"{self._base}{path}", headers=headers, json=payload)
            if resp.status_code >= 400:
                logger.error(
                    "WhatsApp API error: status=%s body=%s", resp.status_code, resp.text[:200]
                )
        except Exception as exc:
            logger.error("WhatsApp API request failed: %s", exc)


def build_client() -> WhatsAppClient:
    """Cria cliente WhatsApp a partir das variáveis de ambiente."""
    token = os.environ.get("WHATSAPP_TOKEN", "")
    phone_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
    return WhatsAppClient(token=token, phone_number_id=phone_id)
