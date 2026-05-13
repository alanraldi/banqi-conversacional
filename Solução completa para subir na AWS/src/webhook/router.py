"""Roteador de eventos webhook banQi."""

from __future__ import annotations

import logging
from typing import Any

from src.webhook.events import (
    handle_consent_term_file_ready,
    handle_no_offer_available,
    handle_proposal_created,
    handle_proposal_status_update,
    handle_simulation_completed,
    handle_simulation_ready,
)

logger = logging.getLogger(__name__)

_HANDLERS = {
    "CONSENT_TERM_FILE_READY": handle_consent_term_file_ready,
    "NO_OFFER_AVAILABLE": handle_no_offer_available,
    "SIMULATION_READY": handle_simulation_ready,
    "SIMULATION_COMPLETED": handle_simulation_completed,
    "PROPOSAL_CREATED": handle_proposal_created,
    "PROPOSAL_STATUS_UPDATE": handle_proposal_status_update,
}


def route_banqi_webhook(event_type: str, payload: dict[str, Any]) -> str | None:
    """Roteia um evento banQi para o handler correto."""
    handler = _HANDLERS.get(event_type)
    if not handler:
        logger.warning("route_banqi_webhook: evento desconhecido '%s'", event_type)
        return None
    try:
        return handler(payload)
    except Exception as exc:
        logger.error("route_banqi_webhook: erro no handler '%s' — %s", event_type, exc, exc_info=True)
        return None
