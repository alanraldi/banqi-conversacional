# Domain Config — Tasks

## Status: ✅ Complete (Fase 1)

All tasks in this module are implemented and tested. This task list serves as a reconstruction guide for developers.

---

## T-DC-001: Pydantic Schema Models
- [x] Create `src/domain/schema.py`
- [x] Implement `DomainInfo` model with slug regex validation
- [x] Implement `AgentInfo` model with name pattern (48 char max)
- [x] Implement `SupervisorConfig` model with prompt_file field
- [x] Implement `SubAgentConfig` model with tools_source enum
- [x] Implement `MemoryNamespaceConfig` with top_k/relevance_score bounds
- [x] Implement `MemoryConfig` with namespaces dict
- [x] Implement `ChannelConfig`, `InterfaceConfig`, `ErrorMessagesConfig`
- [x] Implement `DomainConfig` root model with `min_length=1` on sub_agents
- [x] Add `model_validator` for path traversal protection on prompt_file fields

**Files:** `src/domain/schema.py`
**Tests:** `tests/unit/test_schema.py` (6 tests)

## T-DC-002: Configuration Loader
- [x] Create `src/domain/loader.py`
- [x] Implement `get_domain_dir()` with DOMAIN_DIR env var resolution
- [x] Implement `load_domain_config()` with double-check locking singleton
- [x] Implement `_validate_model_env_vars()` for fail-fast on missing model IDs
- [x] Implement `get_prompt()` for loading .md prompt files relative to domain dir
- [x] Implement `reset_config()` for test isolation

**Files:** `src/domain/loader.py`
**Tests:** Covered by integration tests and `test_schema.py` indirectly

## T-DC-003: BanQi Banking Domain Configuration
- [x] Create `domains/banqi-banking/domain.yaml` with full configuration
- [x] Create supervisor prompt (`domains/banqi-banking/prompts/supervisor.md`)
- [x] Create services agent prompt (`domains/banqi-banking/prompts/services.md`)
- [x] Create knowledge agent prompt (`domains/banqi-banking/prompts/knowledge.md`)
- [x] Add 11 knowledge base documents in `domains/banqi-banking/kb-docs/`

**Files:** `domains/banqi-banking/`

## T-DC-004: Domain Template
- [x] Create `domains/_template/domain.yaml` with placeholder values and inline comments
- [x] Create stub prompt files for supervisor, services, knowledge
- [x] Create `kb-docs/.gitkeep`
- [x] Create `domains/_template/README.md` with 5-step quick start

**Files:** `domains/_template/`

## T-DC-005: Unit Tests
- [x] Test valid slug acceptance
- [x] Test invalid slug rejection (uppercase, starts with dash)
- [x] Test valid minimal config loads
- [x] Test empty sub_agents rejection
- [x] Test path traversal rejection (`../`)
- [x] Test absolute path rejection (`/etc/passwd`)
- [x] Test default values population

**Files:** `tests/unit/test_schema.py`

---

## Reconstruction Guide

To rebuild this module from scratch:

1. **Start with schema.py** — Define all 11 Pydantic models following the hierarchy in `design.md`. The `DomainConfig` root model ties everything together.

2. **Add path traversal validator** — Use `@model_validator(mode="after")` on `DomainConfig` to check all `prompt_file` fields.

3. **Build loader.py** — Implement singleton with `threading.Lock()` and double-check pattern. Resolution order: `DOMAIN_DIR` env → default `domains/banqi-banking`.

4. **Add env var validation** — After Pydantic validates structure, check that all `model_id_env` values exist in `os.environ`.

5. **Create banqi-banking domain** — Copy `_template`, fill in BanQi-specific values, write prompts.

6. **Write tests** — Focus on validation boundaries: invalid slugs, empty sub_agents, path traversal, defaults.

**Key principle:** The schema is the contract. If `domain.yaml` passes Pydantic validation, the rest of the system can trust it without additional checks.
