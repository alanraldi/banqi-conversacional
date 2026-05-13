"""WhatsApp webhook Lambda handler — API Gateway event format.

Initialized outside handler (config, error messages) for Lambda warm starts.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from client import WhatsAppClient
from config import WhatsAppConfig
from webhook_processor import handle_message, handle_verification

logger = logging.getLogger(__name__)

# --- Init outside handler (Lambda warm start) ---
_config: WhatsAppConfig | None = None
_client: WhatsAppClient | None = None
_error_message: str = "Sorry, an error occurred. Please try again."

try:
    _config = WhatsAppConfig()
    _client = WhatsAppClient(_config)
    _error_message = os.environ.get("ERROR_MESSAGE_GENERIC", _error_message)
    logger.info("Lambda initialized")
except Exception as e:
    logger.error("Lambda init failed: %s", e)


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """API Gateway Lambda handler for WhatsApp webhook."""
    # Support both v1 (httpMethod) and v2 (requestContext.http.method)
    method = (
        event.get("httpMethod")
        or event.get("requestContext", {}).get("http", {}).get("method", "")
    ).upper()

    if not _config or not _client:
        return _response(503, {"error": "Service unavailable"})

    if method == "GET":
        params = event.get("queryStringParameters") or {}
        return handle_verification(params, _config.verify_token)

    if method == "POST":
        body = (event.get("body") or "").encode("utf-8")
        headers = event.get("headers") or {}
        signature = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256")
        return handle_message(body, signature, _config, _client, _error_message)

    return _response(405, {"error": "Method not allowed"})


def _response(status_code: int, body: dict[str, Any]) -> dict[str, Any]:
    """Build API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
