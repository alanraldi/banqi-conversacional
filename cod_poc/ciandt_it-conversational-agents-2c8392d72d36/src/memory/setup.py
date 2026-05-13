"""Memory Setup — configura AgentCore Memory (STM+LTM) a partir do domain.yaml.

Namespaces são montados dinamicamente: /{namespace}/{user_id}.
Degraded mode: se AGENTCORE_MEMORY_ID não configurado, log warning e retorna.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from strands import Agent

from src.config.settings import get_settings
from src.domain.schema import DomainConfig

logger = logging.getLogger(__name__)


def _mask_user_id(user_id: str) -> str:
    """Mask user_id for logging — keep only last 4 chars for debugging."""
    if len(user_id) <= 4:
        return "****"
    return f"****{user_id[-4:]}"


def attach_memory(
    *,
    agent: Agent,
    config: DomainConfig,
    user_id: str,
    session_id: str | None = None,
) -> None:
    """Anexa AgentCore Memory ao agent usando namespaces do domain.yaml.

    Args:
        agent: Agent Strands para anexar memória.
        config: Configuração do domínio com namespaces.
        user_id: Identificador do usuário.
        session_id: Identificador da sessão (gerado se ausente).

    Raises:
        ImportError: Se dependências de memória não instaladas.
    """
    settings = get_settings()

    if not settings.AGENTCORE_MEMORY_ID:
        logger.warning("AGENTCORE_MEMORY_ID not set — running without memory (degraded mode)")
        return

    from bedrock_agentcore.memory.integrations.strands.config import (
        AgentCoreMemoryConfig,
    )
    from bedrock_agentcore.memory.integrations.strands.session_manager import (
        AgentCoreMemorySessionManager,
    )
    from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider

    if not session_id:
        prefix = config.agent.session_prefix
        ts = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        session_id = f"{prefix}_{ts}"

    retrieval_config = _build_retrieval_config(config, user_id)

    memory_config = AgentCoreMemoryConfig(
        memory_id=settings.AGENTCORE_MEMORY_ID,
        session_id=session_id,
        actor_id=user_id,
        retrieval_config=retrieval_config,
    )

    agent.session_manager = AgentCoreMemorySessionManager(
        agentcore_memory_config=memory_config,
        region_name=settings.AWS_REGION,
    )

    ltm_tools = AgentCoreMemoryToolProvider(
        memory_id=settings.AGENTCORE_MEMORY_ID,
        actor_id=user_id,
        session_id=session_id,
        region=settings.AWS_REGION,
        namespace=f"/users/{user_id}",
    ).tools

    if hasattr(agent, "tools") and agent.tools:
        agent.tools.extend(ltm_tools)
    else:
        agent.tools = list(ltm_tools)

    logger.info(
        "Memory attached",
        extra={"memory_id": settings.AGENTCORE_MEMORY_ID, "user_id": _mask_user_id(user_id)},
    )


def _build_retrieval_config(
    config: DomainConfig,
    user_id: str,
) -> dict:
    """Monta retrieval_config a partir dos namespaces do domain.yaml.

    Args:
        config: Configuração do domínio.
        user_id: ID do usuário para namespace path.

    Returns:
        Dict de namespace_path → RetrievalConfig.
    """
    from bedrock_agentcore.memory.integrations.strands.config import RetrievalConfig

    result: dict = {}
    for ns_name, ns_cfg in config.memory.namespaces.items():
        namespace_path = f"/{ns_name}/{user_id}"
        result[namespace_path] = RetrievalConfig(
            top_k=ns_cfg.top_k,
            relevance_score=ns_cfg.relevance_score,
        )
    return result
