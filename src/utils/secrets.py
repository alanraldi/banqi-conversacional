"""Recuperação de secrets — dev: env var / prod: Secrets Manager.

Cache por nome de secret. Fail-fast sem fallback para valores padrão.
Convenção de path: ${domain_slug}/<service>/<nome-do-secret>
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache

import boto3

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_secret(name: str) -> str:
    """Recupera valor do secret — env var primeiro, depois Secrets Manager.

    Args:
        name: Nome da env var (dev) ou ID do secret no Secrets Manager (prod).

    Returns:
        Valor do secret como string.

    Raises:
        RuntimeError: Se não conseguir recuperar o secret.
    """
    # Dev: env var tem precedência
    val = os.getenv(name)
    if val:
        return val

    # Prod: Secrets Manager
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=name)
        return response["SecretString"]
    except Exception as e:
        raise RuntimeError(f"Falha ao recuperar secret '{name}': {e}") from e


def load_whatsapp_secrets(secret_arn: str | None = None) -> dict[str, str]:
    """Carrega credenciais WhatsApp do Secrets Manager ou env vars.

    Em dev: carrega das variáveis de ambiente individuais.
    Em prod: carrega do Secrets Manager (JSON com todas as credenciais).

    Args:
        secret_arn: ARN do secret no Secrets Manager (opcional — usa WHATSAPP_SECRET_ARN se não informado).

    Returns:
        Dict com chaves: WHATSAPP_ACCESS_TOKEN, WHATSAPP_APP_SECRET, WHATSAPP_VERIFY_TOKEN.

    Raises:
        RuntimeError: Se não conseguir carregar as credenciais.
    """
    # Dev: env vars individuais
    if all(os.getenv(k) for k in ("WHATSAPP_TOKEN", "WHATSAPP_APP_SECRET", "WHATSAPP_VERIFY_TOKEN")):
        return {
            "WHATSAPP_ACCESS_TOKEN": os.environ["WHATSAPP_TOKEN"],
            "WHATSAPP_APP_SECRET": os.environ["WHATSAPP_APP_SECRET"],
            "WHATSAPP_VERIFY_TOKEN": os.environ["WHATSAPP_VERIFY_TOKEN"],
        }

    # Prod: Secrets Manager
    arn = secret_arn or os.getenv("WHATSAPP_SECRET_ARN")
    if not arn:
        raise RuntimeError(
            "WHATSAPP_SECRET_ARN não configurado e variáveis de ambiente individuais ausentes."
        )

    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=arn)
        secrets: dict[str, str] = json.loads(response["SecretString"])
        return secrets
    except Exception as e:
        raise RuntimeError(f"Falha ao carregar secrets do WhatsApp: {e}") from e
