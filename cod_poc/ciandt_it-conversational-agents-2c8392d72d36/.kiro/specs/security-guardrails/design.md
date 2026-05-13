# Security & Guardrails — Design

## Overview

Multi-layer security: Bedrock Guardrails (conversation), PII regex masking (logs), input validation (OWASP LLM), secrets management (dual dev/prod), path traversal protection (domain config), and structured logging with PII filtering.

## Security Layers

```
User Input
    │
    ▼
1. Input Validation (validation.py)
   ├── validate_non_empty() — reject empty
   ├── validate_input_length() — max 4096 chars (OWASP LLM04)
   └── _sanitize_identifier() — alphanumeric only for IDs
    │
    ▼
2. Bedrock Guardrails (model level)
   ├── PROMPT_ATTACK detection (HIGH sensitivity)
   └── Topic policy (off-topic DENY)
    │
    ▼
3. Agent Processing
    │
    ▼
4. PII Masking (logs only)
   ├── CPF: ***.***.***-**
   ├── Phone: ***-****-****
   └── Email: ***@***.***
    │
    ▼
5. Structured JSON Logging (CloudWatch)
```

## Components

### Bedrock Guardrails (`factory.py → _guardrail_kwargs()`)
- Applied at BedrockModel level
- `guardrail_redact_input=False` — preserve conversation context
- `guardrail_latest_message=True` — evaluate only last message
- Configured via `BEDROCK_GUARDRAIL_ID` + `BEDROCK_GUARDRAIL_VERSION`

### PII Masking (`src/utils/pii.py`)
- `PIIMaskingFilter` — logging.Filter applied to all handlers
- Regex patterns: CPF (11 digits), phone (10-13 digits), email
- Design: prefer false positives over false negatives (LGPD compliance)
- Converts all log args to string before masking (catches numeric PII)

### Input Validation (`src/utils/validation.py`)
- `validate_non_empty()` — reject empty/whitespace
- `validate_input_length()` — max 4096 chars (OWASP LLM04 — prompt injection via oversized input)
- `CPFInput` / `PhoneInput` — Pydantic models with check digit validation
- `format_cpf_masked()` — safe display format for chat responses
- `_sanitize_identifier()` in main.py — alphanumeric only for user IDs (prevents namespace injection)

### Secrets Management (`src/utils/secrets.py`)
- `get_secret()` — env var first (dev), Secrets Manager fallback (prod)
- `lru_cache(maxsize=32)` — cached per secret name
- Fail-fast: `RuntimeError` if secret not found (no fallback values, ADR-008)

### Structured Logging (`src/utils/logging.py`)
- `JSONFormatter` — single-line JSON for CloudWatch
- Fields: timestamp, level, logger, message, agent_name, session_id, duration_ms
- PII masking applied after formatting via `setup_pii_logging()`
- External lib noise reduced (httpx, boto3 → WARNING)

### Path Traversal Protection (`schema.py`)
- `model_validator` on DomainConfig rejects `..` and absolute paths in `prompt_file`

### LGPD Compliance
- `scripts/delete_user_data.py` — right to erasure (Art. 18)
- PII never in logs (regex masking)
- Memory data scoped to user namespace

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Dual PII strategy | Guardrails (conversation) + regex (logs) | Guardrails handle LLM output; regex handles structured logs |
| False positive preference | Mask 11-digit numbers even if not CPF | LGPD violation > debugging inconvenience |
| Secrets dual | env var (dev) / Secrets Manager (prod) | ADR-008 — no fallback, fail-fast |
| Input length limit | 4096 chars | OWASP LLM04 — prevent prompt injection via oversized input |
| Guardrail latest_message | True | Avoid multi-turn conversation trap |
