# Channel WhatsApp — Requirements

## Functional Requirements

### FR-WA-001: Webhook Verification
WHEN Meta sends a GET request with `hub.mode=subscribe` and a valid `hub.verify_token`
THE SYSTEM SHALL return HTTP 200 with the `hub.challenge` value
SO THAT the webhook URL is verified with Meta.

### FR-WA-002: HMAC Signature Validation
WHEN a POST webhook arrives
THE SYSTEM SHALL validate the `X-Hub-Signature-256` header using HMAC-SHA256 with the app secret
AND SHALL reject requests with missing, malformed, or invalid signatures (HTTP 403)
AND SHALL use timing-safe comparison (`hmac.compare_digest`).

### FR-WA-003: Webhook Payload Parsing
WHEN a valid POST webhook arrives
THE SYSTEM SHALL parse Meta's nested JSON structure into typed Pydantic models
AND SHALL extract text messages from `entry[].changes[].value.messages[]`
AND SHALL reject invalid payloads with HTTP 400.

### FR-WA-004: Message Deduplication
WHEN a text message is received
THE SYSTEM SHALL check DynamoDB for the `message_id` using conditional put
AND SHALL skip processing if the message was already seen (within 120s TTL)
SO THAT duplicate webhook deliveries from Meta are handled idempotently.

### FR-WA-005: Agent Invocation
WHEN a new text message passes dedup
THE SYSTEM SHALL invoke AgentCore Runtime with the message text, phone number (as user_id), and a deterministic session ID
AND SHALL return the domain's `error_message.generic` if invocation fails.

### FR-WA-006: Memory Persistence
WHEN the agent responds successfully
THE SYSTEM SHALL persist the USER+ASSISTANT conversation turn to AgentCore Memory via `create_event`
SO THAT LTM strategies (semantic, user_preference, summarization) can process the conversation.

### FR-WA-007: Response Delivery
WHEN the agent produces a response
THE SYSTEM SHALL send it as a text message via WhatsApp Business API to the user's phone number.

### FR-WA-008: Typing Indicator
WHEN a message is being processed
THE SYSTEM SHALL send a "read" status and typing indicator to the user
SO THAT the user sees the agent is working.

### FR-WA-009: Dual Secret Loading
WHEN the Lambda initializes
THE SYSTEM SHALL load WhatsApp secrets from:
1. Secrets Manager (prod) — via `WHATSAPP_SECRET_ARN` env var
2. Individual env vars (dev) — `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`
AND SHALL fail-fast if required secrets are missing.

### FR-WA-010: Session ID Generation
WHEN building a session ID for a phone number
THE SYSTEM SHALL generate a deterministic ID: `{domain_slug}-wa-session-{clean_phone}`
AND SHALL ensure minimum 33 characters (AgentCore requirement) by padding.

### FR-WA-011: API Gateway Format Support
WHEN receiving events from API Gateway
THE SYSTEM SHALL support both v1 format (`httpMethod`) and v2 format (`requestContext.http.method`).

## Non-Functional Requirements

### NFR-WA-001: Cold Start Optimization
THE SYSTEM SHALL initialize config and HTTP client outside the handler function
SO THAT they are reused across Lambda warm starts.

### NFR-WA-002: Zero External HTTP Dependencies
THE SYSTEM SHALL use `urllib.request` (stdlib) for WhatsApp API calls
SO THAT the Lambda package has no extra HTTP library dependencies.

### NFR-WA-003: Graceful Degradation
WHEN DynamoDB dedup table is not configured
THE SYSTEM SHALL skip deduplication and process all messages.
WHEN memory persistence fails
THE SYSTEM SHALL log a warning and continue (non-blocking).

### NFR-WA-004: Security
THE SYSTEM SHALL never log WhatsApp access tokens or app secrets
AND SHALL mask PII (phone numbers) in logs via PIIMaskingFilter.

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-WA-001 | Valid HMAC signature accepted | `test_signature.py::test_valid_signature` |
| AC-WA-002 | Missing signature header rejected | `test_signature.py::test_missing_header` |
| AC-WA-003 | Empty secret rejected | `test_signature.py::test_empty_secret` |
| AC-WA-004 | Invalid format (non-sha256) rejected | `test_signature.py::test_invalid_format` |
| AC-WA-005 | Wrong signature rejected | `test_signature.py::test_wrong_signature` |
| AC-WA-006 | Tampered payload rejected | `test_signature.py::test_tampered_payload` |
| AC-WA-007 | Webhook models parse Meta's nested structure | `tests/unit/test_models.py` |
| AC-WA-008 | Webhook verification returns challenge | Integration test |
| AC-WA-009 | Duplicate messages skipped | Integration test |
| AC-WA-010 | Agent invoked with correct payload | `tests/e2e/test_staging_whatsapp.py` |
| AC-WA-011 | Response delivered via WhatsApp API | `tests/e2e/test_staging_whatsapp.py` |
| AC-WA-012 | SAM local webhook works | `tests/container/test_sam_webhook.sh` |
