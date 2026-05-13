"""Chainlit adapter — dev/test interface for local testing.

Reads welcome_message, author_name from domain.yaml.
Routes messages through Supervisor Agent (same pipeline as WhatsApp).
Not for production — Chainlit is a dev dependency.

Usage: chainlit run src/channels/chainlit/app.py
"""

from __future__ import annotations

import logging
import uuid

import chainlit as cl

from src.agents.factory import create_supervisor
from src.domain.loader import load_domain_config
from src.domain.schema import DomainConfig
from src.utils.agent_helpers import extract_text
from src.utils.logging import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

_cfg: DomainConfig = load_domain_config()

# Fail-fast if channel disabled
if not _cfg.channels.get("chainlit", type("", (), {"enabled": True})).enabled:
    raise SystemExit("Chainlit channel is disabled in domain.yaml")


@cl.on_chat_start
async def on_start() -> None:
    """Display welcome message and init session."""
    session_id = f"chainlit-{uuid.uuid4()}"
    cl.user_session.set("session_id", session_id)
    await cl.Message(content=_cfg.interface.welcome_message).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    """Route message through Supervisor Agent."""
    session_id = cl.user_session.get("session_id")
    user_id = f"chainlit-{session_id}"

    try:
        supervisor = create_supervisor(user_id=user_id, session_id=session_id)
        result = supervisor(message.content)
        text = extract_text(result)
    except Exception as e:
        logger.error("Agent error: %s", e, exc_info=True)
        text = _cfg.error_messages.generic

    await cl.Message(content=text, author=_cfg.interface.author_name).send()
