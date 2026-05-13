"""Pydantic models for domain.yaml validation."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class DomainInfo(BaseModel):
    """Top-level domain metadata."""

    name: str = Field(min_length=1)
    slug: str = Field(min_length=1, pattern=r"^[a-z0-9][a-z0-9-]*$")
    description: str = ""
    language_default: str = "pt-BR"


class AgentInfo(BaseModel):
    """AgentCore runtime identifiers."""

    name: str = Field(min_length=1, pattern=r"^[a-zA-Z][a-zA-Z0-9_]{0,47}$")
    memory_name: str = Field(min_length=1)
    session_prefix: str = "session"


class SupervisorConfig(BaseModel):
    """Supervisor agent configuration."""

    prompt_file: str
    description: str = "Supervisor Agent"
    model_id_env: str = "SUPERVISOR_AGENT_MODEL_ID"


class SubAgentConfig(BaseModel):
    """Sub-agent configuration (loaded dynamically from YAML)."""

    name: str = Field(min_length=1)
    description: str = ""
    prompt_file: str
    tool_docstring: str = Field(min_length=1)
    model_id_env: str
    tools_source: str = Field(default="none", pattern=r"^(gateway_mcp|bedrock_kb|none)$")


class MemoryNamespaceConfig(BaseModel):
    """Memory namespace retrieval settings."""

    top_k: int = Field(default=3, ge=1)
    relevance_score: float = Field(default=0.5, ge=0.0, le=1.0)


class MemoryConfig(BaseModel):
    """Memory configuration with namespaces."""

    namespaces: dict[str, MemoryNamespaceConfig] = Field(default_factory=dict)


class ChannelConfig(BaseModel):
    """Channel (messaging interface) configuration."""

    enabled: bool = True
    type: str = "webhook"


class InterfaceConfig(BaseModel):
    """UI-facing messages and branding."""

    welcome_message: str = "Hello! How can I help?"
    author_name: str = "Assistant"


class ErrorMessagesConfig(BaseModel):
    """User-facing error messages."""

    generic: str = "Sorry, an error occurred. Please try again."
    empty_input: str = "Please send your question or request."


class DomainConfig(BaseModel):
    """Root configuration — validated on startup, fail-fast on invalid."""

    domain: DomainInfo
    agent: AgentInfo
    supervisor: SupervisorConfig
    sub_agents: dict[str, SubAgentConfig] = Field(min_length=1)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    channels: dict[str, ChannelConfig] = Field(default_factory=dict)
    interface: InterfaceConfig = Field(default_factory=InterfaceConfig)
    error_messages: ErrorMessagesConfig = Field(default_factory=ErrorMessagesConfig)

    @model_validator(mode="after")
    def validate_prompt_paths_safe(self) -> DomainConfig:
        """Reject prompt paths that escape the project directory (path traversal)."""
        all_paths = [self.supervisor.prompt_file] + [a.prompt_file for a in self.sub_agents.values()]
        for p in all_paths:
            normalized = Path(p).as_posix()
            if normalized.startswith("/") or ".." in normalized:
                raise ValueError(f"Prompt path must be relative without '..': {p}")
        return self
