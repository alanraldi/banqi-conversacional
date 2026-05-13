# Security & Guardrails — Requirements

## Functional Requirements

### FR-SG-001: Bedrock Guardrails
WHEN a message is sent to the LLM
THE SYSTEM SHALL apply Bedrock Guardrails with prompt attack detection (HIGH) and topic policy (off-topic DENY).

### FR-SG-002: PII Masking in Logs
WHEN any log message is written
THE SYSTEM SHALL mask CPF, phone numbers, and email addresses using regex patterns
AND SHALL prefer false positives over false negatives.

### FR-SG-003: Input Validation
WHEN user input is received
THE SYSTEM SHALL reject empty input and input exceeding 4096 characters.

### FR-SG-004: User ID Sanitization
WHEN extracting user_id from payload
THE SYSTEM SHALL keep only alphanumeric chars, hyphens, underscores, and plus signs (max 64 chars)
SO THAT namespace injection and path traversal are prevented.

### FR-SG-005: Secrets Management
WHEN a secret is needed
THE SYSTEM SHALL check env var first (dev), then Secrets Manager (prod)
AND SHALL fail-fast with RuntimeError if not found (no fallback values).

### FR-SG-006: Path Traversal Protection
WHEN domain.yaml is loaded
THE SYSTEM SHALL reject prompt_file paths containing `..` or starting with `/`.

### FR-SG-007: LGPD Right to Erasure
WHEN a user requests data deletion
THE SYSTEM SHALL provide `scripts/delete_user_data.py` to remove all user data from Memory.

### FR-SG-008: CPF Validation
WHEN a CPF is provided
THE SYSTEM SHALL validate format (11 digits) and check digits
AND SHALL provide masked display format (`***.***.*89-00`).

## Non-Functional Requirements

### NFR-SG-001: Structured Logging
THE SYSTEM SHALL output logs as single-line JSON (CloudWatch compatible)
WITH fields: timestamp, level, logger, message, and optional context fields.

### NFR-SG-002: IAM Least Privilege
THE SYSTEM SHALL use zero `Resource: '*'` in IAM policies — all ARNs scoped.

### NFR-SG-003: Network Security
THE SYSTEM SHALL run in VPC private subnets with 7 VPC Endpoints (PrivateLink)
AND SHALL use WAF with rate limiting (1000 req/5min) on public endpoints.

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-SG-001 | PII masked in log output | `tests/unit/test_pii.py` |
| AC-SG-002 | Path traversal rejected | `tests/unit/test_schema.py` |
| AC-SG-003 | HMAC signature validated | `tests/unit/test_signature.py` |
| AC-SG-004 | Input length enforced | `tests/unit/test_validation.py` |
| AC-SG-005 | Secrets fail-fast on missing | `tests/unit/test_validation.py` |
| AC-SG-006 | IAM zero wildcard resources | `tests/unit/infra/test_terraform.py` |
| AC-SG-007 | Structured JSON logging works | `tests/unit/test_logging.py` |
| AC-SG-008 | CPF/phone validation correct | `tests/unit/test_validation.py` |
