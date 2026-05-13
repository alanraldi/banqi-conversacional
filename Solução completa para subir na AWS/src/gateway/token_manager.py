"""OAuth2 token manager para AgentCore Gateway (Cognito Client Credentials).

Cache de token com renovação automática antes da expiração.
"""

from __future__ import annotations

import logging
import os
import time
from threading import Lock

import httpx

logger = logging.getLogger(__name__)

_EXPIRY_BUFFER_SECONDS = 60  # renova 60s antes de expirar


class GatewayTokenManager:
    """Singleton thread-safe para gerenciar o token OAuth2 do Gateway."""

    _instance: GatewayTokenManager | None = None
    _lock: Lock = Lock()

    def __init__(self) -> None:
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._token_lock = Lock()

    @classmethod
    def get_instance(cls) -> "GatewayTokenManager":
        """Retorna a instância singleton."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def get_token(self) -> str:
        """Retorna o token OAuth2 válido, renovando se necessário."""
        with self._token_lock:
            if self._token and time.time() < self._expires_at - _EXPIRY_BUFFER_SECONDS:
                return self._token
            self._token = self._fetch_token()
            return self._token

    def _fetch_token(self) -> str:
        """Obtém novo token do Cognito via Client Credentials."""
        client_id = os.environ.get("GATEWAY_CLIENT_ID", "")
        client_secret = os.environ.get("GATEWAY_CLIENT_SECRET", "")
        token_endpoint = os.environ.get("GATEWAY_TOKEN_ENDPOINT", "")
        scope = os.environ.get("GATEWAY_SCOPE", "")

        if not all([client_id, client_secret, token_endpoint]):
            raise RuntimeError(
                "Gateway OAuth não configurado. "
                "Verifique GATEWAY_CLIENT_ID, GATEWAY_CLIENT_SECRET, GATEWAY_TOKEN_ENDPOINT."
            )

        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    token_endpoint,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "scope": scope,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            token = data["access_token"]
            expires_in = data.get("expires_in", 3600)
            self._expires_at = time.time() + expires_in
            logger.info("GatewayTokenManager: novo token obtido, expira em %ds", expires_in)
            return token

        except Exception as exc:
            logger.error("GatewayTokenManager: falha ao obter token — %s", exc)
            raise RuntimeError(f"Falha ao obter token do Gateway: {exc}") from exc
