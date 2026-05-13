"""Recuperação de secrets — dev: env var / prod: Secrets Manager."""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

import boto3

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_secret(name: str) -> str:
    """Recupera valor do secret — env var primeiro, depois Secrets Manager."""
    val = os.getenv(name)
    if val:
        return val

    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=name)
        return response["SecretString"]
    except Exception as e:
        raise RuntimeError(f"Falha ao recuperar secret '{name}': {e}") from e


def load_whatsapp_secrets(secret_arn: str | None = None) -> dict[str, str]:
    """Carrega credenciais WhatsApp do Secrets Manager ou env vars."""
    if all(os.getenv(k) for k in ("WHATSAPP_TOKEN", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN")):
        return {
            "WHATSAPP_ACCESS_TOKEN": os.environ["WHATSAPP_TOKEN"],
            "WHATSAPP_APP_SECRET": os.environ["WHATSAPP_APP_SECRET"],
            "WHATSAPP_VERIFY_TOKEN": os.environ["WHATSAPP_VERIFY_TOKEN"],
        }

    arn = secret_arn or os.getenv("WHATSAPP_SECRET_ARN")
    if not arn:
        raise RuntimeError("WHATSAPP_SECRET_ARN não configurado e variáveis de ambiente individuais ausentes.")

    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=arn)
        secrets: dict[str, str] = json.loads(response["SecretString"])
        return secrets
    except Exception as e:
        raise RuntimeError(f"Falha ao carregar secrets do WhatsApp: {e}") from e
