"""Unit tests for src/agents/context.py — zero AWS dependencies."""

from __future__ import annotations

import threading

from src.agents.context import SessionContext


class TestSessionContext:
    """C1: Thread-safe session context."""

    def test_set_and_get(self):
        ctx = SessionContext()
        ctx.set(user_id="u1", session_id="s1")
        snap = ctx.get()
        assert snap.user_id == "u1"
        assert snap.session_id == "s1"

    def test_default_is_none(self):
        ctx = SessionContext()
        snap = ctx.get()
        assert snap.user_id is None
        assert snap.session_id is None

    def test_clear(self):
        ctx = SessionContext()
        ctx.set(user_id="u1")
        ctx.clear()
        assert ctx.get().user_id is None

    def test_thread_isolation(self):
        ctx = SessionContext()
        ctx.set(user_id="main")
        results = {}

        def worker():
            ctx.set(user_id="worker")
            results["worker"] = ctx.get().user_id

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert ctx.get().user_id == "main"
        assert results["worker"] == "worker"

    def test_immutable_snapshot(self):
        ctx = SessionContext()
        ctx.set(user_id="u1")
        snap = ctx.get()
        # frozen dataclass — cannot mutate
        try:
            snap.user_id = "changed"
            assert False, "Should have raised"
        except AttributeError:
            pass
