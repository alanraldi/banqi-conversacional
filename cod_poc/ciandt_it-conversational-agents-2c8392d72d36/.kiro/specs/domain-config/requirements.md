# Domain Config — Requirements

## Functional Requirements

### FR-DC-001: YAML-Based Domain Configuration
WHEN a developer creates a new domain
THE SYSTEM SHALL load all domain-specific settings from a single `domain.yaml` file located at `domains/{slug}/domain.yaml`
SO THAT no Python code changes are required to deploy a new domain.

### FR-DC-002: Schema Validation on Startup
WHEN the application starts and loads `domain.yaml`
THE SYSTEM SHALL validate the entire configuration against Pydantic v2 models
AND SHALL fail-fast with descriptive error messages if validation fails
SO THAT invalid configurations are caught before any request is processed.

### FR-DC-003: Domain Metadata
WHEN a domain configuration is loaded
THE SYSTEM SHALL require:
- `domain.name` (non-empty string) — display name
- `domain.slug` (lowercase alphanumeric + hyphens, starts with letter/digit) — used in AWS resource names
- `domain.description` (optional string)
- `domain.language_default` (string, default: "pt-BR")

### FR-DC-004: Agent Runtime Configuration
WHEN a domain configuration is loaded
THE SYSTEM SHALL require:
- `agent.name` (alphanumeric + underscore, max 48 chars) — AgentCore runtime identifier
- `agent.memory_name` (non-empty string) — AgentCore Memory store name
- `agent.session_prefix` (string, default: "session")

### FR-DC-005: Supervisor Agent Configuration
WHEN a domain configuration is loaded
THE SYSTEM SHALL require:
- `supervisor.prompt_file` (relative path to .md file)
- `supervisor.model_id_env` (env var name, default: "SUPERVISOR_AGENT_MODEL_ID")
- `supervisor.description` (optional string)

### FR-DC-006: Dynamic Sub-Agent Registration
WHEN a domain configuration is loaded
THE SYSTEM SHALL require at least one sub-agent in `sub_agents` (dict)
AND each sub-agent SHALL have:
- `name` (non-empty string)
- `prompt_file` (relative path to .md file)
- `tool_docstring` (non-empty string — used for agents-as-tools registration)
- `model_id_env` (env var name pointing to Bedrock model ID)
- `tools_source` (one of: `gateway_mcp`, `bedrock_kb`, `none`)

### FR-DC-007: Memory Namespace Configuration
WHEN a domain configuration includes `memory.namespaces`
THE SYSTEM SHALL validate each namespace with:
- `top_k` (integer >= 1, default: 3)
- `relevance_score` (float 0.0–1.0, default: 0.5)
AND namespace keys SHALL support template variables (e.g., `users/{user_id}/preferences`).

### FR-DC-008: Channel Configuration
WHEN a domain configuration includes `channels`
THE SYSTEM SHALL validate each channel with:
- `enabled` (boolean, default: true)
- `type` (string, default: "webhook")

### FR-DC-009: Interface and Error Messages
WHEN a domain configuration is loaded
THE SYSTEM SHALL provide defaults for:
- `interface.welcome_message` — displayed on first interaction
- `interface.author_name` — displayed as agent name in UI
- `error_messages.generic` — shown on unhandled errors
- `error_messages.empty_input` — shown when user sends empty message

### FR-DC-010: Environment Variable Resolution
WHEN the application starts
THE SYSTEM SHALL resolve `DOMAIN_DIR` environment variable to locate the active domain directory
WITH resolution order:
1. `DOMAIN_DIR` env var (absolute or relative to project root)
2. Default: `domains/banqi-banking`

### FR-DC-011: Model ID Environment Validation
WHEN a domain configuration is loaded
THE SYSTEM SHALL verify that all `model_id_env` values (supervisor + all sub-agents) exist as environment variables
AND SHALL fail-fast with a list of all missing variables if any are absent
SO THAT deployment errors are caught immediately, not at first request.

### FR-DC-012: Prompt File Loading
WHEN the agent factory requests a prompt
THE SYSTEM SHALL load the `.md` file from the path specified in `prompt_file`, relative to the active domain directory
AND SHALL fail-fast with `FileNotFoundError` if the file does not exist.

### FR-DC-013: Domain Template System
WHEN a developer wants to create a new domain
THE SYSTEM SHALL provide a `domains/_template/` directory containing:
- Pre-filled `domain.yaml` with placeholder values and inline documentation
- Stub prompt files for supervisor, services, and knowledge agents
- Empty `kb-docs/` directory
- `README.md` with quick start instructions

## Non-Functional Requirements

### NFR-DC-001: Thread Safety
WHEN multiple threads access the configuration simultaneously
THE SYSTEM SHALL use double-check locking to ensure the singleton is initialized exactly once
AND SHALL return the cached instance on all subsequent calls without acquiring the lock.

### NFR-DC-002: Immutability
WHEN the configuration is loaded
THE SYSTEM SHALL treat it as immutable for the lifetime of the process
AND SHALL NOT provide any mechanism to modify configuration at runtime (except `reset_config()` for testing).

### NFR-DC-003: Fail-Fast Semantics
WHEN any configuration error is detected (invalid YAML, missing fields, invalid values, missing env vars)
THE SYSTEM SHALL raise an exception immediately during startup
AND SHALL NOT fall back to defaults or partial configurations for required fields.

### NFR-DC-004: Path Traversal Protection
WHEN a `prompt_file` value contains `..` or starts with `/`
THE SYSTEM SHALL reject the configuration with a `ValidationError`
SO THAT prompt loading cannot escape the project directory.

### NFR-DC-005: Performance
WHEN `load_domain_config()` is called after initial load
THE SYSTEM SHALL return the cached singleton in O(1) without file I/O or YAML parsing.

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-DC-001 | Valid `domain.yaml` loads without errors | `test_schema.py::TestDomainConfig::test_valid_minimal` |
| AC-DC-002 | Empty `sub_agents` raises `ValidationError` | `test_schema.py::TestDomainConfig::test_rejects_empty_sub_agents` |
| AC-DC-003 | Path traversal in `prompt_file` raises `ValidationError` | `test_schema.py::TestDomainConfig::test_rejects_path_traversal` |
| AC-DC-004 | Absolute path in `prompt_file` raises `ValidationError` | `test_schema.py::TestDomainConfig::test_rejects_absolute_path` |
| AC-DC-005 | Invalid slug (uppercase) raises `ValidationError` | `test_schema.py::TestDomainInfo::test_invalid_slug_uppercase` |
| AC-DC-006 | Default values populated correctly | `test_schema.py::TestDomainConfig::test_defaults` |
| AC-DC-007 | Missing model env vars raises `OSError` | Manual verification / integration test |
| AC-DC-008 | `DOMAIN_DIR` env var overrides default path | Manual verification |
| AC-DC-009 | Thread-safe singleton returns same instance | Manual verification |
| AC-DC-010 | `banqi-banking/domain.yaml` loads successfully | `python -c "from src.domain.loader import load_domain_config; print(load_domain_config().domain.name)"` |
