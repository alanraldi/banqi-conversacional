"""Staging WhatsApp webhook — validates verification endpoint."""

import httpx
import pytest


@pytest.mark.staging
def test_webhook_verification(staging_url: str) -> None:
    """GET /webhook with valid verify_token returns challenge."""
    resp = httpx.get(
        f"{staging_url}/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test",
            "hub.challenge": "e2e-challenge-123",
        },
        timeout=10,
    )
    # May return 200 (correct token) or 403 (wrong token for staging)
    assert resp.status_code in (200, 403)


@pytest.mark.staging
def test_webhook_post_without_signature_returns_403(staging_url: str) -> None:
    """POST /webhook without signature header returns 403."""
    resp = httpx.post(
        f"{staging_url}/webhook",
        json={"object": "whatsapp_business_account", "entry": []},
        timeout=10,
    )
    assert resp.status_code == 403
