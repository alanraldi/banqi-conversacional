"""Agent Factory — creates Supervisor + sub-agents dynamically from domain.yaml.

Implements Agents-as-Tools pattern: each sub-agent is registered as a @tool
on the Supervisor, which decides which to invoke based on user intent.

Performance: heavy setup (model, prompts, tools) is cached. Only per-request
setup (session context, memory) is done on each call.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Any

from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models import BedrockModel

from src.agents.context import SessionContext
from src.config.settings import get_settings
from src.domain.loader import get_prompt, load_domain_config
from src.domain.schema import DomainConfig, SubAgentConfig

logger = logging.getLogger(__name__)

# Singleton thread-local context (Fix C1)
session_context = SessionContext()


def create_supervisor(
    *,
    user_id: str | None = None,
    session_id: str | None = None,
) -> Agent:
    """Create Supervisor Agent with sub-agents as tools.

    Heavy setup (model, prompts, delegate tools) is cached.
    Per-request setup (session context, memory, conversation manager) is fresh.
    """
    cfg = load_domain_config()
    settings = get_settings()

    session_context.set(user_id=user_id, session_id=session_id)

    model = _get_cached_model(cfg.supervisor.model_id_env)
    system_prompt = _get_cached_prompt(cfg.supervisor.prompt_file)
    delegate_tools = _get_cached_delegate_tools()

    conversation_manager = SlidingWindowConversationManager(
        window_size=settings.CONVERSATION_WINDOW_SIZE,
        should_truncate_results=True,
    )

    # Memory session_manager MUST be passed in constructor for hooks to register
    sm = _create_session_manager(cfg, user_id, session_id) if user_id else None
    logger.info(
        "Session manager: %s (user_id=%s, session_id=%s)", type(sm).__name__ if sm else "None", user_id, session_id
    )

    supervisor = Agent(
        name="Supervisor Agent",
        model=model,
        tools=list(delegate_tools),
        system_prompt=system_prompt,
        agent_id="supervisor_agent",
        description=cfg.supervisor.description,
        conversation_manager=conversation_manager,
        session_manager=sm,
    )

    # LTM tools can be added after construction
    if user_id:
        _attach_ltm_tools(supervisor, user_id, session_id)

    return supervisor


@lru_cache(maxsize=4)
def _get_cached_model(model_id_env: str) -> BedrockModel:
    """Cache BedrockModel instances — one per model_id_env."""
    model_id = os.environ.get(model_id_env)
    if not model_id:
        raise ValueError(f"Missing env var: {model_id_env}")
    return BedrockModel(
        model_id=model_id,
        cache_tools="default",
        **_guardrail_kwargs(),
    )


@lru_cache(maxsize=8)
def _get_cached_prompt(prompt_file: str) -> list[dict[str, Any]]:
    """Cache prompt text — read from disk once. TTL 1h for Bedrock prompt caching."""
    text = get_prompt(prompt_file)
    return [
        {"text": text},
        {"cachePoint": {"type": "default"}},
    ]


@lru_cache(maxsize=1)
def _get_cached_delegate_tools() -> tuple[Any, ...]:
    """Cache delegate tools — created once from domain.yaml."""
    cfg = load_domain_config()
    tools = tuple(_make_delegate_tool(key, sa) for key, sa in cfg.sub_agents.items())
    logger.info(
        "Delegate tools created",
        extra={"sub_agents": list(cfg.sub_agents.keys())},
    )
    return tools


def _make_delegate_tool(key: str, agent_cfg: SubAgentConfig) -> Any:
    """Create a @tool function that delegates to a sub-agent."""
    docstring = agent_cfg.tool_docstring

    @tool(name=f"{key}_assistant")
    def delegate(query: str) -> str:
        ctx = session_context.get()
        sub = _create_sub_agent(agent_cfg, key, ctx.user_id, ctx.session_id)
        result = sub(query)
        return str(result)

    delegate.__doc__ = docstring
    return delegate


def _create_sub_agent(
    agent_cfg: SubAgentConfig,
    key: str,
    user_id: str | None,
    session_id: str | None,
) -> Agent:
    """Create sub-agent from config. Model and prompt are cached."""
    tools = _get_tools_for_agent(agent_cfg)
    return Agent(
        name=agent_cfg.name,
        model=_get_cached_model(agent_cfg.model_id_env),
        tools=tools,
        system_prompt=_get_cached_prompt(agent_cfg.prompt_file),
        agent_id=f"{key}_agent",
        description=agent_cfg.description,
    )


# --- Tool provider registry (maps tools_source → loader function) ---


def _get_tools_for_agent(agent_cfg: SubAgentConfig) -> list:
    """Resolve tools from agent config tools_source. Degraded mode if unavailable."""
    provider = _TOOL_PROVIDERS.get(agent_cfg.tools_source)
    if not provider:
        logger.warning("Unknown tools_source '%s' — no tools", agent_cfg.tools_source)
        return []
    return provider()


def _get_gateway_tools() -> list:
    """Load MCP tools from AgentCore Gateway. Empty list if not configured."""
    endpoint = os.environ.get("AGENTCORE_GATEWAY_ENDPOINT")
    if not endpoint:
        logger.warning("AGENTCORE_GATEWAY_ENDPOINT not set — running without MCP tools")
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
        logger.warning("Gateway MCP tools unavailable — degraded mode: %s", e)
        return []


def _get_kb_tools() -> list:
    """Return Bedrock KB retrieve tool if configured."""
    if not os.environ.get("KNOWLEDGE_BASE_ID"):
        logger.warning("KNOWLEDGE_BASE_ID not set — running without KB tool")
        return []
    try:
        from strands_tools import retrieve

        return [retrieve]
    except Exception as e:
        logger.warning("KB retrieve tool unavailable: %s", e)
        return []


_TOOL_PROVIDERS: dict[str, Any] = {
    "gateway_mcp": _get_gateway_tools,
    "bedrock_kb": _get_kb_tools,
    "none": lambda: [],
}


def _guardrail_kwargs() -> dict[str, Any]:
    """Return Bedrock Guardrails kwargs if configured.

    - guardrail_redact_input=False: preserva contexto da conversa (PII masking via regex nos logs)
    - guardrail_latest_message=True: avalia só a última mensagem, evita multi-turn conversation trap
    - guardrail_redact_output=False: PII mascarado mas mensagem preservada
    """
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
    cfg: DomainConfig,
    user_id: str,
    session_id: str | None,
) -> Any:
    """Create AgentCoreMemorySessionManager. Returns None if not configured."""
    settings = get_settings()
    if not settings.AGENTCORE_MEMORY_ID:
        logger.warning("AGENTCORE_MEMORY_ID not set — running without memory")
        return None
    try:
        from bedrock_agentcore.memory.integrations.strands.config import (
            AgentCoreMemoryConfig,
            RetrievalConfig,
        )
        from bedrock_agentcore.memory.integrations.strands.session_manager import (
            AgentCoreMemorySessionManager,
        )

        if not session_id:
            session_id = f"{cfg.agent.session_prefix}-{user_id}"

        retrieval_config = {
            f"/{ns.replace('{user_id}', user_id).replace('{session_id}', session_id)}": RetrievalConfig(
                top_k=nc.top_k, relevance_score=nc.relevance_score
            )
            for ns, nc in cfg.memory.namespaces.items()
        }

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
        logger.warning("Memory session manager creation failed — degraded mode: %s", e, exc_info=True)
        return None


def _attach_ltm_tools(agent: Agent, user_id: str, session_id: str | None) -> None:
    """Add LTM tools to agent (can be done after construction)."""
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
            namespace=f"/users/{user_id}",
        ).tools

        for t in ltm_tools:
            agent.tool_registry.register_tool(t)
    except Exception as e:
        logger.warning("LTM tools attach failed: %s", e)
