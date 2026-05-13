"""Unit tests for src/utils/agent_helpers.py — zero AWS dependencies."""

from __future__ import annotations

from src.utils.agent_helpers import extract_text


class TestExtractText:
    def test_extracts_from_strands_format(self):
        class FakeResult:
            message = {"content": [{"text": "Hello!"}]}

        assert extract_text(FakeResult()) == "Hello!"

    def test_fallback_to_str(self):
        assert extract_text("plain string") == "plain string"

    def test_empty_content_list(self):
        class FakeResult:
            message = {"content": []}

        result = FakeResult()
        assert extract_text(result) == str(result)

    def test_no_message_attr(self):
        assert extract_text(42) == "42"
