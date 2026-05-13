# Memory Integration — Tasks

## Status: ✅ Complete (Fase 2)

---

## T-MI-001: Memory Setup Module
- [x] Create `src/memory/setup.py`
- [x] `attach_memory()` — STM session manager + LTM tools
- [x] `_build_retrieval_config()` — namespace template resolution
- [x] `_mask_user_id()` — PII masking for logs
- [x] Degraded mode when AGENTCORE_MEMORY_ID not set

**Files:** `src/memory/setup.py`

## T-MI-002: Factory Integration
- [x] `_create_session_manager()` in factory.py — STM via constructor
- [x] `_attach_ltm_tools()` in factory.py — LTM post-construction
- [x] Namespace template resolution with actual user_id/session_id

**Files:** `src/agents/factory.py`

## T-MI-003: WhatsApp Memory Persistence
- [x] `save_conversation_to_memory()` in agentcore_client.py
- [x] `create_event` with USER+ASSISTANT payload
- [x] Non-blocking (log warning on failure)

**Files:** `src/channels/whatsapp/agentcore_client.py`

---

## Reconstruction Guide

1. **Build setup.py** — `attach_memory()` that reads namespaces from domain.yaml, creates STM session manager, attaches LTM tools.
2. **Integrate in factory.py** — STM in Agent constructor, LTM post-construction.
3. **Add create_event in WhatsApp Lambda** — explicit persistence feeds LTM strategies.

**Key principle:** Memory is optional — the agent must work without it (degraded mode). This enables local dev without AWS credentials.
