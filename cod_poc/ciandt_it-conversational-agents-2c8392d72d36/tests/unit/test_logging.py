"""Unit tests for src/utils/logging.py — zero AWS dependencies."""

from __future__ import annotations

import json
import logging

from src.utils.logging import JSONFormatter


class TestJSONFormatter:
    def test_outputs_valid_json(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="hello",
            args=None,
            exc_info=None,
        )
        output = fmt.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "hello"
        assert parsed["level"] == "INFO"

    def test_includes_extra_fields(self):
        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="req",
            args=None,
            exc_info=None,
        )
        record.duration_ms = 42
        output = fmt.format(record)
        parsed = json.loads(output)
        assert parsed["duration_ms"] == 42

    def test_includes_exception(self):
        fmt = JSONFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="",
                lineno=0,
                msg="err",
                args=None,
                exc_info=sys.exc_info(),
            )
        output = fmt.format(record)
        parsed = json.loads(output)
        assert "ValueError" in parsed["exception"]
