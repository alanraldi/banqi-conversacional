"""Pydantic models for WhatsApp Business API webhook payloads.

Parses the nested Meta webhook structure safely. Only text messages
are supported in v1 — other types are parsed but ignored by the processor.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WebhookTextBody(BaseModel):
    """Text message content."""

    body: str = Field(max_length=4096)


class WebhookMessage(BaseModel):
    """Individual message from webhook payload."""

    id: str
    from_: str = Field(alias="from")
    timestamp: str
    type: str
    text: WebhookTextBody | None = None

    model_config = {"populate_by_name": True}


class WebhookStatus(BaseModel):
    """Message delivery status update."""

    id: str
    status: str
    timestamp: str


class WebhookMetadata(BaseModel):
    """Webhook metadata with phone number ID."""

    display_phone_number: str = ""
    phone_number_id: str = ""


class WebhookValue(BaseModel):
    """Value block inside a webhook change."""

    messaging_product: str = "whatsapp"
    metadata: WebhookMetadata = Field(default_factory=WebhookMetadata)
    messages: list[WebhookMessage] | None = None
    statuses: list[WebhookStatus] | None = None


class WebhookChange(BaseModel):
    """Single change entry."""

    value: WebhookValue
    field: str = "messages"


class WebhookEntry(BaseModel):
    """Top-level entry in webhook payload."""

    id: str
    changes: list[WebhookChange]


class WebhookPayload(BaseModel):
    """Root webhook payload from Meta."""

    object: str
    entry: list[WebhookEntry]

    def extract_messages(self) -> list[WebhookMessage]:
        """Extract all messages from nested payload structure."""
        messages: list[WebhookMessage] = []
        for entry in self.entry:
            for change in entry.changes:
                if change.value.messages:
                    messages.extend(change.value.messages)
        return messages
