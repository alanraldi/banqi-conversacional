# Agent Orchestration — Tasks

## Status: ✅ Complete (Fase 2)

All tasks implemented and tested. This task list serves as a reconstruction guide.

---

## T-AO-001: Session Context
- [x] Create `src/agents/context.py`
- [x] Implement `_Ctx` frozen dataclass (user_id, session_id)
- [x] Implement `SessionContext` with `threading.local()` storage
- [x] Methods: `set()`, `get()`, `clear()`
- [x] Unit tests: set/get, defaults, clear, thread isolation, immutability

**Files:** `src/agents/context.py`
**Tests:** `tests/unit/test_context.py` (5 tests)

## T-AO-002: Agent Factory — Core
- [x] Create `src/agents/factory.py`
- [x] Implement `create_supervisor()` with cached heavy setup + fresh per-request setup
- [x] Implement `_get_cached_model()` with `lru_cache(maxsize=4)`
- [x] Implement `_get_cached_prompt()` with `lru_cache(maxsize=8)` and `cachePoint`
- [x] Implement `_get_cached_delegate_tools()` with `lru_cache(maxsize=1)`
- [x] Implement `SlidingWindowConversationManager` creation per request

**Files:** `src/agents/factory.py`

## T-AO-003: Agents-as-Tools Pattern
- [x] Implement `_make_delegate_tool()` — creates `@tool(name="{key}_assistant")`
- [x] Set `__doc__` from `tool_docstring` for LLM routing
- [x] Access `session_context.get()` inside delegate for user context
- [x] Create fresh sub-agent per invocation via `_create_sub_agent()`

**Files:** `src/agents/factory.py`

## T-AO-004: Tool Provider Registry
- [x] Implement `_TOOL_PROVIDERS` dict mapping tools_source → loader function
- [x] Implement `_get_gateway_tools()` — MCP client with Cognito OAuth token
- [x] Implement `_get_kb_tools()` — Bedrock KB `retrieve` tool
- [x] Implement degraded mode: log warning + empty list on failure

**Files:** `src/agents/factory.py`

## T-AO-005: Memory Integration
- [x] Implement `_create_session_manager()` — AgentCoreMemorySessionManager
- [x] Resolve namespace templates (`{user_id}`, `{session_id}`) from domain.yaml
- [x] Implement `_attach_ltm_tools()` — AgentCoreMemoryToolProvider post-construction
- [x] Degraded mode if AGENTCORE_MEMORY_ID not set

**Files:** `src/agents/factory.py`

## T-AO-006: Guardrails Integration
- [x] Implement `_guardrail_kwargs()` — returns Bedrock Guardrails config
- [x] Settings: redact_input=False, redact_output=False, latest_message=True
- [x] Skip if BEDROCK_GUARDRAIL_ID not configured

**Files:** `src/agents/factory.py`

## T-AO-007: Agent Helpers
- [x] Create `src/utils/agent_helpers.py`
- [x] Implement `extract_text()` — handles `result.message.content[0].text` format
- [x] Fallback to `str(result)` for unexpected formats

**Files:** `src/utils/agent_helpers.py`
**Tests:** `tests/unit/test_agent_helpers.py`

## T-AO-008: Main Entrypoint
- [x] Create `src/main.py`
- [x] Implement `@app.entrypoint` with payload extraction (prompt, user_id, session_id)
- [x] Implement `@app.ping` health check
- [x] Implement `_extract_prompt()` with validation
- [x] Implement `_extract_user_id()` with sanitization (alphanumeric only, max 64 chars)
- [x] Fail-fast on startup if domain config invalid

**Files:** `src/main.py`

---

## Reconstruction Guide

To rebuild this module from scratch:

1. **Start with context.py** — Thread-local `SessionContext` with frozen dataclass. This solves the concurrent request problem (Fix C1).

2. **Build factory.py core** — `create_supervisor()` that loads domain config, creates cached model/prompt/tools, and fresh conversation manager per request.

3. **Implement agents-as-tools** — `_make_delegate_tool()` creates `@tool` functions from `domain.yaml` sub-agents. The `tool_docstring` is what the LLM reads for routing.

4. **Add tool providers** — Registry pattern mapping `tools_source` to loader functions. Always use degraded mode (empty list) on failure.

5. **Add memory** — STM via `AgentCoreMemorySessionManager` in constructor, LTM via `AgentCoreMemoryToolProvider` post-construction.

6. **Add guardrails** — Model-level kwargs from settings. Skip if not configured.

7. **Build main.py** — Thin entrypoint that extracts payload fields, calls `create_supervisor()`, and returns `{"result": text}`.

**Key principle:** The factory is the bridge between domain config (YAML) and Strands SDK (Python). Everything is driven by `domain.yaml` — adding a new sub-agent is a YAML change, not a code change.
