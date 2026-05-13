"""Staging invocation — validates supervisor processes messages."""

import httpx
import pytest


@pytest.mark.staging
def test_invocation_returns_result(staging_url: str) -> None:
    resp = httpx.post(
        f"{staging_url}/invocations",
        json={"prompt": "Olá", "user_id": "e2e-test"},
        timeout=30,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert len(data["result"]) > 0


@pytest.mark.staging
def test_empty_prompt_returns_error_message(staging_url: str) -> None:
    resp = httpx.post(
        f"{staging_url}/invocations",
        json={"prompt": "", "user_id": "e2e-test"},
        timeout=10,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
