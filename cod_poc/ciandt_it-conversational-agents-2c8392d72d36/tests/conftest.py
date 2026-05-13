"""Global conftest — factories and fixtures shared across all test levels."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.domain.schema import DomainConfig

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def make_domain_config(**overrides: Any) -> DomainConfig:
    """Create a valid DomainConfig with sensible defaults. Override any field."""
    base: dict[str, Any] = {
        "domain": {
            "name": "TestBot",
            "slug": "test-bot",
            "description": "Test assistant",
            "language_default": "pt-BR",
        },
        "agent": {
            "name": "test_multi_agent",
            "memory_name": "TestMemory",
            "session_prefix": "test",
        },
        "supervisor": {
            "prompt_file": "prompts/supervisor.md",
            "description": "Test Supervisor",
            "model_id_env": "SUPERVISOR_AGENT_MODEL_ID",
        },
        "sub_agents": {
            "services": {
                "name": "Services Agent",
                "description": "Test services",
                "prompt_file": "prompts/services.md",
                "tool_docstring": "Test tool",
                "model_id_env": "SERVICES_AGENT_MODEL_ID",
            },
        },
        "interface": {
            "welcome_message": "Hello test!",
            "author_name": "TestBot",
        },
        "error_messages": {
            "generic": "Test error.",
            "empty_input": "Send something.",
        },
    }
    base.update(overrides)
    return DomainConfig(**base)


def make_whatsapp_payload(
    message_text: str = "Olá",
    phone: str = "5511999999999",
    message_id: str = "wamid.test123",
) -> dict[str, Any]:
    """Create a valid WhatsApp webhook payload dict."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-1",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "phone-id-1",
                            },
                            "messages": [
                                {
                                    "from": phone,
                                    "id": message_id,
                                    "timestamp": "1234567890",
                                    "type": "text",
                                    "text": {"body": message_text},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def make_whatsapp_status_payload(
    status: str = "delivered",
    message_id: str = "wamid.test123",
) -> dict[str, Any]:
    """Create a WhatsApp status update payload (no messages)."""
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "entry-1",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550001111",
                                "phone_number_id": "phone-id-1",
                            },
                            "statuses": [
                                {
                                    "id": message_id,
                                    "status": status,
                                    "timestamp": "1234567890",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def make_webhook_signature(payload: bytes, secret: str) -> str:
    """Generate a valid X-Hub-Signature-256 header value."""
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def domain_config_fixture() -> DomainConfig:
    """A valid DomainConfig for testing."""
    return make_domain_config()


@pytest.fixture()
def valid_domain_dict() -> dict[str, Any]:
    """Raw dict that can be passed to DomainConfig(**d)."""
    cfg = make_domain_config()
    return json.loads(cfg.model_dump_json())


@pytest.fixture()
def valid_domain_yaml_file(tmp_path: Path) -> Path:
    """Write a valid domain.yaml to a temp directory with prompt files."""
    # Create prompt files
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "supervisor.md").write_text("You are a supervisor.")
    (prompts_dir / "services.md").write_text("You are a services agent.")

    cfg = make_domain_config()
    yaml_path = tmp_path / "domain.yaml"
    yaml_path.write_text(yaml.dump(json.loads(cfg.model_dump_json())))
    return yaml_path


@pytest.fixture()
def malformed_domain_yaml_file(tmp_path: Path) -> Path:
    """domain.yaml with missing required fields."""
    yaml_path = tmp_path / "domain.yaml"
    yaml_path.write_text("domain:\n  slug: broken\n")
    return yaml_path


@pytest.fixture()
def whatsapp_text_message_payload() -> dict[str, Any]:
    """Valid WhatsApp text message payload."""
    return make_whatsapp_payload()


@pytest.fixture()
def whatsapp_status_payload() -> dict[str, Any]:
    """WhatsApp status update payload (no user messages)."""
    return make_whatsapp_status_payload()


@pytest.fixture()
def env_with_model_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set model ID env vars needed by Agent Factory."""
    monkeypatch.setenv("SUPERVISOR_AGENT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    monkeypatch.setenv("SERVICES_AGENT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    monkeypatch.setenv("KNOWLEDGE_AGENT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    monkeypatch.setenv("AGENTCORE_MEMORY_ID", "mem-test-123")
