# Knowledge Base — Design

## Overview

Integrates Amazon Bedrock Knowledge Base for RAG (Retrieval-Augmented Generation). Domain documents in `domains/{slug}/kb-docs/` are uploaded to S3, chunked, and indexed automatically via Terraform. The Knowledge Agent uses the `retrieve` tool from `strands_tools` to query the KB.

## Architecture

```
domains/banqi-banking/kb-docs/
├── conta-digital.md
├── emprestimos.md
├── ... (11 docs)
    │
    ▼ (terraform apply → S3 upload + ingestion)
┌─────────────────────────────────┐
│  S3 Bucket (kb-docs)            │
└─────────────────────────────────┘
    │
    ▼ (Bedrock KB ingestion)
┌─────────────────────────────────┐
│  Bedrock Knowledge Base         │
│  ├── Chunking: 300 tokens       │
│  ├── Overlap: 20%               │
│  └── Vector store: S3 Vectors   │
└─────────────────────────────────┘
    │
    ▼ (retrieve tool)
┌─────────────────────────────────┐
│  Knowledge Agent (Haiku)        │
│  └── tools: [retrieve]          │
│      └── KNOWLEDGE_BASE_ID env  │
└─────────────────────────────────┘
```

## Components

### KB Documents (`domains/{slug}/kb-docs/`)
- Supported formats: `.pdf`, `.md`, `.txt`, `.html`, `.docx`, `.csv`
- Chunked automatically by Bedrock KB (300 tokens, 20% overlap)
- Terraform uploads to S3 and triggers ingestion on `terraform apply`

### Tool Binding (`factory.py → _get_kb_tools()`)
- Returns `strands_tools.retrieve` if `KNOWLEDGE_BASE_ID` env var is set
- `KNOWLEDGE_BASE_ID` propagated from `BEDROCK_KB_ID` in main.py startup
- Degraded mode: empty list if not configured

### Knowledge Agent Prompt (`prompts/knowledge.md`)
- Defines search strategy, how to present results, out-of-scope handling
- Domain-specific — lives in `domains/{slug}/prompts/`

### Terraform Module (`infrastructure/terraform/modules/knowledge_base/`)
- S3 bucket for documents
- Bedrock KB with S3 Vectors data source
- Ingestion job triggered on apply
- Outputs: `BEDROCK_KB_ID`

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| S3 Vectors | Over OpenSearch Serverless | Simpler, lower cost for PoC |
| 300 token chunks | With 20% overlap | Balance between context and precision |
| Terraform ingestion | Triggered on apply | Documents update with infrastructure deploy |
| retrieve tool | From strands_tools | Native Strands integration, handles KB query + response formatting |
