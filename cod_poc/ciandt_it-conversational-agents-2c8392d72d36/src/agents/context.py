"""Thread-safe session context — Fix C1 (replaces global mutable dict)."""

from __future__ import annotations

import threading
from dataclasses import dataclass


@dataclass(frozen=True)
class _Ctx:
    """Immutable session context snapshot."""

    user_id: str | None = None
    session_id: str | None = None


class SessionContext:
    """Thread-local session context. Each thread/request gets isolated state."""

    def __init__(self) -> None:
        self._local = threading.local()

    def set(self, *, user_id: str | None = None, session_id: str | None = None) -> None:
        self._local.ctx = _Ctx(user_id=user_id, session_id=session_id)

    def get(self) -> _Ctx:
        return getattr(self._local, "ctx", _Ctx())

    def clear(self) -> None:
        self._local.ctx = _Ctx()
