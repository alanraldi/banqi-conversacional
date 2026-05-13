# Channel WhatsApp — Design

## Overview

The WhatsApp channel connects the conversational agent to WhatsApp Business API via a Lambda function behind API Gateway + WAF. It handles webhook verification, HMAC signature validation, message deduplication, agent invocation via AgentCore Runtime, memory persistence, and response delivery.

## Architecture

```
WhatsApp User
    │
    ▼ (Meta webhook)
┌──────────────────────────────────────────────┐
│  API Gateway (REST) + WAF (1000 req/5min)    │
└──────────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────────┐
│  Lambda (lambda_handler.py)                  │
│  ├── GET  → handle_verification()            │
│  └── POST → handle_message()                 │
│       ├── 1. Signature validation (HMAC)     │
│       ├── 2. Parse payload (Pydantic)        │
│       ├── 3. Dedup (DynamoDB conditional put) │
│       ├── 4. Typing indicator                │
│       ├── 5. Invoke AgentCore Runtime        │
│       ├── 6. Persist memory (create_event)   │
│       └── 7. Send response (WhatsApp API)    │
└──────────────────────────────────────────────┘
    │                    │                  │
    ▼                    ▼                  ▼
DynamoDB (dedup)   AgentCore Runtime   WhatsApp API
                   (invoke_agent)      (send_message)
```

## Component Design

### 1. Lambda Handler (`lambda_handler.py`)

Thin entrypoint supporting both API Gateway v1 (`httpMethod`) and v2 (`requestContext.http.method`).

**Cold start optimization**: `WhatsAppConfig` and `WhatsAppClient` initialized outside handler function — reused across warm starts.

### 2. Webhook Processor (`webhook_processor.py`)

Orchestrates the full message flow:

| Step | Function | Failure Mode |
|---|---|---|
| Signature | `validate_webhook_signature()` | 403 Forbidden |
| Parse | `WebhookPayload.model_validate_json()` | 400 Invalid payload |
| Dedup | `_is_duplicate()` via DynamoDB conditional put | Skip message (log) |
| Typing | `client.send_typing_indicator()` | Ignore (cosmetic) |
| Invoke | `invoke_agent_runtime()` | Return error_message |
| Memory | `save_conversation_to_memory()` | Log warning (non-blocking) |
| Respond | `client.send_message()` | Log error |

**Session ID**: deterministic from phone number — `{domain_slug}-wa-session-{phone}`, padded to ≥33 chars (AgentCore minimum).

### 3. Signature Validation (`signature.py`)

HMAC-SHA256 validation of `X-Hub-Signature-256` header (Fix C7):
- Rejects missing header, empty secret, invalid format, wrong signature
- Uses `hmac.compare_digest()` for timing-safe comparison
- Never returns True unconditionally

### 4. WhatsApp Client (`client.py`)

HTTP client using `urllib.request` (stdlib only — zero Lambda dependencies):
- `send_message(to, text)` — text message via WhatsApp Business API
- `send_typing_indicator(to, message_id)` — mark as read + typing
- Base URL: `https://graph.facebook.com/{api_version}/{phone_number_id}`

### 5. Configuration (`config.py`)

Dual secret loading (ADR-008):
- **Prod**: JSON secret from Secrets Manager via `WHATSAPP_SECRET_ARN`
- **Dev**: individual env vars (`WHATSAPP_ACCESS_TOKEN`, etc.)
- Fail-fast on missing required values
- `lru_cache(maxsize=1)` on secret loading

### 6. AgentCore Client (`agentcore_client.py`)

- `invoke_agent_runtime()` — calls AgentCore Runtime with prompt/user_id/session_id, logs latency
- `save_conversation_to_memory()` — persists USER+ASSISTANT turn via `create_event` (feeds LTM strategies: SEMANTIC, USER_PREFERENCE, SUMMARIZATION)
- Lazy singleton boto3 client reused across warm starts

### 7. Webhook Models (`models.py`)

Pydantic models for Meta's nested webhook structure:
- `WebhookPayload` → `WebhookEntry` → `WebhookChange` → `WebhookValue`
- `WebhookMessage` (text body max 4096 chars, `from` aliased to `from_`)
- `WebhookStatus` (delivery status updates)
- `extract_messages()` helper to flatten nested structure

### 8. Message Deduplication

DynamoDB conditional put with TTL:
- Table: `{domain_slug}-whatsapp-dedup`
- Key: `message_id` (WhatsApp `wamid.*`)
- TTL: 120 seconds
- Conditional: `attribute_not_exists(message_id)` — atomic check-and-set
- Graceful: if table not configured, dedup is skipped

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Separate Lambda | Not in AgentCore container | Independent scaling, lower latency for webhook (ADR-006) |
| stdlib HTTP | `urllib.request` over `httpx`/`requests` | Zero extra dependencies in Lambda package |
| Secrets dual | Secrets Manager (prod) / env vars (dev) | ADR-008 — no fallback, fail-fast |
| Dedup via DynamoDB | Conditional put + TTL | Atomic, serverless, auto-cleanup |
| Memory create_event | Explicit after response | Feeds LTM strategies (semantic, preferences, summaries) |
| Pydantic models | For webhook payload parsing | Type-safe, handles Meta's deeply nested structure |

## Dependencies

- `boto3` — DynamoDB (dedup), Secrets Manager, AgentCore Runtime
- `pydantic` — webhook payload validation
- `urllib.request` (stdlib) — WhatsApp Business API calls
- No `strands-agents` dependency — Lambda is decoupled from agent framework

## Integration Points

- **API Gateway** — routes webhook requests to Lambda
- **WAF** — rate limiting (1000 req/5min)
- **AgentCore Runtime** — invokes the agent container
- **AgentCore Memory** — persists conversation turns via `create_event`
- **DynamoDB** — message deduplication
- **Secrets Manager** — WhatsApp credentials (prod)
- **Terraform module** `whatsapp/` — provisions all resources
