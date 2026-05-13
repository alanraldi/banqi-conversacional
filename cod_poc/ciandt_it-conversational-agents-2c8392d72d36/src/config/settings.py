"""Application settings — dual strategy: dev (.env + AWS_PROFILE) / prod (IAM Roles + Secrets Manager)."""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import boto3
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Domain-agnostic settings. Zero domain-specific fields."""

    # --- Environment ---
    APP_ENV: str = Field(default="dev")

    @property
    def is_dev(self) -> bool:
        return self.APP_ENV.lower() == "dev"

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV.lower() == "prod"

    # --- AWS (dev: AWS_PROFILE / prod: IAM Role) ---
    AWS_PROFILE: str | None = Field(default=None)
    AWS_REGION: str = Field(default="us-east-1")
    AWS_ACCOUNT_ID: str | None = Field(default=None)

    # --- AgentCore ---
    AGENTCORE_MEMORY_ID: str | None = Field(default=None)
    AGENTCORE_MEMORY_ENABLED: bool = Field(default=True)
    AGENTCORE_OBSERVABILITY_ENABLED: bool = Field(default=True)
    AGENTCORE_GATEWAY_ENABLED: bool = Field(default=True)

    # --- Bedrock Knowledge Base ---
    BEDROCK_KB_ID: str | None = Field(default=None)
    MIN_SCORE: float = Field(default=0.4)

    # --- Bedrock Guardrails (optional) ---
    BEDROCK_GUARDRAIL_ID: str | None = Field(default=None)
    BEDROCK_GUARDRAIL_VERSION: str = Field(default="DRAFT")

    # --- Conversation ---
    CONVERSATION_WINDOW_SIZE: int = Field(default=20)

    # --- Observability ---
    OPENTELEMETRY_ENABLED: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Lazy singleton — only created when first called. Cacheable and test-friendly."""
    return Settings()


def get_boto3_session(settings_instance: Settings | None = None) -> boto3.Session:
    """Create boto3 session respecting the credential chain.

    Args:
        settings_instance: Optional settings override (for testing).

    Returns:
        boto3.Session configured for dev (AWS_PROFILE) or prod (IAM Role).
    """
    s = settings_instance or get_settings()
    kwargs: dict[str, Any] = {"region_name": s.AWS_REGION}
    if s.AWS_PROFILE:
        kwargs["profile_name"] = s.AWS_PROFILE
    return boto3.Session(**kwargs)


def get_secret(secret_name: str, settings_instance: Settings | None = None) -> str:
    """Retrieve secret — delegates to utils/secrets.py (single source of truth).

    Args:
        secret_name: Name of the secret (env var name or Secrets Manager ID).
        settings_instance: Ignored — kept for backward compatibility.

    Returns:
        Secret value as string.
    """
    from src.utils.secrets import get_secret as _get_secret

    return _get_secret(secret_name)
