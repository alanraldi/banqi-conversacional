"""Entrypoint do AgentCore Runtime — banQi Consignado.

Compatível com AWS Bedrock AgentCore Runtime via Strands Agents SDK.
"""

from __future__ import annotations

import logging

from src.agents.factory import create_supervisor
from src.config.settings import get_settings
from src.utils.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def invoke(user_input: str, user_id: str, session_id: str) -> str:
    """Ponto de entrada principal invocado pelo AgentCore Runtime.

    Args:
        user_input: Mensagem do usuário.
        user_id: Identificador do usuário (telefone WhatsApp E.164).
        session_id: ID da sessão (gerado pelo Lambda handler).

    Returns:
        Texto da resposta do agente.
    """
    settings = get_settings()
    logger.info(
        "invoke: user_id=%s session_id=%s input_len=%d",
        user_id[:6] + "****" if user_id else "unknown",
        session_id,
        len(user_input),
    )

    try:
        supervisor = create_supervisor(user_id=user_id, session_id=session_id)
        result = supervisor(user_input)
        return str(result)
    except Exception as e:
        logger.error("invoke: erro no supervisor — %s", e, exc_info=True)
        return settings.ERROR_MESSAGE_GENERIC
