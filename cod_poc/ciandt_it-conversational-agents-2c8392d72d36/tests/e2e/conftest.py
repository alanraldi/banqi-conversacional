"""E2E staging conftest — provides staging URL and runtime client."""

from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--staging-url", default=os.getenv("STAGING_URL", ""))


@pytest.fixture(scope="session")
def staging_url(request: pytest.FixtureRequest) -> str:
    url = request.config.getoption("--staging-url")
    if not url:
        pytest.skip("--staging-url not provided")
    return url.rstrip("/")
