"""Unit tests for src/channels/whatsapp/models.py — zero AWS dependencies."""

from __future__ import annotations

from src.channels.whatsapp.models import WebhookPayload

_SAMPLE_PAYLOAD = {
    "object": "whatsapp_business_account",
    "entry": [
        {
            "id": "123",
            "changes": [
                {
                    "value": {
                        "messaging_product": "whatsapp",
                        "metadata": {"display_phone_number": "15551234", "phone_number_id": "pid1"},
                        "messages": [
                            {
                                "id": "msg1",
                                "from": "5511999887766",
                                "timestamp": "1234567890",
                                "type": "text",
                                "text": {"body": "Hello"},
                            }
                        ],
                    },
                    "field": "messages",
                }
            ],
        }
    ],
}


class TestWebhookPayload:
    def test_parse_valid_payload(self):
        p = WebhookPayload(**_SAMPLE_PAYLOAD)
        assert p.object == "whatsapp_business_account"

    def test_extract_messages(self):
        p = WebhookPayload(**_SAMPLE_PAYLOAD)
        msgs = p.extract_messages()
        assert len(msgs) == 1
        assert msgs[0].from_ == "5511999887766"
        assert msgs[0].text.body == "Hello"

    def test_extract_messages_empty_when_no_messages(self):
        payload = {
            "object": "whatsapp_business_account",
            "entry": [{"id": "1", "changes": [{"value": {}, "field": "messages"}]}],
        }
        p = WebhookPayload(**payload)
        assert p.extract_messages() == []

    def test_text_body_max_length(self):
        import pytest
        from pydantic import ValidationError

        long_payload = _SAMPLE_PAYLOAD.copy()
        long_payload["entry"] = [
            {
                "id": "1",
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "id": "m1",
                                    "from": "123",
                                    "timestamp": "0",
                                    "type": "text",
                                    "text": {"body": "x" * 5000},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ]
        with pytest.raises(ValidationError):
            WebhookPayload(**long_payload)
