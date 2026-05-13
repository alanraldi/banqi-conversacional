"""Entrypoint genérico para AgentCore Runtime.

Zero referências hardcoded a domínio específico.
Toda configuração vem do domain.yaml + env vars.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from bedrock_agentcore.runtime import BedrockAgentCoreApp

from src.agents.factory import create_supervisor
from src.config.settings import get_settings
from src.domain.loader import load_domain_config
from src.domain.schema import DomainConfig
from src.utils.agent_helpers import extract_text
from src.utils.logging import setup_logging
from src.utils.validation import validate_input_length, validate_non_empty

# --- Fail-fast no startup ---
setup_logging()
logger = logging.getLogger(__name__)

try:
    _cfg: DomainConfig = load_domain_config()
except Exception as e:
    logger.critical("Startup failed — invalid domain config: %s", e)
    raise

# Propaga BEDROCK_KB_ID para KNOWLEDGE_BASE_ID (usado por tools built-in)
_settings = get_settings()
if _settings.BEDROCK_KB_ID:
    os.environ.setdefault("KNOWLEDGE_BASE_ID", _settings.BEDROCK_KB_ID)

app = BedrockAgentCoreApp()


@app.ping
def health() -> str:
    """Health check endpoint."""
    return "Healthy"


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, str]:
    """Processa requisição do AgentCore Runtime.

    Args:
        payload: Dict com prompt, user_id/phone_number, session_id.

    Returns:
        Dict com result (texto da resposta).
    """
    prompt = _extract_prompt(payload)
    if not prompt:
        return {"result": _cfg.error_messages.empty_input}

    user_id = _extract_user_id(payload)
    session_id = payload.get("session_id") or f"{_cfg.agent.session_prefix}-{user_id}"

    try:
        supervisor = create_supervisor(user_id=user_id, session_id=session_id)
        result = supervisor(prompt)
        return {"result": extract_text(result)}
    except Exception as e:
        logger.error("Processing error: %s", e, exc_info=True)
        return {"result": _cfg.error_messages.generic}


def _extract_prompt(payload: dict[str, Any]) -> str | None:
    """Extrai e valida prompt do payload."""
    raw = payload.get("prompt", "") or payload.get("input", {}).get("prompt", "")
    try:
        text = validate_non_empty(raw, "prompt")
        return validate_input_length(text)
    except ValueError:
        return None


def _extract_user_id(payload: dict[str, Any]) -> str:
    """Extract and sanitize user_id from payload.

    Validates format (alphanumeric + limited special chars) and length
    to prevent injection in memory namespaces and session IDs.
    """
    raw = payload.get("phone_number") or payload.get("from") or payload.get("wa_id") or payload.get("user_id")

    if not raw or not str(raw).strip():
        logger.warning("No user_id in payload — using anonymous session")
        return "anonymous"

    sanitized = _sanitize_identifier(str(raw).strip())
    return sanitized


def _sanitize_identifier(value: str, max_length: int = 64) -> str:
    """Sanitize identifier for use in memory namespaces and session IDs.

    Keeps only alphanumeric, hyphens, underscores, plus signs.
    Prevents path traversal and injection.
    """
    clean = re.sub(r"[^a-zA-Z0-9\-_+]", "", value)
    if not clean:
        return "invalid"
    return clean[:max_length]


if __name__ == "__main__":
    logger.info("Starting %s on port 8080", _cfg.agent.name)
    app.run()
