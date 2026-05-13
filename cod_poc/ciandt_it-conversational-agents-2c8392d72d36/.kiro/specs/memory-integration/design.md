# Memory Integration — Design

## Overview

Integrates AgentCore Memory (STM + LTM) with the agent framework. Memory namespaces are configured in `domain.yaml` and resolved dynamically per user/session.

## Architecture

```
Supervisor Agent
├── STM: AgentCoreMemorySessionManager (constructor hook)
│   └── Namespaces from domain.yaml:
│       ├── /users/{user_id}/preferences (top_k=3, score=0.7)
│       ├── /users/{user_id}/facts (top_k=7, score=0.4)
│       └── /summaries/{user_id}/{session_id} (top_k=3, score=0.4)
└── LTM: AgentCoreMemoryToolProvider (post-construction)
    └── Tools: memory_read, memory_write → /users/{user_id}
```

## Components

### Memory Setup (`src/memory/setup.py`)
- `attach_memory()` — attaches STM session manager + LTM tools to agent
- `_build_retrieval_config()` — resolves namespace templates from domain.yaml
- Degraded mode if `AGENTCORE_MEMORY_ID` not set
- PII masking on user_id in logs (`_mask_user_id`)

### Settings (`src/config/settings.py`)
- `AGENTCORE_MEMORY_ID` — Memory store ID (from Terraform output)
- `AGENTCORE_MEMORY_ENABLED` — toggle
- `AWS_REGION` — for Memory API calls

### WhatsApp Memory Persistence (`agentcore_client.py`)
- `save_conversation_to_memory()` — explicit `create_event` after each turn
- Feeds LTM strategies: SEMANTIC (facts), USER_PREFERENCE, SUMMARIZATION

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| STM in constructor | `session_manager` param | Strands hooks must register at construction time |
| LTM post-construction | `tool_registry.register_tool()` | LTM tools can be added after Agent creation |
| Namespace templates | `{user_id}`, `{session_id}` in YAML | Domain-specific namespace structure without code changes |
| Explicit create_event | WhatsApp Lambda persists turns | Without this, LTM strategies have no data to process |
| Degraded mode | Log warning, continue | Agent works without memory — useful for dev/testing |
