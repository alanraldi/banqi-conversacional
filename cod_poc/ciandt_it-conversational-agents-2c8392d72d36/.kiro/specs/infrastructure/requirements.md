# Infrastructure — Requirements

## Functional Requirements

### FR-IF-001: Single Command Deploy
WHEN `terraform apply` is executed with domain variables
THE SYSTEM SHALL provision all ~36 resources (ECR, Runtime, Memory, Gateway, KB, Guardrails, Lambda, API GW, DynamoDB, VPC, WAF).

### FR-IF-002: Domain-Driven Variables
WHEN deploying for a new domain
THE SYSTEM SHALL accept `domain_slug`, `agent_name`, `memory_name`, `image_tag` as variables
SO THAT the same Terraform code deploys any domain.

### FR-IF-003: IAM Least Privilege
THE SYSTEM SHALL scope all IAM policies to specific resource ARNs
AND SHALL have zero `Resource: '*'` in any policy.

### FR-IF-004: VPC Mode
WHEN `vpc_mode` is set
THE SYSTEM SHALL support three modes:
- `create` — provision new VPC with private subnets + VPC Endpoints
- `existing` — use provided VPC/subnet IDs
- `none` — skip VPC (for dev/testing)

### FR-IF-005: Container Security
THE SYSTEM SHALL build ARM64 containers with non-root user (UID 1000), HEALTHCHECK, and Trivy scan.

### FR-IF-006: WhatsApp Resources
WHEN WhatsApp channel is enabled
THE SYSTEM SHALL provision Lambda + API Gateway + WAF + DynamoDB dedup + Secrets Manager.

### FR-IF-007: KB Document Upload
WHEN `terraform apply` is executed
THE SYSTEM SHALL upload documents from `domains/{slug}/kb-docs/` to S3 and trigger KB ingestion.

### FR-IF-008: Outputs
WHEN deploy completes
THE SYSTEM SHALL output: `AGENTCORE_MEMORY_ID`, `BEDROCK_KB_ID`, `BEDROCK_GUARDRAIL_ID`, `webhook_url`.

## Non-Functional Requirements

### NFR-IF-001: Network Security
THE SYSTEM SHALL use VPC private subnets with 7 VPC Endpoints (PrivateLink) for all AWS service calls.

### NFR-IF-002: WAF Protection
THE SYSTEM SHALL apply WAF rate limiting (1000 req/5min) on the WhatsApp webhook endpoint.

### NFR-IF-003: Encryption
THE SYSTEM SHALL enable encryption at rest for S3, DynamoDB, and Secrets Manager.

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-IF-001 | terraform plan succeeds | CI pipeline |
| AC-IF-002 | Zero `Resource: '*'` in IAM | `tests/unit/infra/test_terraform.py` |
| AC-IF-003 | Container health check passes | `tests/container/test_health.sh` |
| AC-IF-004 | Webhook URL accessible | `tests/e2e/test_staging_whatsapp.py` |
| AC-IF-005 | KB ingestion completes | Terraform apply output |
| AC-IF-006 | CloudFormation template valid | `tests/unit/infra/test_cloudformation.py` |
| AC-IF-007 | CDK stack synthesizes | `tests/unit/infra/test_cdk_stack.py` |
| AC-IF-008 | Container invocation works | `tests/container/test_invocation.sh` |
| AC-IF-009 | Staging health check passes | `tests/e2e/test_staging_health.py` |
| AC-IF-010 | Staging invocation works | `tests/e2e/test_staging_invocation.py` |
