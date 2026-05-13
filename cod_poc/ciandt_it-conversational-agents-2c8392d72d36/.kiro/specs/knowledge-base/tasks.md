# Knowledge Base — Tasks

## Status: ✅ Complete (Fase 4)

---

## T-KB-001: Domain Documents
- [x] Create `domains/banqi-banking/kb-docs/` with 11 banking documents
- [x] Formats: Markdown (.md)

**Files:** `domains/banqi-banking/kb-docs/` (11 files)

## T-KB-002: Terraform Module
- [x] Create `infrastructure/terraform/modules/knowledge_base/`
- [x] S3 bucket for documents
- [x] Bedrock KB with S3 Vectors data source
- [x] Document upload via `aws_s3_object`
- [x] Ingestion job trigger
- [x] Output: `BEDROCK_KB_ID`

**Files:** `infrastructure/terraform/modules/knowledge_base/`

## T-KB-003: Tool Binding
- [x] `_get_kb_tools()` in factory.py — returns `retrieve` if KNOWLEDGE_BASE_ID set
- [x] `BEDROCK_KB_ID` → `KNOWLEDGE_BASE_ID` propagation in main.py

**Files:** `src/agents/factory.py`, `src/main.py`

## T-KB-004: Knowledge Agent Prompt
- [x] Create `domains/banqi-banking/prompts/knowledge.md`
- [x] Search strategy, result presentation, out-of-scope handling

**Files:** `domains/banqi-banking/prompts/knowledge.md`

---

## Reconstruction Guide

1. **Write domain documents** in `domains/{slug}/kb-docs/` (Markdown recommended).
2. **Terraform module** — S3 bucket + Bedrock KB + ingestion. Output `BEDROCK_KB_ID`.
3. **Tool binding** — `_get_kb_tools()` returns `strands_tools.retrieve` when `KNOWLEDGE_BASE_ID` is set.
4. **Knowledge prompt** — defines how the agent searches and presents KB results.
