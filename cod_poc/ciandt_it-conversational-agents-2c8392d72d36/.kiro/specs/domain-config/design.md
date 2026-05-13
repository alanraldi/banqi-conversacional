# Domain Config — Design

## Overview

The Domain Config module is the **core configuration system** of the conversational-agents framework. It enables domain-agnostic behavior by externalizing all domain-specific settings (agent names, prompts, sub-agents, memory, channels) into a single `domain.yaml` file per domain. The Python code never changes between domains — only the YAML and prompt files.

## Architecture

```
domains/
├── banqi-banking/          ← Active domain (set via DOMAIN_DIR)
│   ├── domain.yaml         ← Single source of truth
│   ├── prompts/
│   │   ├── supervisor.md
│   │   ├── services.md
│   │   └── knowledge.md
│   └── kb-docs/            ← Knowledge Base documents
└── _template/              ← Scaffold for new domains
    ├── domain.yaml
    ├── prompts/*.md
    └── kb-docs/.gitkeep

src/domain/
├── schema.py               ← Pydantic v2 models (validation)
└── loader.py               ← Singleton loader (thread-safe)
```

## Component Design

### 1. Schema (`src/domain/schema.py`)

11 Pydantic v2 models forming a strict validation hierarchy:

```
DomainConfig (root)
├── DomainInfo              → name, slug, description, language_default
├── AgentInfo               → name (AgentCore runtime), memory_name, session_prefix
├── SupervisorConfig        → prompt_file, description, model_id_env
├── SubAgentConfig (dict)   → name, description, prompt_file, tool_docstring, model_id_env, tools_source
├── MemoryConfig
│   └── MemoryNamespaceConfig → top_k, relevance_score
├── ChannelConfig (dict)    → enabled, type
├── InterfaceConfig         → welcome_message, author_name
└── ErrorMessagesConfig     → generic, empty_input
```

**Key validation rules:**
- `slug`: lowercase alphanumeric + hyphens, must start with letter/digit (`^[a-z0-9][a-z0-9-]*$`)
- `agent.name`: alphanumeric + underscore, max 48 chars (`^[a-zA-Z][a-zA-Z0-9_]{0,47}$`)
- `sub_agents`: minimum 1 entry required (`min_length=1`)
- `tools_source`: enum of `gateway_mcp | bedrock_kb | none`
- `memory.namespaces.top_k`: >= 1
- `memory.namespaces.relevance_score`: 0.0 to 1.0
- **Path traversal protection**: `model_validator` rejects prompt paths with `..` or absolute paths

### 2. Loader (`src/domain/loader.py`)

Thread-safe singleton with fail-fast semantics:

```
load_domain_config(config_path?)
    │
    ├── Return cached _config if exists (fast path)
    │
    └── Acquire _lock (double-check locking)
        ├── Resolve domain dir: DOMAIN_DIR env → default "domains/banqi-banking"
        ├── Read & parse YAML
        ├── Validate via DomainConfig(**raw) — Pydantic fail-fast
        ├── _validate_model_env_vars() — fail-fast on missing model IDs
        └── Cache in _config singleton
```

**Key functions:**
- `get_domain_dir()` → resolves `DOMAIN_DIR` env var (absolute or relative to PROJECT_ROOT)
- `load_domain_config(config_path?)` → singleton loader with thread-safe double-check locking
- `get_prompt(prompt_file)` → loads `.md` prompt file relative to domain dir
- `reset_config()` → clears cache (testing only)
- `_validate_model_env_vars(config)` → ensures all `model_id_env` vars are set in environment

**Fail-fast behavior:**
- Missing `domain.yaml` → `FileNotFoundError`
- Invalid YAML structure → Pydantic `ValidationError`
- Missing model env vars → `OSError` with list of missing vars
- Missing prompt file → `FileNotFoundError`

### 3. Domain YAML Structure

Reference implementation (`domains/banqi-banking/domain.yaml`):

```yaml
domain:
  name: "BanQi"
  slug: "banqi-banking"
  description: "Assistente bancário conversacional"
  language_default: "pt-BR"

agent:
  name: "banqi_multi_agent"
  memory_name: "BanQiMemory"
  session_prefix: "session"

supervisor:
  prompt_file: "prompts/supervisor.md"
  model_id_env: "SUPERVISOR_AGENT_MODEL_ID"

sub_agents:                              # N sub-agents, minimum 1
  services:
    name: "Services Agent"
    prompt_file: "prompts/services.md"
    tool_docstring: "Processa consultas bancárias"
    model_id_env: "SERVICES_AGENT_MODEL_ID"
    tools_source: "gateway_mcp"
  knowledge:
    name: "Knowledge Agent"
    prompt_file: "prompts/knowledge.md"
    tool_docstring: "Consultas gerais sobre produtos"
    model_id_env: "KNOWLEDGE_AGENT_MODEL_ID"
    tools_source: "bedrock_kb"

memory:
  namespaces:
    users/{user_id}/preferences:
      top_k: 3
      relevance_score: 0.7
    users/{user_id}/facts:
      top_k: 7
      relevance_score: 0.4

channels:
  whatsapp: { enabled: true, type: webhook }
  chainlit: { enabled: true, type: local }

interface:
  welcome_message: "🏦 Olá! Sou o assistente BanQi."
  author_name: "BanQi Assistant"

error_messages:
  generic: "Desculpe, ocorreu um erro."
  empty_input: "Envie sua pergunta."
```

### 4. Template System

`domains/_template/` provides a scaffold for new domains:
- Pre-filled `domain.yaml` with placeholder values and inline comments
- Stub prompt files (`supervisor.md`, `services.md`, `knowledge.md`)
- Empty `kb-docs/` directory with `.gitkeep`
- `README.md` with 5-step quick start guide

New domain creation: `cp -r domains/_template domains/new-slug` → edit YAML → deploy.

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Config format | YAML over JSON/TOML | Human-readable, supports multiline strings for prompts, familiar to DevOps |
| Validation | Pydantic v2 | Type-safe, auto-generates error messages, `model_validator` for cross-field rules |
| Loading pattern | Singleton with double-check locking | Config is immutable at runtime; avoids re-parsing on every request |
| Fail-fast | Crash on startup if invalid | Better than silent fallbacks — errors surface immediately in deploy |
| Path resolution | `DOMAIN_DIR` env var | Enables multi-domain deploys from same codebase without code changes |
| Security | Path traversal rejection | Prevents `../../etc/passwd` in prompt_file fields |
| Env var validation | Separate pass after Pydantic | Model IDs come from env, not YAML — validates runtime environment |

## Dependencies

- `pydantic >= 2.0` — schema validation
- `pyyaml` — YAML parsing
- Python `threading` — lock for singleton
- Python `pathlib` — path resolution and traversal protection

## Integration Points

- **Agent Factory** (`src/agents/factory.py`) — reads `DomainConfig` to create supervisor + sub-agents
- **Memory Setup** (`src/memory/setup.py`) — reads `memory.namespaces` for AgentCore Memory config
- **Channels** (`src/channels/`) — reads `channels` and `interface` for welcome messages
- **Gateway** (`src/gateway/token_manager.py`) — reads `agent.name` for AgentCore Gateway auth
- **Infrastructure** (`infrastructure/terraform/`) — `domain.yaml` values map to Terraform variables
