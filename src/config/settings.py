"""Settings para banQi Conversacional — empréstimo consignado.

Estratégia dual:
- Dev: .env + AWS_PROFILE
- Prod: IAM Roles + Secrets Manager (sem .env)

Uso: from src.config.settings import get_settings; s = get_settings()
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import boto3
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Configurações do banQi Conversacional — Consignado."""

    # --- Ambiente ---
    APP_ENV: str = Field(default="dev")

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV.lower() == "dev"

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV.lower() == "prod"

    # --- AWS ---
    AWS_PROFILE: str | None = Field(default=None)
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ACCOUNT_ID: str | None = Field(default=None)

    # --- AgentCore Memory ---
    AGENTCORE_MEMORY_ID: str | None = Field(default=None)
    AGENTCORE_MEMORY_ENABLED: bool = Field(default=True)

    # --- AgentCore Gateway (MCP) ---
    AGENTCORE_GATEWAY_ENDPOINT: str | None = Field(default=None)
    GATEWAY_CLIENT_ID: str | None = Field(default=None)
    GATEWAY_CLIENT_SECRET: str | None = Field(default=None)
    GATEWAY_TOKEN_ENDPOINT: str | None = Field(default=None)
    GATEWAY_SCOPE: str | None = Field(default=None)

    # --- Bedrock Guardrails ---
    BEDROCK_GUARDRAIL_ID: str | None = Field(default=None)
    BEDROCK_GUARDRAIL_VERSION: str = Field(default="DRAFT")

    # --- Modelos ---
    SUPERVISOR_AGENT_MODEL_ID: str = Field(
        default="us.anthropic.claude-sonnet-4-6-20250514-v1:0"
    )
    CONSIGNADO_AGENT_MODEL_ID: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )
    GENERAL_AGENT_MODEL_ID: str = Field(
        default="us.anthropic.claude-haiku-4-5-20251001-v1:0"
    )

    # --- Conversa ---
    CONVERSATION_WINDOW_SIZE: int = Field(default=20)

    # --- Domínio ---
    DOMAIN_SLUG: str = Field(default="banqi-consignado")

    # --- DynamoDB dedup ---
    DEDUP_TABLE_NAME: str | None = Field(default=None)

    # --- WhatsApp (sensíveis — carregados via Secrets Manager em prod) ---
    WHATSAPP_TOKEN: str | None = Field(default=None)
    WHATSAPP_APP_SECRET: str | None = Field(default=None)
    WHATSAPP_VERIFY_TOKEN: str | None = Field(default=None)
    WHATSAPP_PHONE_NUMBER_ID: str | None = Field(default=None)

    # --- Mensagens de erro ---
    ERROR_MESSAGE_GENERIC: str = Field(
        default="Desculpe, ocorreu um erro. Tente novamente em alguns instantes."
    )
    ERROR_MESSAGE_OUT_OF_SCOPE: str = Field(
        default="Posso te ajudar apenas com empréstimo consignado. Quer simular ou contratar?"
    )

    # --- API banQi ---
    BANQI_API_BASE_URL: str | None = Field(default=None)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton lazy — criado apenas na primeira chamada."""
    return Settings()


def get_boto3_session(settings_instance: Settings | None = None) -> boto3.Session:
    """Cria sessão boto3 respeitando a cadeia de credenciais.

    Args:
        settings_instance: Configurações opcionais (para testes).

    Returns:
        boto3.Session configurada para dev (AWS_PROFILE) ou prod (IAM Role).
    """
    s = settings_instance or get_settings()
    kwargs: dict[str, Any] = {"region_name": s.AWS_REGION}
    if s.AWS_PROFILE:
        kwargs["profile_name"] = s.AWS_PROFILE
    return boto3.Session(**kwargs)


def get_secret(secret_name: str) -> str:
    """Recupera secret — delega para utils/secrets.py (fonte única da verdade).

    Args:
        secret_name: Nome da variável de ambiente (dev) ou ID do Secrets Manager (prod).

    Returns:
        Valor do secret como string.
    """
    from src.utils.secrets import get_secret as _get_secret

    return _get_secret(secret_name)
