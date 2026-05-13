"""Agent Factory — cria Supervisor + sub-agentes a partir do domain.yaml.

Implementa o padrão Agents-as-Tools: cada sub-agente é registrado como @tool
no Supervisor, que decide qual invocar com base na intenção do usuário.

Sub-agentes são STATELESS. O Supervisor sempre injeta o contexto completo ao delegar.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models import BedrockModel

from src.agents.context import SessionContext
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

session_context = SessionContext()

_DOMAIN_ROOT = Path(__file__).parent.parent.parent / "domains" / "consignado"


def _load_domain() -> dict[str, Any]:
    with open(_DOMAIN_ROOT / "domain.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_prompt(prompt_file: str) -> str:
    path = _DOMAIN_ROOT / prompt_file
    return path.read_text(encoding="utf-8")


def create_supervisor(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> Agent:
    """Cria o Supervisor Agent com sub-agentes como tools.

    Setup pesado (modelo, prompts, tools delegadas) é cacheado via lru_cache.
    Setup por-request (contexto de sessão, memória, conversation manager) é sempre novo.
    """
    cfg = _load_domain()
    settings = get_settings()

    session_context.set(user_id=user_id, session_id=session_id)

    model = _get_cached_model(cfg["supervisor"]["model_id_env"])
    system_prompt = _get_cached_prompt(cfg["supervisor"]["prompt_file"])
    delegate_tools = _get_cached_delegate_tools()

    conversation_manager = SlidingWindowConversationManager(
        window_size=settings.CONVERSATION_WINDOW_SIZE,
        should_truncate_results=True,
    )

    sm = _create_session_manager(cfg, user_id, session_id) if user_id else None
    logger.info(
        "Session manager: %s (user_id=%s)", type(sm).__name__ if sm else "None", user_id
    )

    supervisor = Agent(
        name="Supervisor Agent",
        model=model,
        tools=list(delegate_tools),
        system_prompt=system_prompt,
        agent_id="supervisor_agent",
        description=cfg["supervisor"]["description"],
        conversation_manager=conversation_manager,
        session_manager=sm,
    )

    if user_id:
        _attach_ltm_tools(supervisor, user_id, session_id)

    return supervisor


@lru_cache(maxsize=4)
def _get_cached_model(model_id_env: str) -> BedrockModel:
    model_id = os.environ.get(model_id_env)
    if not model_id:
        raise ValueError(f"Variável de ambiente não configurada: {model_id_env}")
    return BedrockModel(
        model_id=model_id,
        cache_tools="default",
        **_guardrail_kwargs(),
    )


@lru_cache(maxsize=8)
def _get_cached_prompt(prompt_file: str) -> list[dict[str, Any]]:
    text = _load_prompt(prompt_file)
    return [
        {"text": text},
        {"cachePoint": {"type": "default"}},
    ]


@lru_cache(maxsize=1)
def _get_cached_delegate_tools() -> tuple[Any, ...]:
    cfg = _load_domain()
    tools = tuple(
        _make_delegate_tool(key, sa_cfg)
        for key, sa_cfg in cfg["sub_agents"].items()
    )
    logger.info("Delegate tools criadas: %s", [k for k in cfg["sub_agents"]])
    return tools


def _make_delegate_tool(key: str, agent_cfg: dict[str, Any]) -> Any:
    """Cria função @tool que delega para um sub-agente."""
    docstring = agent_cfg["tool_docstring"]

    @tool(name=f"{key}_assistant")
    def delegate(query: str) -> str:
        ctx = session_context.get()
        sub = _create_sub_agent(agent_cfg, key)
        result = sub(query)
        return str(result)

    delegate.__doc__ = docstring
    return delegate


def _create_sub_agent(agent_cfg: dict[str, Any], key: str) -> Agent:
    tools = _get_tools_for_agent(agent_cfg)
    return Agent(
        name=agent_cfg["name"],
        model=_get_cached_model(agent_cfg["model_id_env"]),
        tools=tools,
        system_prompt=_get_cached_prompt(agent_cfg["prompt_file"]),
        agent_id=f"{key}_agent",
        description=agent_cfg["description"],
    )


def _get_tools_for_agent(agent_cfg: dict[str, Any]) -> list:
    source = agent_cfg.get("tools_source", "none")
    provider = _TOOL_PROVIDERS.get(source)
    if not provider:
        logger.warning("tools_source desconhecido '%s' — sem tools", source)
        return []
    return provider()


def _get_gateway_tools() -> list:
    endpoint = os.environ.get("AGENTCORE_GATEWAY_ENDPOINT")
    if not endpoint:
        logger.warning("AGENTCORE_GATEWAY_ENDPOINT não configurado — modo degradado")
        return []
    try:
        from mcp.client.streamable_http import streamablehttp_client
        from strands.tools.mcp import MCPClient

        from src.gateway.token_manager import GatewayTokenManager

        token = GatewayTokenManager.get_instance().get_token()
        mcp = MCPClient(
            lambda: streamablehttp_client(endpoint, headers={"Authorization": f"Bearer {token}"}),
        )
        return [mcp]
    except Exception as e:
        logger.warning("MCP tools do Gateway indisponíveis — modo degradado: %s", e)
        return []


_TOOL_PROVIDERS: dict[str, Any] = {
    "gateway_mcp": _get_gateway_tools,
    "none": lambda: [],
}


def _guardrail_kwargs() -> dict[str, Any]:
    settings = get_settings()
    if not settings.BEDROCK_GUARDRAIL_ID:
        return {}
    return {
        "guardrail_id": settings.BEDROCK_GUARDRAIL_ID,
        "guardrail_version": settings.BEDROCK_GUARDRAIL_VERSION,
        "guardrail_trace": "enabled",
        "guardrail_redact_input": False,
        "guardrail_redact_output": False,
        "guardrail_latest_message": True,
    }


def _create_session_manager(
    cfg: dict[str, Any],
    user_id: str,
    session_id: str | None,
) -> Any:
    settings = get_settings()
    if not settings.AGENTCORE_MEMORY_ID:
        logger.warning("AGENTCORE_MEMORY_ID não configurado — sem memória")
        return None
    try:
        from bedrock_agentcore.memory.integrations.strands.config import (
            AgentCoreMemoryConfig,
            RetrievalConfig,
        )
        from bedrock_agentcore.memory.integrations.strands.session_manager import (
            AgentCoreMemorySessionManager,
        )

        session_prefix = cfg.get("agent", {}).get("session_prefix", "session")
        if not session_id:
            session_id = f"{session_prefix}-{user_id}"

        retrieval_config = {}
        for ns, nc in cfg.get("memory", {}).get("namespaces", {}).items():
            resolved = (
                ns.replace("{user_id}", user_id)
                  .replace("{session_id}", session_id)
            )
            retrieval_config[f"/{resolved}"] = RetrievalConfig(
                top_k=nc["top_k"], relevance_score=nc["relevance_score"]
            )

        memory_config = AgentCoreMemoryConfig(
            memory_id=settings.AGENTCORE_MEMORY_ID,
            session_id=session_id,
            actor_id=user_id,
            retrieval_config=retrieval_config,
        )
        return AgentCoreMemorySessionManager(
            agentcore_memory_config=memory_config,
            region_name=settings.AWS_REGION,
        )
    except Exception as e:
        logger.warning("Memory session manager falhou — modo degradado: %s", e, exc_info=True)
        return None


def _attach_ltm_tools(agent: Agent, user_id: str, session_id: str | None) -> None:
    settings = get_settings()
    if not settings.AGENTCORE_MEMORY_ID:
        return
    try:
        from strands_tools.agent_core_memory import AgentCoreMemoryToolProvider

        ltm_tools = AgentCoreMemoryToolProvider(
            memory_id=settings.AGENTCORE_MEMORY_ID,
            actor_id=user_id,
            session_id=session_id or f"session-{user_id}",
            region=settings.AWS_REGION,
            namespace=f"/users/{user_id}/consignado",
        ).tools

        for t in ltm_tools:
            agent.tool_registry.register_tool(t)
    except Exception as e:
        logger.warning("LTM tools não disponíveis: %s", e)
