"""MockChannelAdapter — validates that ChannelAdapter ABC is extensible.

Proves a new channel can be added by implementing only receive_message
and send_response, without modifying any orchestration code (agents, memory).

This module lives in tests/ — not shipped to production.
"""

from __future__ import annotations

from typing import Any

from src.channels.base import ChannelAdapter, IncomingMessage, OutgoingResponse


class MockChannelAdapter(ChannelAdapter):
    """In-memory channel adapter for testing extensibility."""

    def __init__(self) -> None:
        self.sent: list[OutgoingResponse] = []
        self.typing_users: list[str] = []

    def receive_message(self, raw_event: dict[str, Any]) -> IncomingMessage | None:
        text = raw_event.get("text")
        user_id = raw_event.get("user_id")
        if not text or not user_id:
            return None
        return IncomingMessage(text=text, user_id=user_id, channel="mock")

    def send_response(self, response: OutgoingResponse) -> bool:
        self.sent.append(response)
        return True

    def send_typing_indicator(self, user_id: str) -> None:
        self.typing_users.append(user_id)


def test_mock_adapter_receives_message():
    """New channel can parse raw events into IncomingMessage."""
    adapter = MockChannelAdapter()
    msg = adapter.receive_message({"text": "hello", "user_id": "u1"})
    assert msg is not None
    assert msg.text == "hello"
    assert msg.user_id == "u1"
    assert msg.channel == "mock"


def test_mock_adapter_returns_none_for_invalid_event():
    """Returns None when raw event is missing required fields."""
    adapter = MockChannelAdapter()
    assert adapter.receive_message({}) is None
    assert adapter.receive_message({"text": "hello"}) is None


def test_mock_adapter_sends_response():
    """New channel can send responses without touching orchestration."""
    adapter = MockChannelAdapter()
    resp = OutgoingResponse(text="hi", user_id="u1")
    assert adapter.send_response(resp) is True
    assert adapter.sent == [resp]


def test_mock_adapter_typing_indicator():
    """Optional method works with override."""
    adapter = MockChannelAdapter()
    adapter.send_typing_indicator("u1")
    assert adapter.typing_users == ["u1"]


def test_mock_adapter_verify_webhook_default():
    """verify_webhook returns None by default (not overridden)."""
    adapter = MockChannelAdapter()
    assert adapter.verify_webhook({"hub.mode": "subscribe"}) is None


def test_orchestration_does_not_import_channels():
    """Orchestration layer (agents, memory) has zero imports from channels/."""
    import ast
    from pathlib import Path

    orchestration_dirs = ["src/agents", "src/memory", "src/config", "src/domain"]
    project = Path(__file__).resolve().parents[3]

    for dir_name in orchestration_dirs:
        dir_path = project / dir_name
        if not dir_path.exists():
            continue
        for py_file in dir_path.glob("*.py"):
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    module = getattr(node, "module", "") or ""
                    names = [a.name for a in node.names] if hasattr(node, "names") else []
                    full = module + " ".join(names)
                    assert "channels" not in full, f"{py_file.name} imports from channels/ — violates architecture"
