"""Lambda handler — canal WhatsApp e webhooks banQi.

Suporta dois tipos de entrada:
1. WhatsApp Cloud API (GET: verificação / POST: mensagem do cliente)
2. Webhooks banQi (POST: eventos assíncronos do backend)

Orquestra: signature validation → dedup → typing → AgentCore → respond.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.utils.logging import configure_logging
from src.webhook.agentcore_client import invoke_agent_runtime, save_conversation_to_memory
from src.webhook.models import BanqiWebhookPayload, WhatsAppWebhookPayload
from src.webhook.router import route_banqi_webhook
from src.webhook.session import get_session_id, register_session
from src.webhook.signature import validate_webhook_signature
from src.webhook.whatsapp_client import WhatsAppClient, build_client

configure_logging()
logger = logging.getLogger(__name__)

_DEDUP_TTL_SECONDS = 120
_DOMAIN_SLUG = os.environ.get("DOMAIN_SLUG", "banqi-consignado")
_MIN_SESSION_LEN = 33

# Singletons — reutilizados entre Lambda warm starts
_wpp_client: WhatsAppClient | None = None
_dedup_table: Any = None
_dedup_checked = False


def _get_wpp_client() -> WhatsAppClient:
    global _wpp_client
    if _wpp_client is None:
        _wpp_client = build_client()
    return _wpp_client


def _get_dedup_table() -> Any | None:
    global _dedup_table, _dedup_checked
    if not _dedup_checked:
        name = os.environ.get("DEDUP_TABLE_NAME")
        if name:
            _dedup_table = boto3.resource("dynamodb").Table(name)
        _dedup_checked = True
    return _dedup_table


def _build_session_id(phone: str) -> str:
    clean = phone.replace("+", "").replace("-", "").replace(" ", "")
    sid = f"{_DOMAIN_SLUG}-wa-session-{clean}"
    return sid.ljust(_MIN_SESSION_LEN, "0")[:256]


def _is_duplicate(message_id: str) -> bool:
    table = _get_dedup_table()
    if not table:
        return False
    try:
        table.put_item(
            Item={"message_id": message_id, "ttl": int(time.time()) + _DEDUP_TTL_SECONDS},
            ConditionExpression="attribute_not_exists(message_id)",
        )
        return False
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return True
        raise


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Entrypoint do Lambda para WhatsApp e webhooks banQi.

    Detecta o tipo de request pelo path/source e despacha adequadamente.
    """
    # Detectar versão do API Gateway (v1 vs v2)
    if "requestContext" in event and "http" in event.get("requestContext", {}):
        method = event["requestContext"]["http"]["method"]
        path = event.get("rawPath", "/")
    else:
        method = event.get("httpMethod", "POST")
        path = event.get("path", "/")

    headers = event.get("headers") or {}
    body_raw = event.get("body", "") or ""

    if isinstance(body_raw, str):
        body_bytes = body_raw.encode("utf-8")
    else:
        body_bytes = body_raw

    # Rota: webhooks banQi recebidos no path /webhook/banqi
    if "/banqi" in path or "/events" in path:
        return _handle_banqi_webhook(body_bytes, headers, method)

    # Rota: WhatsApp Cloud API
    if method == "GET":
        return _handle_verification(event)

    return _handle_whatsapp_message(body_bytes, headers)


def _handle_verification(event: dict[str, Any]) -> dict[str, Any]:
    """Verifica o webhook do WhatsApp (hub.challenge)."""
    params = event.get("queryStringParameters") or {}
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")

    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == verify_token
    ):
        logger.info("Webhook WhatsApp verificado com sucesso")
        return {"statusCode": 200, "body": params.get("hub.challenge", "")}

    logger.warning("Falha na verificação do webhook WhatsApp")
    return {"statusCode": 403, "body": "Forbidden"}


def _handle_whatsapp_message(body_bytes: bytes, headers: dict[str, str]) -> dict[str, Any]:
    """Processa mensagem recebida do WhatsApp: validação → dedup → AgentCore → resposta."""
    app_secret = os.environ.get("WHATSAPP_APP_SECRET", "")
    signature = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256", "")

    if not validate_webhook_signature(body_bytes, signature, app_secret):
        return {"statusCode": 403, "body": "Invalid signature"}

    try:
        payload = WhatsAppWebhookPayload.model_validate_json(body_bytes)
    except Exception as exc:
        logger.error("Payload WhatsApp inválido: %s", exc)
        return {"statusCode": 400, "body": "Invalid payload"}

    messages = payload.extract_messages()
    if not messages:
        return {"statusCode": 200, "body": json.dumps({"status": "no_message"})}

    error_message = os.environ.get(
        "ERROR_MESSAGE_GENERIC",
        "Desculpe, ocorreu um erro. Tente novamente em alguns instantes.",
    )
    memory_id = os.environ.get("AGENTCORE_MEMORY_ID", "")
    wpp = _get_wpp_client()

    for msg in messages:
        if msg.type != "text" or not msg.text:
            continue

        if _is_duplicate(msg.id):
            logger.info("Mensagem duplicada ignorada: %s", msg.id)
            continue

        phone = msg.from_
        session_id = _build_session_id(phone)

        # Persistir sessão ativa para correlação de webhooks
        register_session(phone, session_id)

        # Typing indicator
        wpp.send_typing_indicator(phone, msg.id)

        # Invocar AgentCore Runtime
        try:
            response_text = invoke_agent_runtime(
                prompt=msg.text.body,
                user_id=phone,
                session_id=session_id,
            )
        except RuntimeError:
            response_text = error_message

        # Persistir na LTM
        if memory_id and response_text != error_message:
            save_conversation_to_memory(
                memory_id=memory_id,
                actor_id=phone,
                session_id=session_id,
                user_message=msg.text.body,
                agent_response=response_text,
            )

        # Enviar resposta
        wpp.send_message(phone, response_text)

    return {"statusCode": 200, "body": json.dumps({"status": "processed"})}


def _handle_banqi_webhook(
    body_bytes: bytes,
    headers: dict[str, str],
    method: str,
) -> dict[str, Any]:
    """Processa eventos assíncronos do backend banQi.

    Retorna sempre HTTP 200 para evitar retentativas desnecessárias do backend.
    """
    if method != "POST":
        return {"statusCode": 200, "body": json.dumps({"status": "ok"})}

    try:
        webhook = BanqiWebhookPayload.model_validate_json(body_bytes)
    except Exception as exc:
        logger.error("Payload webhook banQi inválido: %s", exc)
        return {"statusCode": 200, "body": json.dumps({"status": "invalid_payload"})}

    phone = webhook.phone
    event_type = webhook.event

    logger.info(
        "banqi_webhook: event=%s phone=%s",
        event_type,
        (phone[:6] + "****") if phone else "unknown",
    )

    if not phone:
        logger.warning("banqi_webhook: phone ausente no payload — ignorando")
        return {"statusCode": 200, "body": json.dumps({"status": "no_phone"})}

    # Buscar sessão ativa
    session_id = get_session_id(phone)
    if not session_id:
        logger.info(
            "banqi_webhook: sem sessão ativa para phone=%s event=%s — evento órfão",
            phone[:6] + "****",
            event_type,
        )
        return {"statusCode": 200, "body": json.dumps({"status": "no_active_session"})}

    # Rotear evento para o handler correto
    message = route_banqi_webhook(event_type, webhook.model_dump())
    if message:
        wpp = _get_wpp_client()
        wpp.send_message(phone, message)

    return {"statusCode": 200, "body": json.dumps({"status": "processed", "event": event_type})}
