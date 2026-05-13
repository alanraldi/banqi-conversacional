# Channel WhatsApp — Tasks

## Status: ✅ Complete (Fase 3)

All tasks implemented and tested.

---

## T-WA-001: Webhook Models
- [x] Create `src/channels/whatsapp/models.py`
- [x] Implement Pydantic models for Meta's nested webhook structure
- [x] `WebhookMessage` with `from` alias, text body max 4096 chars
- [x] `WebhookPayload.extract_messages()` helper

**Files:** `src/channels/whatsapp/models.py`

## T-WA-002: Signature Validation
- [x] Create `src/channels/whatsapp/signature.py`
- [x] HMAC-SHA256 validation with `hmac.compare_digest()`
- [x] Reject: missing header, empty secret, invalid format, wrong sig
- [x] Unit tests: 6 test cases covering all rejection paths

**Files:** `src/channels/whatsapp/signature.py`
**Tests:** `tests/unit/test_signature.py` (6 tests)

## T-WA-003: WhatsApp Client
- [x] Create `src/channels/whatsapp/client.py`
- [x] `send_message(to, text)` via WhatsApp Business API
- [x] `send_typing_indicator(to, message_id)` — read + typing
- [x] stdlib `urllib.request` only (zero Lambda dependencies)

**Files:** `src/channels/whatsapp/client.py`

## T-WA-004: Configuration
- [x] Create `src/channels/whatsapp/config.py`
- [x] Dual secret loading: Secrets Manager (prod) / env vars (dev)
- [x] `lru_cache(maxsize=1)` on secret loading
- [x] Fail-fast on missing required values

**Files:** `src/channels/whatsapp/config.py`

## T-WA-005: AgentCore Client
- [x] Create `src/channels/whatsapp/agentcore_client.py`
- [x] `invoke_agent_runtime()` with latency logging
- [x] `save_conversation_to_memory()` via `create_event` (USER+ASSISTANT)
- [x] Lazy singleton boto3 client for warm starts

**Files:** `src/channels/whatsapp/agentcore_client.py`

## T-WA-006: Webhook Processor
- [x] Create `src/channels/whatsapp/webhook_processor.py`
- [x] `handle_verification()` — GET webhook challenge
- [x] `handle_message()` — full POST flow (sig → parse → dedup → typing → invoke → memory → respond)
- [x] DynamoDB dedup with conditional put + 120s TTL
- [x] Deterministic session ID (≥33 chars)

**Files:** `src/channels/whatsapp/webhook_processor.py`

## T-WA-007: Lambda Handler
- [x] Create `src/channels/whatsapp/lambda_handler.py`
- [x] Support API Gateway v1 and v2 event formats
- [x] Init config/client outside handler (cold start optimization)
- [x] Route GET → verification, POST → message processing

**Files:** `src/channels/whatsapp/lambda_handler.py`

## T-WA-008: E2E and Container Tests
- [x] Create `tests/e2e/test_staging_whatsapp.py` — staging webhook test
- [x] Create `tests/container/test_sam_webhook.sh` — SAM local test

**Files:** `tests/e2e/test_staging_whatsapp.py`, `tests/container/test_sam_webhook.sh`

---

## Reconstruction Guide

1. **Start with models.py** — Pydantic models matching Meta's nested webhook JSON. The `extract_messages()` helper flattens the structure.

2. **Build signature.py** — HMAC-SHA256 with `hmac.compare_digest()`. Test all rejection paths (Fix C7).

3. **Build client.py** — stdlib `urllib.request` for WhatsApp API. No external HTTP libs.

4. **Build config.py** — Dual secret loading (Secrets Manager or env vars). Fail-fast.

5. **Build agentcore_client.py** — `invoke_agent_runtime()` + `save_conversation_to_memory()`. Lazy singleton boto3 client.

6. **Build webhook_processor.py** — Orchestrates the 7-step flow. DynamoDB dedup with conditional put.

7. **Build lambda_handler.py** — Thin entrypoint. Init outside handler for warm starts.

**Key principle:** The Lambda is decoupled from the agent framework — it only knows how to call AgentCore Runtime via boto3. No `strands-agents` dependency.
