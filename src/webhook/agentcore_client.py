"""Cliente do AgentCore Runtime e Memory para o Lambda handler.

invoke_agent_runtime: envia mensagem do usuário ao AgentCore e retorna resposta.
save_conversation_to_memory: persiste turno de conversa na LTM (AgentCore Memory).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger(__name__)

_RUNTIME_ARN_ENV = "AGENTCORE_RUNTIME_ARN"
_MEMORY_ID_ENV = "AGENTCORE_MEMORY_ID"
_AWS_REGION_ENV = "AWS_REGION"


def _get_region() -> str:
    return os.environ.get(_AWS_REGION_ENV, "us-east-1")


def invoke_agent_runtime(
    prompt: str,
    user_id: str,
    session_id: str,
) -> str:
    """Invoca o AgentCore Runtime com a mensagem do usuário.

    Args:
        prompt: Texto da mensagem do usuário.
        user_id: Identificador do usuário (telefone E.164).
        session_id: ID da sessão (≥ 33 caracteres, gerado pelo handler).

    Returns:
        Texto da resposta do agente.

    Raises:
        RuntimeError: Se o runtime ARN não estiver configurado ou houver erro na invocação.
    """
    runtime_arn = os.environ.get(_RUNTIME_ARN_ENV, "")
    if not runtime_arn:
        raise RuntimeError(f"Variável de ambiente não configurada: {_RUNTIME_ARN_ENV}")

    client = boto3.client("bedrock-agentcore-runtime", region_name=_get_region())

    try:
        resp = client.invoke_agent(
            agentRuntimeArn=runtime_arn,
            sessionId=session_id,
            userId=user_id,
            input={"text": prompt},
        )

        # Resposta é streaming — concatenar chunks
        output_parts = []
        for event in resp.get("outputStream", []):
            chunk = event.get("chunk", {})
            text = chunk.get("bytes", b"").decode("utf-8", errors="replace")
            if text:
                output_parts.append(text)

        response_text = "".join(output_parts).strip()
        if not response_text:
            logger.warning("invoke_agent_runtime: resposta vazia para session_id=%s", session_id)
            return ""

        return response_text

    except Exception as exc:
        logger.error("invoke_agent_runtime: erro — %s", exc, exc_info=True)
        raise RuntimeError(f"Falha ao invocar AgentCore Runtime: {exc}") from exc


def save_conversation_to_memory(
    memory_id: str,
    actor_id: str,
    session_id: str,
    user_message: str,
    agent_response: str,
) -> None:
    """Persiste um turno de conversa na LTM do AgentCore Memory.

    Args:
        memory_id: ID do AgentCore Memory store.
        actor_id: ID do ator (telefone do usuário).
        session_id: ID da sessão.
        user_message: Mensagem enviada pelo usuário.
        agent_response: Resposta gerada pelo agente.
    """
    try:
        client = boto3.client("bedrock-agentcore-memory", region_name=_get_region())
        client.create_event(
            memoryId=memory_id,
            actorId=actor_id,
            sessionId=session_id,
            messages=[
                {"role": "USER", "content": [{"text": user_message}]},
                {"role": "ASSISTANT", "content": [{"text": agent_response}]},
            ],
        )
        logger.debug("save_conversation_to_memory: ok actor_id=%s", actor_id[:6] + "****")
    except Exception as exc:
        logger.warning("save_conversation_to_memory: falhou (não crítico) — %s", exc)
