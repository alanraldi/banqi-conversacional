# Domain Template

## Quick Start — New Domain in 5 Steps

### 1. Copy this template

```bash
cp -r domains/_template domains/your-domain-slug
```

### 2. Edit `domain.yaml`

Set your domain name, slug, agent descriptions, and welcome message.
The slug is used in AWS resource names — use lowercase and hyphens only.

### 3. Write prompts

Edit the 3 prompt files in `prompts/`:

- **supervisor.md** — Decision tree for routing user intent to the correct sub-agent. Include domain-specific intent patterns and few-shot examples.
- **services.md** — Operational workflows, tool usage rules, validation logic.
- **knowledge.md** — Search strategy, response guidelines, out-of-scope definition.

Tip: Use `domains/banqi-banking/prompts/` as a reference for structure and detail level.

### 4. Add Knowledge Base documents

Place your domain documents in `kb-docs/`. Supported formats: `.pdf`, `.md`, `.txt`, `.html`, `.docx`, `.csv`.

These are automatically chunked and indexed by Bedrock Knowledge Base during `terraform apply`.

### 5. Deploy

```bash
# Set the domain
export DOMAIN_DIR=domains/your-domain-slug

# Deploy infrastructure
cd infrastructure/terraform
terraform apply \
  -var domain_slug=your-domain-slug \
  -var image_tag=v1.0.0
```

## File Reference

| File | Purpose |
|------|---------|
| `domain.yaml` | Agent identity, sub-agents, memory, channels, messages |
| `prompts/supervisor.md` | Supervisor routing logic and decision framework |
| `prompts/services.md` | Services agent operational workflows |
| `prompts/knowledge.md` | Knowledge agent search and response strategy |
| `kb-docs/` | Documents for Bedrock Knowledge Base (RAG) |
