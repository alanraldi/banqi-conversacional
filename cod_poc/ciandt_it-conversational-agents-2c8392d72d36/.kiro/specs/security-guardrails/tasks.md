# Security & Guardrails — Tasks

## Status: ✅ Complete (Fase 5)

---

## T-SG-001: PII Masking
- [x] Create `src/utils/pii.py`
- [x] Regex patterns: CPF, phone (formatted + unformatted), email
- [x] `PIIMaskingFilter` logging.Filter — converts args to string before masking
- [x] `setup_pii_logging()` — applies filter to all root handlers

**Files:** `src/utils/pii.py`

## T-SG-002: Input Validation
- [x] Create `src/utils/validation.py`
- [x] `validate_non_empty()`, `validate_input_length()` (4096 max)
- [x] `CPFInput` Pydantic model with check digit validation
- [x] `PhoneInput` Pydantic model (10-15 digits)
- [x] `format_cpf_masked()` for safe display

**Files:** `src/utils/validation.py`

## T-SG-003: Secrets Management
- [x] Create `src/utils/secrets.py`
- [x] `get_secret()` — env var → Secrets Manager, fail-fast
- [x] `lru_cache(maxsize=32)` per secret name

**Files:** `src/utils/secrets.py`

## T-SG-004: Structured Logging
- [x] Create `src/utils/logging.py`
- [x] `JSONFormatter` — single-line JSON for CloudWatch
- [x] `setup_logging()` — configure handlers + PII masking
- [x] Reduce external lib noise

**Files:** `src/utils/logging.py`

## T-SG-005: Guardrails Integration
- [x] `_guardrail_kwargs()` in factory.py
- [x] Terraform module `guardrails/` — provisions Bedrock Guardrail

**Files:** `src/agents/factory.py`, `infrastructure/terraform/modules/guardrails/`

## T-SG-006: LGPD Script
- [x] Create `scripts/delete_user_data.py` — right to erasure

**Files:** `scripts/delete_user_data.py`

---

## Reconstruction Guide

1. **pii.py** — Regex patterns + logging.Filter. Apply to all handlers via `setup_pii_logging()`.
2. **validation.py** — Input validators (empty, length, CPF, phone). Used in main.py.
3. **secrets.py** — Dual strategy with lru_cache. No fallback values.
4. **logging.py** — JSONFormatter + PII filter setup. Call `setup_logging()` at startup.
5. **Guardrails** — Model-level kwargs in factory.py + Terraform module for provisioning.

**Key principle:** Defense in depth — every layer assumes the previous one might fail.
