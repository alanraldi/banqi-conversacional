# Knowledge Base — Requirements

## Functional Requirements

### FR-KB-001: Document Ingestion
WHEN `terraform apply` is executed
THE SYSTEM SHALL upload documents from `domains/{slug}/kb-docs/` to S3 and trigger Bedrock KB ingestion.

### FR-KB-002: RAG Retrieval
WHEN the Knowledge Agent receives a query
THE SYSTEM SHALL use the `retrieve` tool to search the Bedrock Knowledge Base
AND SHALL return relevant document chunks to the agent.

### FR-KB-003: KB Tool Binding
WHEN `tools_source` is `bedrock_kb` in domain.yaml
THE SYSTEM SHALL bind the `retrieve` tool from `strands_tools` to the sub-agent
USING the `KNOWLEDGE_BASE_ID` environment variable.

### FR-KB-004: Degraded Mode
WHEN `KNOWLEDGE_BASE_ID` is not configured
THE SYSTEM SHALL log a warning and run the Knowledge Agent without the retrieve tool.

## Acceptance Criteria

| ID | Criterion | Verified By |
|---|---|---|
| AC-KB-001 | Documents uploaded to S3 on terraform apply | Terraform plan |
| AC-KB-002 | KB ingestion triggered | Terraform apply output |
| AC-KB-003 | retrieve tool returns relevant results | E2E test |
| AC-KB-004 | Agent works without KB when ID not set | Integration test |
