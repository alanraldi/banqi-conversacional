"""Staging health check — validates runtime is alive."""

import httpx
import pytest


@pytest.mark.staging
def test_ping(staging_url: str) -> None:
    resp = httpx.get(f"{staging_url}/ping", timeout=10)
    assert resp.status_code == 200
    assert "Healthy" in resp.text
