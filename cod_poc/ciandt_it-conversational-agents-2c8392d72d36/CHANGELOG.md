# Changelog

All notable changes to this project are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/).

## [1.0.16] — 2026-04-27

### Changed
- Reorganized domain-specific files into `domains/{slug}/` structure (ADR-013)
- Updated README with "How To" guides for BanQi deploy and new domain creation
- Removed dev tracking files from repo

## [1.0.15] — 2026-04-24

### Added
- BanQi domain documents for Bedrock Knowledge Base (11 docs)
- Domain template (`domains/_template/`) with quick start guide

### Changed
- Dockerfile, env example, test fixtures updated for domains/ structure

## [1.0.14] — 2026-04-23

### Fixed
- IaC review: 20/20 issues addressed — IAM scoped (zero `Resource: '*'`), Secrets Manager integration, VPC endpoints

## [1.0.13] — 2026-04-22

### Added
- WhatsApp `create_event` memory persistence
- Dual API Gateway format support

### Fixed
- Session ID fix for WhatsApp channel

## [1.0.12] — 2026-04-21

### Changed
- Rewrote all prompts from PAF with delegation rules and few-shot examples

## [1.0.11] — 2026-04-20

### Added
- Memory STM + LTM integration (AgentCore Memory)
- Bedrock Guardrails (prompt attack + topic policy)
- Model-per-agent support (Sonnet supervisor + Haiku sub-agents)
- `tools_source` registry for sub-agent tool binding

## [1.0.10] — 2026-04-19

### Added
- Container build + KB docs upload + ingestion via Terraform
- Knowledge Base with OpenSearch Serverless

### Changed
- KB and WhatsApp enabled by default in `terraform apply`

## [1.0.9] — 2026-04-18

### Added
- Terraform modules: guardrails, knowledge_base, whatsapp (T-040/T-041)

## [1.0.8] — 2026-04-17

### Added
- Pre-commit hooks: detect-secrets, tfsec, checkov, ruff
- Unit tests for core modules
- `.coverage` to `.gitignore`

### Fixed
- 9 fixes from review round 4
- Dependencies and build backend in `pyproject.toml`

## [1.0.7] — 2026-04-16

### Added
- Security, tests, and CI/CD — Phase 5
  - PIIMaskingFilter (CPF, phone, email)
  - Bedrock Guardrails integration
  - pytest config (unit, integration, container, e2e markers)
  - GitHub Actions + Bitbucket Pipelines

## [1.0.6] — 2026-04-15

### Added
- Terraform, CloudFormation, CDK infrastructure — Phase 4
  - 8 Terraform modules (iam, runtime, memory, gateway, network, guardrails, knowledge_base, whatsapp)
  - VPC with private subnets + 7 VPC Endpoints (PrivateLink)
  - WAF (rate limit 1000/5min)

## [1.0.5] — 2026-04-14

### Added
- WhatsApp channel — Phase 3
  - Lambda handler with webhook verification
  - HMAC signature validation
  - DynamoDB dedup (idempotency)
  - Chainlit dev/test interface

## [1.0.4] — 2026-04-13

### Added
- Agent orchestration — Phase 2
  - Agent factory with agents-as-tools pattern
  - AgentCore Memory setup (STM + LTM)
  - AgentCore Gateway token manager
  - Main entrypoint (`src/main.py`)

## [1.0.3] — 2026-04-12

### Added
- Core modules — Phase 1
  - Domain schema (Pydantic v2, 11 models)
  - Domain loader (singleton, thread-safe, fail-fast)
  - Settings module (`src/config/settings.py`)
  - Agent context (`src/agents/context.py`)
  - Utils: logging, PII masking, validation, secrets

## [1.0.0] — 2026-04-11

### Added
- Initial project scaffold
- Project structure and `pyproject.toml`
