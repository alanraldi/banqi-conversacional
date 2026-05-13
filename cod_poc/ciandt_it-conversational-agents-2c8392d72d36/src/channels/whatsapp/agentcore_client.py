"""AgentCore Runtime client — invokes agent and persists memory from WhatsApp Lambda.

Agent name from env var (not hardcoded). Logs latency and errors.
create_event saves USER+ASSISTANT messages to AgentCore Memory (feeds LTM strategies).
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

import boto3
import botocore.config

logger = logging.getLogger(__name__)

_AGENT_NAME_ENV = "AGENTCORE_AGENT_NAME"
_TIMEOUT_ENV = "AGENTCORE_TIMEOUT"

# Lazy singleton — reused across Lambda warm starts
_client: Any = None  # boto3 bedrock-agentcore client


def _get_client() -> Any:
    """Get or create boto3 bedrock-agentcore client (singleton)."""
    global _client
    if _client is None:
        timeout = int(os.environ.get(_TIMEOUT_ENV, "30"))
        _client = boto3.client(
            "bedrock-agentcore",
            config=botocore.config.Config(read_timeout=timeout, connect_timeout=10),
        )
    return _client


def save_conversation_to_memory(
    memory_id: str,
    actor_id: str,
    session_id: str,
    user_message: str,
    agent_response: str,
) -> None:
    """Persist USER+ASSISTANT turn to AgentCore Memory via create_event.

    Feeds memory strategies (SEMANTIC → facts, USER_PREFERENCE → preferences,
    SUMMARIZATION → summaries). Without this, LTM context is lost between sessions.
    """
    client = _get_client()
    try:
        client.create_event(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
            eventTimestamp=datetime.now(tz=UTC),
            payload=[
                {"conversational": {"content": {"text": user_message}, "role": "USER"}},
                {"conversational": {"content": {"text": agent_response}, "role": "ASSISTANT"}},
            ],
        )
        logger.info("Memory event saved", extra={"session_id": session_id})
    except Exception as e:
        logger.warning("Failed to save memory event: %s", e)


def invoke_agent_runtime(
    prompt: str,
    user_id: str,
    session_id: str,
) -> str:
    """Invoke AgentCore Runtime and return agent response text.

    Args:
        prompt: User message.
        user_id: Phone number or user identifier.
        session_id: Conversation session ID.

    Returns:
        Agent response text.

    Raises:
        RuntimeError: If invocation fails.
    """
    agent_name = os.environ.get(_AGENT_NAME_ENV)
    if not agent_name:
        raise RuntimeError(f"Missing env var: {_AGENT_NAME_ENV}")

    client = _get_client()

    payload = json.dumps(
        {
            "prompt": prompt,
            "phone_number": user_id,
            "session_id": session_id,
        }
    ).encode("utf-8")

    start = time.monotonic()
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_name,
            runtimeSessionId=session_id,
            payload=payload,
        )
        body = response["response"].read().decode("utf-8")
        result = json.loads(body)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.info("AgentCore invoked", extra={"duration_ms": elapsed_ms})
        return result.get("result", str(result))
    except Exception as e:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.error("AgentCore invocation failed: %s", e, extra={"duration_ms": elapsed_ms})
        raise RuntimeError(f"AgentCore invocation failed: {e}") from e
