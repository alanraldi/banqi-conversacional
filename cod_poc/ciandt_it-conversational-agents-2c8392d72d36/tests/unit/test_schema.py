"""Unit tests for src/domain/schema.py — zero AWS dependencies."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.domain.schema import DomainConfig, DomainInfo


def _minimal_config(**overrides) -> dict:
    base = {
        "domain": {"name": "Test", "slug": "test-bot"},
        "agent": {"name": "TestAgent", "memory_name": "test-mem"},
        "supervisor": {"prompt_file": "prompts/supervisor.md"},
        "sub_agents": {
            "svc": {
                "name": "Svc",
                "prompt_file": "prompts/svc.md",
                "tool_docstring": "Does stuff",
                "model_id_env": "SVC_MODEL_ID",
            }
        },
    }
    base.update(overrides)
    return base


class TestDomainInfo:
    def test_valid_slug(self):
        assert DomainInfo(name="Test", slug="my-bot-123").slug == "my-bot-123"

    def test_invalid_slug_uppercase(self):
        with pytest.raises(ValidationError):
            DomainInfo(name="Test", slug="MyBot")

    def test_invalid_slug_starts_with_dash(self):
        with pytest.raises(ValidationError):
            DomainInfo(name="Test", slug="-bad")


class TestDomainConfig:
    def test_valid_minimal(self):
        cfg = DomainConfig(**_minimal_config())
        assert cfg.domain.name == "Test"
        assert len(cfg.sub_agents) == 1

    def test_rejects_empty_sub_agents(self):
        with pytest.raises(ValidationError):
            DomainConfig(**_minimal_config(sub_agents={}))

    def test_rejects_path_traversal(self):
        with pytest.raises(ValidationError, match="relative"):
            DomainConfig(
                **_minimal_config(
                    supervisor={"prompt_file": "../../../etc/passwd"},
                )
            )

    def test_rejects_absolute_path(self):
        with pytest.raises(ValidationError, match="relative"):
            DomainConfig(
                **_minimal_config(
                    supervisor={"prompt_file": "/etc/passwd"},
                )
            )

    def test_defaults(self):
        cfg = DomainConfig(**_minimal_config())
        assert cfg.error_messages.generic != ""
        assert cfg.interface.welcome_message != ""
