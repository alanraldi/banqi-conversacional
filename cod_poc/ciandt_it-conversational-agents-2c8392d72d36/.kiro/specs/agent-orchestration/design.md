# Agent Orchestration — Design

## Overview

The Agent Orchestration module implements the **Agents-as-Tools** pattern: a Supervisor agent coordinates N sub-agents, each registered as a `@tool`. The Supervisor decides which sub-agent to invoke based on user intent. Sub-agents are stateless — memory and context are centralized in the Supervisor.

## Architecture

```
User Request
    │
    ▼
create_supervisor(user_id, session_id)
    │
    ├── Cached: BedrockModel, system_prompt, delegate_tools
    └── Fresh:  conversation_manager, session_manager (memory)
    │
    ▼
┌─────────────────────────────────────────────┐
│  Supervisor Agent (Claude Sonnet)            │
│  ├── system_prompt (from prompts/supervisor.md) │
│  ├── conversation_manager (sliding window)  │
│  ├── session_manager (AgentCore Memory)     │
│  └── tools:                                 │
│       ├── services_assistant (→ sub-agent)   │
│       ├── knowledge_assistant (→ sub-agent)  │
│       └── LTM tools (memory read/write)     │
└─────────────────────────────────────────────┘
         │                    │
    @tool call           @tool call
         │                    │
         ▼                    ▼
┌──────────────┐    ┌──────────────┐
│ Services Agent│    │Knowledge Agent│
│ (Haiku)      │    │ (Haiku)      │
│ tools: MCP   │    │ tools: KB    │
└──────────────┘    └──────────────┘
```

## Component Design

### 1. Agent Factory (`src/agents/factory.py`)

Central factory with **cached heavy setup** and **fresh per-request setup**:

```
Cached (lru_cache):                    Fresh (per request):
├── BedrockModel (maxsize=4)           ├── SlidingWindowConversationManager
├── System prompts (maxsize=8)         ├── AgentCoreMemorySessionManager
└── Delegate tools (maxsize=1)         └── SessionContext (thread-local)
```

**Key function: `create_supervisor()`**
1. Load domain config (singleton)
2. Set thread-local session context (user_id, session_id)
3. Get cached model, prompt, delegate tools
4. Create fresh conversation manager (sliding window)
5. Create fresh session manager (AgentCore Memory) if user_id present
6. Construct Supervisor Agent
7. Attach LTM tools post-construction

### 2. Delegate Tool Creation (`_make_delegate_tool()`)

Each sub-agent from `domain.yaml` becomes a `@tool` function:

```python
@tool(name="{key}_assistant")
def delegate(query: str) -> str:
    ctx = session_context.get()          # Thread-local context
    sub = _create_sub_agent(...)         # Fresh agent, cached model/prompt
    result = sub(query)                  # Invoke sub-agent
    return str(result)
delegate.__doc__ = agent_cfg.tool_docstring  # LLM sees this for routing
```

The `tool_docstring` from `domain.yaml` is critical — it's what the Supervisor LLM reads to decide which tool to call.

### 3. Tool Provider Registry

Maps `tools_source` from `domain.yaml` to tool loader functions:

| `tools_source` | Provider | What it loads |
|---|---|---|
| `gateway_mcp` | `_get_gateway_tools()` | MCP tools from AgentCore Gateway (Cognito OAuth) |
| `bedrock_kb` | `_get_kb_tools()` | `retrieve` tool from `strands_tools` |
| `none` | `lambda: []` | No tools |

All providers use **degraded mode** — if tools are unavailable (missing env var, connection error), the agent runs without them instead of crashing.

### 4. Session Context (`src/agents/context.py`)

Thread-safe context passing between Supervisor and sub-agents:

```
SessionContext (threading.local)
└── _Ctx (frozen dataclass)
    ├── user_id: str | None
    └── session_id: str | None
```

- `set()` — called at request start in `create_supervisor()`
- `get()` — called inside `@tool` delegate functions to pass context to sub-agents
- Thread isolation — each request thread has independent state
- Immutable snapshots — `_Ctx` is `frozen=True`

### 5. Agent Helpers (`src/utils/agent_helpers.py`)

Extracts text from Strands Agent result format:

```
result.message = {"content": [{"text": "response text"}]}
```

### 6. Guardrails Integration

Applied at the model level via `_guardrail_kwargs()`:

| Setting | Value | Rationale |
|---|---|---|
| `guardrail_redact_input` | `False` | Preserve conversation context (PII masked via regex in logs) |
| `guardrail_redact_output` | `False` | Keep response readable |
| `guardrail_latest_message` | `True` | Evaluate only last message, avoid multi-turn trap |
| `guardrail_trace` | `enabled` | Debugging visibility |

### 7. Memory Integration

**STM (Short-Term Memory)** — via `AgentCoreMemorySessionManager`:
- Created fresh per request with user_id + session_id
- Namespace templates from `domain.yaml` resolved with actual user/session IDs
- Passed in Agent constructor for hooks to register

**LTM (Long-Term Memory)** — via `AgentCoreMemoryToolProvider`:
- Attached post-construction via `tool_registry.register_tool()`
- Provides read/write tools for persistent user facts

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Agents-as-Tools | Sub-agents as `@tool` on Supervisor | Strands native pattern; Supervisor controls routing via LLM |
| New agent per request | Fresh Agent instance | Strands `_invocation_lock` prevents reuse (ADR-001) |
| Cached heavy setup | `lru_cache` on models, prompts, tools | Avoid re-creating BedrockModel and re-reading prompts per request |
| Thread-local context | `threading.local()` + frozen dataclass | Pass user_id/session_id to `@tool` functions without global mutable state (Fix C1) |
| Degraded mode | Empty tools on failure | Agent works without Gateway/KB — better than crash |
| Sync everywhere | No async | Strands SDK is sync (ADR-005) |
| Model-per-agent | Sonnet (Supervisor) + Haiku (sub-agents) | Cost optimization — routing needs intelligence, execution needs speed (ADR-011) |
| Prompt caching | `cachePoint` in system_prompt | Bedrock prompt caching reduces latency on repeated prompts |

## Dependencies

- `strands-agents` — Agent, tool decorator, BedrockModel, SlidingWindowConversationManager
- `strands-agents-tools` — `retrieve` (KB tool), `AgentCoreMemoryToolProvider` (LTM)
- `bedrock-agentcore` — `AgentCoreMemorySessionManager`, `AgentCoreMemoryConfig`
- `src/domain/` — DomainConfig, prompt loading
- `src/config/settings.py` — env var settings (guardrail IDs, memory IDs, etc.)
- `src/gateway/token_manager.py` — Cognito OAuth token for Gateway MCP

## Integration Points

- **Main entrypoint** (`src/main.py`) — calls `create_supervisor()` per request
- **Domain Config** — drives all agent creation (names, prompts, tools_source, models)
- **WhatsApp Lambda** — invokes AgentCore Runtime which calls `main.py`
- **Chainlit** — calls `create_supervisor()` directly
