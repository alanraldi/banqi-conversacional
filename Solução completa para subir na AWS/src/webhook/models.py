"""Modelos Pydantic para parsing dos payloads do WhatsApp e webhooks banQi."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TextContent(BaseModel):
    body: str


class IncomingMessage(BaseModel):
    id: str
    from_: str = Field(alias="from")
    type: str
    text: TextContent | None = None
    timestamp: str | None = None

    model_config = {"populate_by_name": True}


class Contact(BaseModel):
    profile: dict[str, Any] | None = None
    wa_id: str | None = None


class MetadataWpp(BaseModel):
    display_phone_number: str | None = None
    phone_number_id: str | None = None


class Value(BaseModel):
    messaging_product: str | None = None
    metadata: MetadataWpp | None = None
    contacts: list[Contact] = []
    messages: list[IncomingMessage] = []
    statuses: list[dict[str, Any]] = []


class Change(BaseModel):
    value: Value
    field: str | None = None


class Entry(BaseModel):
    id: str | None = None
    changes: list[Change] = []


class WhatsAppWebhookPayload(BaseModel):
    object: str | None = None
    entry: list[Entry] = []

    def extract_messages(self) -> list[IncomingMessage]:
        msgs = []
        for entry in self.entry:
            for change in entry.changes:
                msgs.extend(change.value.messages)
        return msgs


class BanqiWebhookPayload(BaseModel):
    """Payload genérico dos webhooks banQi."""

    event: str
    phone: str | None = None
    data: dict[str, Any] = {}
    errorCode: str | None = None
    newStatus: str | None = None
    idProposal: str | None = None
    idSimulation: str | None = None
    pdfUrl: str | None = None
