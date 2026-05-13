"""Thread-safe session context para banQi Consignado.

Armazena user_id (número de telefone WhatsApp) e session_id entre chamadas
dentro de um mesmo request, sem compartilhar estado entre threads/requests.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class _Ctx:
    """Snapshot imutável do contexto de sessão."""

    user_id: str | None = None
    session_id: str | None = None


class SessionContext:
    """Thread-local session context. Cada thread/request tem estado isolado."""

    def __init__(self) -> None:
        self._local = threading.local()

    def set(self, *, user_id: str | None = None, session_id: str | None = None) -> None:
        """Define o contexto para a thread atual."""
        self._local.ctx = _Ctx(user_id=user_id, session_id=session_id)

    def get(self) -> _Ctx:
        """Retorna o contexto atual (ou contexto vazio se não definido)."""
        return getattr(self._local, "ctx", _Ctx())

    def clear(self) -> None:
        """Limpa o contexto da thread atual."""
        self._local.ctx = _Ctx()
