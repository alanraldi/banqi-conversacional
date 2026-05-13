"""WhatsApp webhook processor — dedup, agent invocation, response.

Orchestrates: signature validation → dedup → typing → agent → respond.
Domain-agnostic: error messages come from config, not hardcoded.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import boto3
from botocore.exceptions import ClientError

from agentcore_client import invoke_agent_runtime, save_conversation_to_memory
from client import WhatsAppClient
from config import WhatsAppConfig
from models import WebhookPayload
from signature import validate_webhook_signature

logger = logging.getLogger(__name__)

_DEDUP_TTL_SECONDS = 120
_DOMAIN_SLUG = os.environ.get("DOMAIN_SLUG", "agent")
_MIN_SESSION_LEN = 33


def _build_session_id(phone_number: str) -> str:
    """Deterministic session ID for WhatsApp user (≥33 chars for AgentCore)."""
    clean = phone_number.replace("+", "").replace("-", "").replace(" ", "")
    session_id = f"{_DOMAIN_SLUG}-wa-session-{clean}"
    return session_id.ljust(_MIN_SESSION_LEN, "0")[:256]

# Lazy singleton — reused across Lambda warm starts
_dedup_table: Any = None  # boto3 DynamoDB Table resource
_dedup_table_checked = False


def _get_dedup_table() -> object | None:
    """Get DynamoDB dedup table (singleton, None if not configured)."""
    global _dedup_table, _dedup_table_checked
    if not _dedup_table_checked:
        name = os.environ.get("DEDUP_TABLE_NAME")
        if name:
            _dedup_table = boto3.resource("dynamodb").Table(name)
        _dedup_table_checked = True
    return _dedup_table


def _is_duplicate(table: Any, message_id: str) -> bool:
    """Check if message already processed via DynamoDB conditional put."""
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


def handle_verification(
    params: dict[str, str],
    verify_token: str,
) -> dict[str, Any]:
    """Handle GET webhook verification (hub.challenge)."""
    mode = params.get("hub.mode", "")
    token = params.get("hub.verify_token", "")
    challenge = params.get("hub.challenge", "")

    if mode == "subscribe" and token == verify_token:
        logger.info("Webhook verified")
        return {"statusCode": 200, "body": challenge}

    logger.warning("Webhook verification failed")
    return {"statusCode": 403, "body": "Forbidden"}


def handle_message(
    body: bytes,
    signature_header: str | None,
    config: WhatsAppConfig,
    client: WhatsAppClient,
    error_message: str,
) -> dict[str, Any]:
    """Handle POST webhook — validate, dedup, invoke agent, respond.

    Args:
        body: Raw request body bytes.
        signature_header: X-Hub-Signature-256 header value.
        config: WhatsApp configuration.
        client: Reusable WhatsApp HTTP client (initialized at Lambda cold start).
        error_message: Generic error message from domain config.

    Returns:
        API Gateway response dict.
    """
    # 1. Signature validation (Fix C7)
    if not validate_webhook_signature(body, signature_header, config.app_secret):
        return {"statusCode": 403, "body": "Invalid signature"}

    # 2. Parse payload
    try:
        payload = WebhookPayload.model_validate_json(body)
    except Exception as e:
        logger.error("Invalid webhook payload: %s", e)
        return {"statusCode": 400, "body": "Invalid payload"}

    # 3. Extract messages (only text in v1)
    messages = payload.extract_messages()
    if not messages:
        return {"statusCode": 200, "body": json.dumps({"status": "no_message"})}

    dedup_table = _get_dedup_table()

    for msg in messages:
        if msg.type != "text" or not msg.text:
            continue

        # 4. Dedup
        if _is_duplicate(dedup_table, msg.id):
            logger.info("Duplicate message ignored: %s", msg.id)
            continue

        # 5. Typing indicator
        client.send_typing_indicator(msg.from_, msg.id)

        # 6. Invoke AgentCore
        session_id = _build_session_id(msg.from_)
        try:
            response_text = invoke_agent_runtime(
                prompt=msg.text.body,
                user_id=msg.from_,
                session_id=session_id,
            )
        except RuntimeError:
            response_text = error_message

        # 7. Persist memory (create_event — feeds LTM strategies)
        if config.agentcore_memory_id and response_text != error_message:
            save_conversation_to_memory(
                memory_id=config.agentcore_memory_id,
                actor_id=msg.from_,
                session_id=session_id,
                user_message=msg.text.body,
                agent_response=response_text,
            )

        # 8. Send response
        client.send_message(msg.from_, response_text)

    return {"statusCode": 200, "body": json.dumps({"status": "processed"})}
