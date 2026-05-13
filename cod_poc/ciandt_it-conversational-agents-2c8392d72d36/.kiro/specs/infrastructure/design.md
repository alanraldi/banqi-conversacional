# Infrastructure — Design

## Overview

Full-stack IaC using Terraform (8 modules). A single `terraform apply` provisions ~36 AWS resources: ECR + container, AgentCore Runtime/Memory/Gateway, Bedrock KB, Guardrails, IAM roles, Lambda WhatsApp + API Gateway + DynamoDB dedup, VPC + VPC Endpoints + WAF.

## Module Architecture

```
infrastructure/terraform/
├── main.tf              ← Module composition
├── variables.tf         ← Input variables
├── outputs.tf           ← Exported values
├── providers.tf         ← AWS provider config
├── terraform.tfvars     ← Environment-specific values
└── modules/
    ├── iam/             ← IAM roles + policies (zero Resource: '*')
    ├── runtime/         ← ECR + AgentCore Runtime (ARM64 container)
    ├── memory/          ← AgentCore Memory (STM + LTM strategies)
    ├── gateway/         ← AgentCore Gateway (Cognito OAuth, MCP targets)
    ├── network/         ← VPC + private subnets + 7 VPC Endpoints
    ├── guardrails/      ← Bedrock Guardrails (prompt attack + topic policy)
    ├── knowledge_base/  ← Bedrock KB + S3 + ingestion
    └── whatsapp/        ← Lambda + API Gateway + DynamoDB dedup + WAF
```

## Module Details

### `iam/` — IAM Roles & Policies
- Runtime execution role (Bedrock, Memory, Gateway, Logs, ECR)
- Lambda execution role (AgentCore invoke, DynamoDB, Secrets Manager, Logs)
- All ARNs scoped — zero `Resource: '*'`

### `runtime/` — AgentCore Runtime
- ECR repository + container image (ARM64, non-root UID 1000)
- AgentCore Runtime configuration
- Health check: `/ping`

### `memory/` — AgentCore Memory
- Memory store with strategies: SEMANTIC, USER_PREFERENCE, SUMMARIZATION
- Namespaces configured per domain

### `gateway/` — AgentCore Gateway
- Cognito User Pool + OAuth client credentials
- MCP tool targets (Lambda ARNs from `gateway_tools` variable)

### `network/` — VPC & Networking
- VPC with private subnets (multi-AZ)
- 7 VPC Endpoints (PrivateLink): Bedrock, Bedrock Runtime, Bedrock Agent, Bedrock AgentCore, ECR (api + dkr), S3, Logs, Secrets Manager
- `vpc_mode` tri-state: `create` / `existing` / `none` (ADR-012)

### `guardrails/` — Bedrock Guardrails
- Prompt attack detection (HIGH sensitivity)
- Topic policy (off-topic DENY)
- Configurable via variables

### `knowledge_base/` — Bedrock KB
- S3 bucket for domain documents
- Bedrock KB with S3 Vectors
- Auto-upload from `domains/{slug}/kb-docs/`
- Ingestion job on apply

### `whatsapp/` — WhatsApp Channel
- Lambda function (Python, from `src/channels/whatsapp/`)
- API Gateway (REST) with webhook route
- WAF (rate limit 1000 req/5min)
- DynamoDB table (dedup, TTL enabled)
- Secrets Manager for WhatsApp credentials

## CI/CD

### Bitbucket Pipelines (dev)
- `bitbucket-pipelines.yml` — lint, test, build, deploy to staging

### GitHub Actions (prod)
- `.github/workflows/test.yml` — pytest + ruff on PR
- `.github/workflows/security.yml` — Trivy container scan

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Terraform over CDK | For IaC | Team familiarity, state management, module ecosystem |
| 8 separate modules | Over monolith | Independent lifecycle, reusable, testable |
| vpc_mode tri-state | create/existing/none | Flexible: new VPC, reuse existing, or skip (ADR-012) |
| ARM64 container | Graviton | Cost + performance (Well-Architected Sustainability) |
| Full-stack apply | Single terraform apply | One command deploys everything (ADR-009) |
| Dual CI/CD | Bitbucket (dev) + GitHub (prod) | ADR-007 — different teams/repos |

## Key Variables

```hcl
domain_slug    = "banqi-banking"
agent_name     = "banqi_multi_agent"
environment    = "staging"
aws_account_id = "123456789012"
aws_region     = "us-east-1"
memory_name    = "BanQiMemory"
image_tag      = "v1.0.16"
```
