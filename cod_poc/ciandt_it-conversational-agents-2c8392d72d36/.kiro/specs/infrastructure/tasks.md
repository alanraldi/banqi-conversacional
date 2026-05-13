# Infrastructure — Tasks

## Status: ✅ Complete (Fase 4 + 6)

---

## T-IF-001: IAM Module
- [x] Runtime execution role (Bedrock, Memory, Gateway, Logs, ECR)
- [x] Lambda execution role (AgentCore invoke, DynamoDB, Secrets Manager, Logs)
- [x] All ARNs scoped — zero `Resource: '*'`

**Files:** `infrastructure/terraform/modules/iam/`

## T-IF-002: Runtime Module
- [x] ECR repository
- [x] AgentCore Runtime configuration
- [x] ARM64 container build + push

**Files:** `infrastructure/terraform/modules/runtime/`

## T-IF-003: Memory Module
- [x] AgentCore Memory store
- [x] Strategies: SEMANTIC, USER_PREFERENCE, SUMMARIZATION

**Files:** `infrastructure/terraform/modules/memory/`

## T-IF-004: Gateway Module
- [x] AgentCore Gateway
- [x] Cognito User Pool + OAuth client credentials
- [x] MCP tool targets from `gateway_tools` variable

**Files:** `infrastructure/terraform/modules/gateway/`

## T-IF-005: Network Module
- [x] VPC with private subnets (multi-AZ)
- [x] 7 VPC Endpoints (PrivateLink)
- [x] `vpc_mode` tri-state (create/existing/none)

**Files:** `infrastructure/terraform/modules/network/`

## T-IF-006: Guardrails Module
- [x] Bedrock Guardrail (prompt attack HIGH + topic policy)
- [x] Configurable via variables

**Files:** `infrastructure/terraform/modules/guardrails/`

## T-IF-007: Knowledge Base Module
- [x] S3 bucket + document upload
- [x] Bedrock KB with S3 Vectors
- [x] Ingestion job trigger

**Files:** `infrastructure/terraform/modules/knowledge_base/`

## T-IF-008: WhatsApp Module
- [x] Lambda function + API Gateway (REST)
- [x] WAF (rate limit 1000/5min)
- [x] DynamoDB dedup table (TTL enabled)
- [x] Secrets Manager for WhatsApp credentials

**Files:** `infrastructure/terraform/modules/whatsapp/`

## T-IF-009: Root Configuration
- [x] `main.tf` — module composition
- [x] `variables.tf` — domain-driven inputs
- [x] `outputs.tf` — AGENTCORE_MEMORY_ID, BEDROCK_KB_ID, etc.
- [x] `providers.tf` — AWS provider
- [x] `terraform.tfvars.example`

**Files:** `infrastructure/terraform/`

## T-IF-010: CI/CD
- [x] GitHub Actions: test.yml (pytest + ruff), security.yml (Trivy)
- [x] Bitbucket Pipelines: bitbucket-pipelines.yml
- [x] Pre-commit hooks: detect-secrets, tfsec, checkov, ruff

**Files:** `.github/workflows/`, `bitbucket-pipelines.yml`, `.pre-commit-config.yaml`

## T-IF-011: Container
- [x] Dockerfile (ARM64, non-root UID 1000, HEALTHCHECK, UV + OpenTelemetry)
- [x] docker-compose.yml (agent + DynamoDB Local)
- [x] `.trivyignore` for container scanning

**Files:** `Dockerfile`, `docker-compose.yml`, `.trivyignore`

---

## Reconstruction Guide

1. **Start with `iam/`** — roles and policies. Scope all ARNs.
2. **Build `network/`** — VPC + VPC Endpoints. Support tri-state `vpc_mode`.
3. **Build `runtime/`** — ECR + AgentCore Runtime.
4. **Build `memory/`** — AgentCore Memory with strategies.
5. **Build `gateway/`** — Cognito + MCP targets.
6. **Build `guardrails/`** — Bedrock Guardrail config.
7. **Build `knowledge_base/`** — S3 + KB + ingestion.
8. **Build `whatsapp/`** — Lambda + API GW + WAF + DynamoDB + Secrets.
9. **Compose in `main.tf`** — wire all modules with shared variables.
10. **Add CI/CD** — GitHub Actions + Bitbucket Pipelines + pre-commit.

**Key principle:** `terraform apply -var image_tag=v1.0.16` deploys everything. One command, full stack.
