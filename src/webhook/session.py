"""Correlação de sessão para webhooks banQi.

Quando o backend envia um webhook, precisamos identificar a sessão ativa do cliente
pelo número de telefone para poder enviar a mensagem de retorno via WhatsApp.

Implementação inicial: DynamoDB como store de sessões ativas.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_SESSION_TABLE_ENV = "SESSION_TABLE_NAME"
_SESSION_TTL_SECONDS = 3600 * 24  # 24h


def _get_table() -> Any | None:
    name = os.environ.get(_SESSION_TABLE_ENV)
    if not name:
        logger.warning("SESSION_TABLE_NAME não configurado — correlação de sessão desabilitada")
        return None
    return boto3.resource("dynamodb").Table(name)


def register_session(phone: str, session_id: str) -> None:
    """Registra sessão ativa do cliente no DynamoDB."""
    table = _get_table()
    if not table:
        return
    try:
        table.put_item(
            Item={
                "phone": phone,
                "session_id": session_id,
                "ttl": int(time.time()) + _SESSION_TTL_SECONDS,
                "updated_at": int(time.time()),
            }
        )
    except Exception as exc:
        logger.warning("register_session: falhou para phone=%s — %s", phone[:6] + "****", exc)


def get_session_id(phone: str) -> str | None:
    """Busca session_id ativo para o telefone.

    Returns:
        session_id se sessão ativa encontrada, None caso contrário.
    """
    table = _get_table()
    if not table:
        return None
    try:
        resp = table.get_item(Key={"phone": phone})
        item = resp.get("Item")
        if not item:
            return None
        # Verificar TTL manualmente (DynamoDB pode demorar a expirar)
        if item.get("ttl", 0) < int(time.time()):
            logger.info("get_session_id: sessão expirada para phone=%s", phone[:6] + "****")
            return None
        return item.get("session_id")
    except ClientError as exc:
        logger.error("get_session_id: erro DynamoDB — %s", exc)
        return None
