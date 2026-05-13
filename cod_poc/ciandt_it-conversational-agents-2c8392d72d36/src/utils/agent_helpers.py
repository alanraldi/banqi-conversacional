"""Agent response helpers — shared utilities for extracting text from Strands Agent results."""

from __future__ import annotations

from typing import Any


def extract_text(result: Any) -> str:
    """Extract text from Strands Agent result.

    Handles the standard Strands response format:
    result.message = {"content": [{"text": "..."}]}
    """
    if hasattr(result, "message") and isinstance(result.message, dict):
        content = result.message.get("content", [])
        if content and isinstance(content[0], dict):
            return content[0].get("text", str(result))
    return str(result)
