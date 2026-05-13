"""Channel adapter pattern — extensible interface for messaging channels.

All channels (WhatsApp, Chainlit, future Telegram/Slack) implement
ChannelAdapter. Orchestration layer (agents, memory) never imports
from channels/ — only channels import from orchestration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class IncomingMessage:
    """Normalized incoming message from any channel."""

    text: str
    user_id: str
    channel: str
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OutgoingResponse:
    """Response to send back through a channel."""

    text: str
    user_id: str


class ChannelAdapter(ABC):
    """Abstract base for all channel adapters.

    Required: receive_message, send_response
    Optional (with defaults): verify_webhook, send_typing_indicator
    """

    @abstractmethod
    def receive_message(self, raw_event: dict[str, Any]) -> IncomingMessage | None:
        """Parse raw event into IncomingMessage. Returns None if not a user message."""
        ...

    @abstractmethod
    def send_response(self, response: OutgoingResponse) -> bool:
        """Send response back to channel. Returns True on success."""
        ...

    def verify_webhook(self, params: dict[str, str]) -> str | None:
        """Verify webhook subscription (e.g., Meta hub.challenge). Returns challenge or None."""
        return None

    def send_typing_indicator(self, user_id: str) -> None:
        """Send typing/read indicator. No-op by default."""
