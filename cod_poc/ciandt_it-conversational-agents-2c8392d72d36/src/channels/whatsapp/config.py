"""WhatsApp configuration — fail-fast on missing secrets.

Prod: reads JSON secret from Secrets Manager via WHATSAPP_SECRET_ARN.
Dev: reads individual env vars (WHATSAPP_ACCESS_TOKEN, etc.).
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

import boto3

logger = logging.getLogger(__name__)


class WhatsAppConfig:
    """WhatsApp Business API config.

    Raises RuntimeError/ValueError on init if required values are missing.
    """

    def __init__(self) -> None:
        secrets = _load_secrets()
        self.access_token: str = secrets["WHATSAPP_ACCESS_TOKEN"]
        self.app_secret: str = secrets["WHATSAPP_APP_SECRET"]
        self.verify_token: str = secrets["WHATSAPP_VERIFY_TOKEN"]
        self.phone_number_id: str = _require_env("WHATSAPP_PHONE_NUMBER_ID")
        self.api_version: str = os.getenv("WHATSAPP_API_VERSION", "v23.0")
        self.timeout: int = int(os.getenv("WHATSAPP_TIMEOUT", "10"))
        self.agentcore_memory_id: str | None = os.getenv("AGENTCORE_MEMORY_ID")

    @property
    def base_url(self) -> str:
        return f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}"


@lru_cache(maxsize=1)
def _load_secrets() -> dict[str, str]:
    """Load WhatsApp secrets from Secrets Manager ARN or env vars."""
    secret_arn = os.getenv("WHATSAPP_SECRET_ARN")

    if secret_arn:
        # Prod: JSON secret from Secrets Manager
        try:
            client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION", "us-east-1"))
            response = client.get_secret_value(SecretId=secret_arn)
            secrets = json.loads(response["SecretString"])
            logger.info("Secrets loaded from Secrets Manager")
            return secrets
        except Exception as e:
            raise RuntimeError(f"Failed to load secrets from {secret_arn}: {e}") from e

    # Dev: individual env vars
    return {
        "WHATSAPP_ACCESS_TOKEN": _require_env("WHATSAPP_ACCESS_TOKEN"),
        "WHATSAPP_APP_SECRET": _require_env("WHATSAPP_APP_SECRET"),
        "WHATSAPP_VERIFY_TOKEN": _require_env("WHATSAPP_VERIFY_TOKEN"),
    }


def _require_env(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise ValueError(f"Missing required env var: {name}")
    return val
