# Contributing

## Setup

```bash
git clone <repo-url>
cd conversational-agents
uv venv && source .venv/bin/activate
uv sync --all-extras
pre-commit install
```

## Pre-commit Hooks

Installed automatically via `pre-commit install`. Runs on every commit:

| Hook | What it does |
|---|---|
| `detect-secrets` | Blocks commits with secrets (API keys, tokens) |
| `tfsec` | Scans Terraform for security issues |
| `checkov` | IaC security scanning (all providers) |
| `ruff` | Python linting + auto-fix |
| `ruff-format` | Python formatting (black-compatible) |

To run manually: `pre-commit run --all-files`

## Code Style

- **Formatter**: `ruff format` (line length: 120)
- **Linter**: `ruff check` (rules: E, F, I, W, S, B, UP, SIM)
- **Type hints**: required on all functions
- **Docstrings**: Google style
- **Python**: 3.12+

## Testing

```bash
pytest -m unit                    # Unit tests (zero AWS) — every commit
pytest -m critical                # Critical issues C1-C7
pytest --cov=src --cov-report=term-missing  # With coverage
```

Test markers:
- `unit` — no AWS dependencies, fast
- `critical` — critical path validation
- `staging` — requires staging URL
- `container` — requires Docker

Coverage target: 80% minimum.

## Branching

- `main` — production-ready, protected
- `feature/<desc>` — new features
- `fix/<desc>` — bug fixes

## Commits

Format: `type(scope): description`

```
feat(agents): add memory STM+LTM integration
fix(whatsapp): correct session ID extraction
docs: update HANDOFF with phase 7
refactor: reorganize domain files into domains/{slug}/
test(unit): add schema validation tests
chore: update pre-commit hooks
```

## Project Structure

```
domains/{slug}/     ← Domain config (YAML + prompts + kb-docs)
src/                ← Python code (never changes per domain)
infrastructure/     ← Terraform, CloudFormation, CDK
tests/              ← unit, integration, container, e2e
```

**Key rule**: to add a new domain, copy `domains/_template/` and edit. No Python changes needed.

## Docker

```bash
# Build
docker build -t conversational-agents .

# Run with docker-compose (includes DynamoDB Local)
docker compose up -d

# Health check
curl http://localhost:8080/ping
```

See [Docker Compose](#docker-compose) section below for details.

## Docker Compose

The `docker-compose.yml` provides two services:

### `agent` — Main application
- Builds from `Dockerfile`
- Port: `8080`
- Env vars from shell (with defaults for model IDs)
- Health check: `GET /ping` every 10s
- Depends on DynamoDB being healthy

### `dynamodb` — DynamoDB Local
- Image: `amazon/dynamodb-local:latest`
- Port: `8000`
- Shared DB mode (single file)
- Health check: curl every 5s

### Usage

```bash
# Start both services
docker compose up -d

# Check health
docker compose ps

# View logs
docker compose logs -f agent

# Stop
docker compose down
```

### Environment Variables

Set before running `docker compose up`:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...          # if using temporary credentials
export AGENTCORE_MEMORY_ID=...        # from terraform output
```

Optional overrides (have defaults):
- `DOMAIN_DIR` — default: `domains/banqi-banking`
- `SUPERVISOR_AGENT_MODEL_ID` — default: `us.anthropic.claude-sonnet-4-6`
- `SERVICES_AGENT_MODEL_ID` — default: `us.anthropic.claude-sonnet-4-6`
- `KNOWLEDGE_AGENT_MODEL_ID` — default: `us.anthropic.claude-sonnet-4-6`
- `AWS_REGION` — default: `us-east-1`
