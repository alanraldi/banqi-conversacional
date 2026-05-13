"""Gateway Token Manager — thread-safe singleton OAuth com cleanup e retry.

Fix C2: resource leak — cleanup() fecha httpx.Client.
Fix C3: no fallback — raise explícito se token não obtido.
"""

from __future__ import annotations

import logging
import os
import threading
import time

import httpx

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0
_TOKEN_BUFFER_SECONDS = 300


class GatewayTokenManager:
    """Thread-safe singleton para gerenciar tokens OAuth do AgentCore Gateway."""

    _instance: GatewayTokenManager | None = None
    _lock = threading.Lock()

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        token_endpoint: str,
        scope: str,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_endpoint = token_endpoint
        self._scope = scope
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._http_client: httpx.Client | None = None

    @classmethod
    def get_instance(cls) -> GatewayTokenManager:
        """Thread-safe singleton with double-check locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    config = _load_gateway_config()
                    cls._instance = cls(**config)
        return cls._instance

    def get_token(self) -> str:
        """Obtain valid OAuth token with retry. Fail-fast on failure (Fix C3).

        Returns:
            Valid OAuth access token.

        Raises:
            RuntimeError: If token cannot be obtained after retries.
        """
        if self._token and time.time() < self._expires_at:
            return self._token

        if self._http_client is None:
            self._http_client = httpx.Client(timeout=30.0)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self._http_client.post(
                    self._token_endpoint,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "scope": self._scope,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                response.raise_for_status()
                data = response.json()

                self._token = data["access_token"]
                expires_in = int(data.get("expires_in", 3600))
                buffer = min(_TOKEN_BUFFER_SECONDS, expires_in // 2)
                self._expires_at = time.time() + expires_in - buffer

                logger.info("Gateway token obtained", extra={"expires_in": expires_in})
                return self._token

            except (httpx.HTTPError, KeyError):
                if attempt < _MAX_RETRIES:
                    wait = _BACKOFF_BASE * (2 ** (attempt - 1))
                    logger.warning(
                        "Token request failed (attempt %d/%d), retrying in %.1fs",
                        attempt,
                        _MAX_RETRIES,
                        wait,
                    )
                    time.sleep(wait)

        raise RuntimeError(f"Failed to obtain gateway token after {_MAX_RETRIES} attempts")

    def cleanup(self) -> None:
        """Close HTTP client and reset state. Called on shutdown."""
        if self._http_client:
            self._http_client.close()
            self._http_client = None
        self._token = None
        self._expires_at = 0.0
        with GatewayTokenManager._lock:
            GatewayTokenManager._instance = None
        logger.info("GatewayTokenManager cleaned up")


def _load_gateway_config() -> dict[str, str]:
    """Load gateway config from env vars.

    Returns:
        Dict with client_id, client_secret, token_endpoint, scope.

    Raises:
        ValueError: If required env vars are missing.
    """
    required = {
        "client_id": "GATEWAY_CLIENT_ID",
        "client_secret": "GATEWAY_CLIENT_SECRET",
        "token_endpoint": "GATEWAY_TOKEN_ENDPOINT",
        "scope": "GATEWAY_SCOPE",
    }

    config: dict[str, str] = {}
    missing: list[str] = []

    for key, env_var in required.items():
        val = os.getenv(env_var)
        if not val:
            missing.append(env_var)
        else:
            config[key] = val

    if missing:
        raise ValueError(f"Missing gateway env vars: {', '.join(missing)}")

    return config
