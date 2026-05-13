# Feature: conversational-agents — Framework Multi-Agente Conversacional Genérico

## Problem Statement

O projeto `paf-conversational-banking` implementa um assistente bancário (BanQi) multi-agente com arquitetura sólida (Agents-as-Tools, AgentCore Memory STM+LTM, MCP Gateway, Bedrock Guardrails), porém está **fortemente acoplado ao domínio bancário** com **73+ pontos de acoplamento** em 12+ arquivos. Isso impede a reutilização da arquitetura para outros domínios (healthcare, retail, telecom, insurance).

Além disso, o projeto possui **7 issues críticos** de segurança e estabilidade identificados em auditoria:
- Race condition em estado global compartilhado entre requests
- Resource leaks em clientes MCP
- Fallback silencioso para tokens inválidos
- IAM policies com wildcards irrestritos
- Zero validação de input em dados sensíveis (CPF)
- PII logado em texto claro (violação LGPD)
- Webhook signature validation desabilitada

O projeto `conversational-agents` resolve esses problemas criando um **framework genérico e configurável** onde todo acoplamento ao domínio é extraído para `config/domain.yaml` + `prompts/*.md`, mantendo a camada de orquestração 100% reutilizável.

## Objetivos

1. **Genericidade**: Qualquer domínio configurável via `domain.yaml` + prompts externos `.md`
2. **Segurança**: Resolver todos os 7 critical issues do relatório de auditoria
3. **Multi-canal**: Channel adapter pattern (WhatsApp produção + Chainlit dev/teste)
4. **Infraestrutura agnóstica**: Suporte a Terraform, CloudFormation e CDK
5. **Extensibilidade**: Novos canais (Telegram, Slack, Teams) sem alterar orquestração

## Stack Técnica

- Python 3.12+, UV para dependências
- Strands Agent Framework (Agents-as-Tools pattern)
- AWS AgentCore Runtime (deploy, memory, gateway, observability)
- Amazon Bedrock (Claude Sonnet 4, Knowledge Base, Guardrails)
- SAM CLI (WhatsApp Lambda webhook)
- Pydantic v2 para validação de configuração e input
- OpenTelemetry para observabilidade


---

## Arquitetura em 3 Camadas

```
┌─────────────────────────────────────────────────┐
│  CAMADA 1: DOMÍNIO (config/ + prompts/)         │  ← Único que muda por vertical
│  • domain.yaml (nomes, descrições, canais)      │
│  • prompts/*.md (supervisor, sub-agents)        │
│  • Tool descriptions e docstrings               │
│  • Mensagens de erro e welcome messages         │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  CAMADA 2: ORQUESTRAÇÃO (src/)                  │  ← Reutilizável, genérico
│  • Supervisor pattern + Agents-as-Tools         │
│  • Domain loader (YAML → config objects)        │
│  • AgentCore Memory (STM+LTM)                  │
│  • AgentCore Gateway (MCP)                      │
│  • Channel adapters (WhatsApp, Chainlit)        │
│  • Session management thread-safe               │
│  • PII masking + input validation               │
└─────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────┐
│  CAMADA 3: INFRAESTRUTURA (infrastructure/)     │  ← Agnóstica
│  • infrastructure/terraform/                    │
│  • infrastructure/cloudformation/               │
│  • infrastructure/cdk/                          │
│  • Dockerfile genérico (ARM64)                  │
│  • .bedrock_agentcore.yaml (gerado)            │
└─────────────────────────────────────────────────┘
```

### Estrutura de Diretórios Alvo

```
conversational-agents/
├── config/
│   └── domain.yaml
├── prompts/
│   ├── supervisor.md
│   ├── services.md
│   └── knowledge.md
├── src/
│   ├── main.py
│   ├── agents/
│   │   ├── supervisor.py
│   │   ├── agent_factory.py
│   │   └── base.py
│   ├── config/
│   │   ├── settings.py
│   │   ├── models.py
│   │   └── domain_loader.py
│   ├── channels/
│   │   ├── base.py
│   │   ├── whatsapp/
│   │   └── chainlit/
│   ├── memory/
│   │   └── memory_setup.py
│   ├── tools/
│   │   └── (domain-specific, registradas via gateway)
│   └── utils/
│       ├── pii.py
│       ├── validation.py
│       └── logging.py
├── infrastructure/
│   ├── terraform/
│   ├── cloudformation/
│   └── cdk/
├── scripts/
│   └── setup.py
├── tests/
├── Dockerfile
├── pyproject.toml
└── .bedrock_agentcore.yaml
```


---

## User Stories (Formato EARS)

### Camada 1: Domínio (Configuração)

#### US-01: Configuração de domínio via YAML

**Como** desenvolvedor que quer criar um assistente para um novo domínio,
**quero** configurar todo o comportamento específico do domínio em um único arquivo `domain.yaml`,
**para que** eu não precise modificar código Python da camada de orquestração.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL load all domain-specific configuration from `config/domain.yaml` at startup.
- [ ] **[When]** When `config/domain.yaml` is missing or malformed, the system SHALL fail fast with a descriptive error message indicating the missing/invalid fields.
- [ ] **[When]** When `domain.yaml` defines `supervisor.prompt_file`, the system SHALL load the supervisor system prompt from that file path relative to project root.
- [ ] **[When]** When `domain.yaml` defines entries in `sub_agents`, the system SHALL create one Strands Agent per entry using the specified `name`, `prompt_file`, `tool_docstring`, and `model_id_env`.
- [ ] **[When]** When `domain.yaml` defines `memory.namespaces`, the system SHALL configure AgentCore Memory retrieval with the specified `top_k` and `relevance_score` per namespace.
- [ ] **[When]** When `domain.yaml` defines `channels`, the system SHALL enable only the channels marked `enabled: true`.
- [ ] **[Ubiquitous]** The system SHALL validate `domain.yaml` against a Pydantic schema at startup, rejecting unknown fields.

#### US-02: Prompts externalizados em arquivos Markdown

**Como** prompt engineer,
**quero** editar os prompts dos agentes em arquivos `.md` separados,
**para que** eu possa iterar nos prompts sem tocar em código Python.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL load agent system prompts from `.md` files referenced in `domain.yaml`.
- [ ] **[When]** When a prompt file referenced in `domain.yaml` does not exist, the system SHALL fail fast with error: `"Prompt file not found: {path}"`.
- [ ] **[When]** When a prompt file is loaded, the system SHALL apply Bedrock prompt caching (SystemContentBlock + cachePoint) to the loaded content.
- [ ] **[Ubiquitous]** The system SHALL NOT contain any hardcoded agent prompts in Python source files.

#### US-03: Mensagens de interface configuráveis

**Como** product owner,
**quero** configurar welcome messages e mensagens de erro no `domain.yaml`,
**para que** eu possa personalizar a experiência do usuário sem deploy.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When a new user session starts, the system SHALL display the `interface.welcome_message` from `domain.yaml`.
- [ ] **[When]** When an error occurs during processing, the system SHALL return the `error_messages.generic` from `domain.yaml`.
- [ ] **[When]** When the user sends an empty message, the system SHALL return the `error_messages.empty_input` from `domain.yaml`.

#### US-04: Validação de schema do domain.yaml

**Como** desenvolvedor,
**quero** que o `domain.yaml` seja validado com Pydantic ao carregar,
**para que** erros de configuração sejam detectados no startup e não em runtime.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL define a `DomainConfig` Pydantic model that validates the complete `domain.yaml` structure.
- [ ] **[When]** When required fields are missing (`domain.name`, `supervisor.prompt_file`, at least one `sub_agents` entry), the system SHALL raise `ValidationError` with field-level details.
- [ ] **[When]** When `model_id_env` references an environment variable that is not set, the system SHALL fail fast with: `"Environment variable {var} required by agent {name} is not set"`.


### Camada 2: Orquestração

#### US-05: Supervisor Agent genérico com Agents-as-Tools

**Como** desenvolvedor,
**quero** que o Supervisor Agent seja criado dinamicamente a partir do `domain.yaml`,
**para que** a coordenação multi-agente funcione para qualquer domínio sem alterar código.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL create a Supervisor Agent whose system prompt is loaded from the file specified in `supervisor.prompt_file`.
- [ ] **[Ubiquitous]** The system SHALL register each sub-agent defined in `domain.yaml` as a `@tool` function available to the Supervisor, using the `tool_docstring` as the tool description.
- [ ] **[When]** When a user message arrives, the Supervisor Agent SHALL analyze intent and delegate to the appropriate sub-agent tool.
- [ ] **[When]** When a sub-agent returns a response, the Supervisor SHALL pass it through to the user without rewriting.
- [ ] **[Ubiquitous]** The system SHALL use `BedrockModel` with the model ID resolved from the environment variable specified in `model_id_env`.

#### US-06: Thread-safe session context (Fix C1)

**Como** operador de produção,
**quero** que o contexto de sessão seja thread-safe,
**para que** não haja vazamento de dados entre sessões concorrentes.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL store per-request context (user_id, session_id) in `threading.local()` instead of a global mutable dict.
- [ ] **[Ubiquitous]** The system SHALL NOT use module-level mutable dicts to share state between the Supervisor and sub-agent tool functions.
- [ ] **[While]** While multiple requests are processed concurrently, the system SHALL guarantee that each request's user_id and session_id are isolated.

#### US-07: MCP Client lifecycle management (Fix C2)

**Como** operador de produção,
**quero** que o MCP Client seja gerenciado como singleton com cleanup,
**para que** não haja resource leaks em produção.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL manage MCP client connections as a singleton with proper lifecycle (init + cleanup).
- [ ] **[When]** When the application shuts down, the system SHALL close all open MCP client connections.
- [ ] **[Ubiquitous]** The system SHALL NOT call `__enter__()` without a corresponding `__exit__()` on MCP clients.

#### US-08: AgentCore Memory integration

**Como** desenvolvedor,
**quero** que a memória AgentCore (STM+LTM) seja configurada a partir do `domain.yaml`,
**para que** os namespaces de memória sejam personalizáveis por domínio.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When `domain.yaml` defines `memory.namespaces`, the system SHALL configure `AgentCoreMemoryConfig` with `RetrievalConfig` per namespace using the specified `top_k` and `relevance_score`.
- [ ] **[When]** When a user_id is provided, the system SHALL create an `AgentCoreMemorySessionManager` with the memory_id from `AGENTCORE_MEMORY_ID` env var.
- [ ] **[Ubiquitous]** The system SHALL use `SlidingWindowConversationManager` with configurable `window_size` from settings.
- [ ] **[When]** When `AGENTCORE_MEMORY_ID` is not set, the system SHALL fail fast with a descriptive error.

#### US-09: Fail-fast on missing credentials (Fix C3)

**Como** operador de produção,
**quero** que o sistema falhe explicitamente quando credenciais estão ausentes,
**para que** não haja fallback silencioso para tokens inválidos.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When OAuth token retrieval fails, the system SHALL raise an exception instead of falling back to a literal `"fallback_token"`.
- [ ] **[When]** When required environment variables (`AGENTCORE_MEMORY_ID`, `WHATSAPP_TOKEN`, `BEDROCK_KB_ID`) are missing, the system SHALL fail fast at startup with a list of missing variables.
- [ ] **[Ubiquitous]** The system SHALL NOT use hardcoded fallback values for any credential or token.


### Camada 2: Canais (Channel Adapters)

#### US-10: Channel adapter pattern com interface abstrata

**Como** desenvolvedor,
**quero** uma interface abstrata `ChannelAdapter` que todos os canais implementem,
**para que** novos canais (Telegram, Slack) possam ser adicionados sem alterar a orquestração.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL define an abstract `ChannelAdapter` base class with methods: `receive_message()`, `send_response()`, `verify_webhook()` (optional).
- [ ] **[When]** When a new channel is added, it SHALL only need to implement the `ChannelAdapter` interface without modifying agent or orchestration code.
- [ ] **[Ubiquitous]** The system SHALL route all incoming messages through the Supervisor Agent regardless of the source channel.

#### US-11: WhatsApp channel adapter (produção)

**Como** usuário final,
**quero** interagir com o assistente via WhatsApp,
**para que** eu possa usar o canal de mensagens mais popular.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When a GET request arrives at `/webhook` with valid `hub.verify_token`, the system SHALL return the `hub.challenge` value (webhook verification).
- [ ] **[When]** When a POST request arrives at `/webhook` with a WhatsApp message, the system SHALL extract the message text and sender phone number, invoke the Supervisor Agent, and send the response back via WhatsApp API.
- [ ] **[When]** When processing a WhatsApp message, the system SHALL send a typing indicator before invoking the agent.
- [ ] **[When]** When a duplicate message arrives (Meta retry), the system SHALL deduplicate via DynamoDB conditional put and return early.
- [ ] **[Ubiquitous]** The WhatsApp adapter SHALL be deployed as an AWS Lambda function via SAM CLI.
- [ ] **[When]** When the WhatsApp webhook receives a message, the system SHALL use the phone number as `user_id` for session management.

#### US-12: WhatsApp webhook signature validation (Fix C7)

**Como** operador de segurança,
**quero** que o webhook do WhatsApp valide a assinatura HMAC-SHA256 de cada request,
**para que** apenas mensagens legítimas da Meta sejam processadas.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When a POST request arrives at the WhatsApp webhook, the system SHALL validate the `X-Hub-Signature-256` header using HMAC-SHA256 with the app secret.
- [ ] **[When]** When signature validation fails, the system SHALL return HTTP 403 and log the attempt.
- [ ] **[Ubiquitous]** The system SHALL NOT have a `validate_webhook_signature` function that returns `True` unconditionally.

#### US-13: Chainlit channel adapter (dev/teste)

**Como** desenvolvedor,
**quero** testar o assistente localmente via interface Chainlit,
**para que** eu possa iterar rapidamente sem precisar do WhatsApp.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When a message is received via Chainlit, the system SHALL route it through the Supervisor Agent using the same pipeline do WhatsApp.
- [ ] **[When]** When the Chainlit session starts, the system SHALL display the `interface.welcome_message` from `domain.yaml`.
- [ ] **[Ubiquitous]** The Chainlit adapter SHALL NOT be deployed in produção — only available in dev/test environments.
- [ ] **[When]** When `channels.chainlit.enabled` is `false` in `domain.yaml`, the system SHALL not initialize the Chainlit adapter.


### Camada 3: Infraestrutura

#### US-14: AgentCore Runtime deploy genérico

**Como** DevOps engineer,
**quero** fazer deploy do framework no AgentCore Runtime com um Dockerfile genérico,
**para que** qualquer domínio possa ser deployado sem alterar a infraestrutura.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL provide a Dockerfile based on `linux/arm64` with Python 3.12+ and UV for dependency management.
- [ ] **[Ubiquitous]** The Dockerfile SHALL NOT contain hardcoded domain-specific environment variables (e.g., `BANQI`, `banking`).
- [ ] **[When]** When the container starts, the system SHALL expose port 8080 and respond to `/ping` with `"Healthy"`.
- [ ] **[When]** When the container receives a POST to `/invocations`, the system SHALL process the payload through the Supervisor Agent.
- [ ] **[Ubiquitous]** The `.bedrock_agentcore.yaml` SHALL be generated by `scripts/setup.py` using values from `domain.yaml`.

#### US-15: Infraestrutura agnóstica (Terraform/CFN/CDK)

**Como** DevOps engineer,
**quero** escolher entre Terraform, CloudFormation ou CDK para provisionar infraestrutura,
**para que** o framework se adapte ao tooling da minha organização.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL provide infrastructure templates in three formats: `infrastructure/terraform/`, `infrastructure/cloudformation/`, `infrastructure/cdk/`.
- [ ] **[Ubiquitous]** Each infrastructure template SHALL provision: AgentCore Runtime, WhatsApp Lambda (SAM), DynamoDB (dedup), IAM roles with least-privilege.
- [ ] **[Ubiquitous]** Infrastructure templates SHALL be parametrized — domain name, agent name, and resource names SHALL come from variables/parameters, not hardcoded.

#### US-16: IAM least-privilege policies (Fix C4)

**Como** security engineer,
**quero** que as IAM policies usem recursos específicos em vez de wildcards,
**para que** o princípio de least-privilege seja respeitado.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL NOT use `Resource: '*'` in any IAM policy for Bedrock or AgentCore actions.
- [ ] **[Ubiquitous]** IAM policies SHALL scope resources to specific ARNs using account ID, region, and resource name variables.
- [ ] **[Ubiquitous]** The system SHALL NOT grant `bedrock-agentcore:*` — only the specific actions required (e.g., `InvokeAgent`, `GetMemory`, `PutMemory`).


---

## Infraestrutura como Código (IaC)

### Contexto

O projeto suporta 3 providers de IaC para provisionar TODOS os módulos AWS BedrockAgentCore. Os templates são parametrizados e seguem o princípio de least-privilege em todas as IAM policies.

**Referência oficial**: [github.com/awslabs/agentcore-samples/04-infrastructure-as-code/](https://github.com/awslabs/agentcore-samples/tree/main/04-infrastructure-as-code/)

### Resource Types AWS::BedrockAgentCore::*

Os seguintes 15 resource types CloudFormation estão disponíveis no namespace `AWS::BedrockAgentCore::*`:

| # | Resource Type | Descrição | Uso no Projeto |
|---|---------------|-----------|----------------|
| 1 | `::Runtime` | Runtime do agente (container, env vars, network, protocol) | ✅ Core — deploy do container ARM64 |
| 2 | `::RuntimeEndpoint` | Endpoints versionados (blue-green deploys) | ✅ Versionamento de deploys |
| 3 | `::Gateway` | Gateway MCP para tools externas | ✅ Conexão com APIs bancárias |
| 4 | `::GatewayTarget` | Targets do Gateway (Lambda, MCP server, OpenAPI) | ✅ Registro de tools no Gateway |
| 5 | `::Memory` | Memory (STM + LTM) | ✅ Persistência de sessão e contexto |
| 6 | `::BrowserCustom` | Browser tool customizado | ⬜ Futuro |
| 7 | `::BrowserProfile` | Perfil de browser | ⬜ Futuro |
| 8 | `::CodeInterpreterCustom` | Code interpreter customizado | ⬜ Futuro |
| 9 | `::Policy` | Cedar authorization policy | ✅ Controle de acesso granular |
| 10 | `::PolicyEngine` | Engine de políticas Cedar | ✅ Avaliação de políticas |
| 11 | `::ApiKeyCredentialProvider` | Provedor de credenciais API Key | ✅ Autenticação de tools |
| 12 | `::OAuth2CredentialProvider` | Provedor de credenciais OAuth2 | ✅ Gateway OAuth tokens |
| 13 | `::WorkloadIdentity` | Identidade de workload | ✅ Identidade do runtime |
| 14 | `::Evaluator` | Avaliador de agentes | ⬜ Futuro — avaliação automatizada |
| 15 | `::OnlineEvaluationConfig` | Configuração de avaliação online | ⬜ Futuro — monitoramento de qualidade |

### Providers Suportados

| Provider | Diretório | Módulo/Constructs |
|----------|-----------|-------------------|
| **CloudFormation** | `infrastructure/cloudformation/` | Templates YAML nativos com `AWS::BedrockAgentCore::*` |
| **CDK (Python)** | `infrastructure/cdk/` | L2 constructs via `@aws-cdk/aws-bedrock-agentcore-alpha` |
| **Terraform** | `infrastructure/terraform/` | Resources `aws_bedrockagentcore_*` no provider AWS nativo |

### User Stories — IaC

#### US-24: Deploy via CloudFormation com recursos AgentCore completos

**Como** DevOps engineer que usa CloudFormation,
**quero** provisionar toda a infraestrutura AgentCore via template CFN,
**para que** o deploy seja reproduzível, auditável e versionado.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL provide a CloudFormation template that provisions: `AWS::BedrockAgentCore::Runtime`, `AWS::BedrockAgentCore::Memory`, `AWS::BedrockAgentCore::Gateway`, `AWS::BedrockAgentCore::GatewayTarget`, IAM roles, ECR repository, DynamoDB (dedup), and Lambda (WhatsApp webhook).
- [ ] **[When]** When `aws cloudformation validate-template` is executed, the template SHALL pass without errors.
- [ ] **[When]** When `cfn-lint` is executed, the template SHALL produce zero HIGH/CRITICAL findings.
- [ ] **[Ubiquitous]** The template SHALL use `Parameters` for all domain-specific values (`DomainSlug`, `AgentName`, `Environment`, `AWSAccountId`) — no hardcoded names.
- [ ] **[Ubiquitous]** The template SHALL include `Outputs` for: Runtime ARN, Memory ID, Gateway ARN, ECR URI, Lambda ARN.
- [ ] **[Ubiquitous]** All IAM policies in the template SHALL use scoped ARNs with `!Sub` — never `Resource: '*'`.

#### US-25: Deploy via CDK Python com L2 constructs AgentCore

**Como** DevOps engineer que usa CDK,
**quero** provisionar infraestrutura AgentCore via CDK Python com L2 constructs,
**para que** eu tenha type-safety, composabilidade e validação em tempo de synth.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL provide a CDK Python stack using `@aws-cdk/aws-bedrock-agentcore-alpha` L2 constructs for Runtime, Memory, and Gateway.
- [ ] **[When]** When `cdk synth` is executed, the stack SHALL produce a valid CloudFormation template.
- [ ] **[When]** When `cdk-nag AwsSolutionsChecks` is applied, the stack SHALL produce zero errors (suppressions require documented justification).
- [ ] **[Ubiquitous]** The stack SHALL accept `domain_slug`, `agent_name`, and `environment` as context/props — no hardcoded names.
- [ ] **[Ubiquitous]** IAM grants SHALL use `grant()` methods with specific actions — never `grant("*")`.
- [ ] **[Ubiquitous]** The stack SHALL include `CfnOutput` for: Runtime ARN, Memory ID, Gateway ARN, ECR URI.

#### US-26: Deploy via Terraform com modules AgentCore

**Como** DevOps engineer que usa Terraform,
**quero** provisionar infraestrutura AgentCore via módulos Terraform,
**para que** eu possa integrar com meu workflow de IaC existente.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL provide Terraform modules using `aws_bedrockagentcore_*` resources for Runtime, Memory, and Gateway.
- [ ] **[When]** When `terraform validate` is executed, the modules SHALL pass without errors.
- [ ] **[When]** When `tfsec` is executed, the modules SHALL produce zero HIGH/CRITICAL findings.
- [ ] **[Ubiquitous]** The modules SHALL use `variable` blocks for all domain-specific values (`domain_slug`, `agent_name`, `environment`, `aws_region`, `aws_account_id`).
- [ ] **[Ubiquitous]** All IAM policies SHALL use interpolated ARNs — never `resources = ["*"]`.
- [ ] **[Ubiquitous]** The modules SHALL include `output` blocks for: Runtime ARN, Memory ID, Gateway ARN, ECR URI.

### User Stories — Testes em 3 Níveis

#### US-27: Testes Nível 1 — Dev Local (zero custo AWS)

**Como** desenvolvedor,
**quero** executar testes completos localmente sem custo AWS,
**para que** eu possa iterar rapidamente com feedback imediato.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL provide a test suite runnable with `pytest` that achieves ≥80% code coverage without any AWS calls.
- [ ] **[Ubiquitous]** The test suite SHALL use `moto` for mocking AWS services (DynamoDB, S3, Secrets Manager).
- [ ] **[Ubiquitous]** The test suite SHALL validate all IaC templates: `cdk synth` + cdk-nag, `terraform validate`, `cfn-lint`.
- [ ] **[When]** When critical issue tests (C1–C7) are executed, they SHALL achieve ≥90% coverage of the critical paths.
- [ ] **[Ubiquitous]** The test suite SHALL include `pytest` markers: `unit`, `integration`, `critical`, `container`, `staging`.
- [ ] **[When]** When `pytest -m critical` is executed, all 7 critical issues SHALL have dedicated test cases.

#### US-28: Testes Nível 2 — Container Local (custo mínimo)

**Como** desenvolvedor,
**quero** testar o container AgentCore localmente antes de fazer deploy,
**para que** eu valide a integração real com custo mínimo.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When `bedrock-agentcore local run` is executed, the container SHALL start and respond to `/ping` with HTTP 200.
- [ ] **[When]** When `sam local invoke` is executed with a WhatsApp webhook event, the Lambda SHALL process the event correctly.
- [ ] **[When]** When the container receives a POST to `/invocations`, it SHALL process the payload through the Supervisor Agent.
- [ ] **[Ubiquitous]** The system SHALL provide a `docker-compose.yml` for orchestrating container + DynamoDB local.

#### US-29: Testes Nível 3 — Staging AWS (pré-produção)

**Como** DevOps engineer,
**quero** executar testes e2e contra um ambiente staging real,
**para que** eu valide o deploy completo antes de ir para produção.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When IaC is applied to staging, the system SHALL deploy all resources (Runtime, Memory, Gateway, Lambda, DynamoDB).
- [ ] **[When]** When e2e tests are executed against staging, they SHALL validate: health check, agent invocation, memory persistence, and WhatsApp webhook flow.
- [ ] **[When]** When staging tests complete, the system SHALL destroy all staging resources to minimize costs.
- [ ] **[Ubiquitous]** The staging environment SHALL use the same IaC templates as production (with `environment=staging` parameter).

#### US-30: Pipeline CI/CD com gates de qualidade

**Como** tech lead,
**quero** um pipeline CI/CD que execute testes em 3 níveis com gates de qualidade,
**para que** nenhum código inseguro ou quebrado chegue a produção.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The CI pipeline SHALL execute Nível 1 tests on every commit/push.
- [ ] **[Ubiquitous]** The CI pipeline SHALL execute Nível 2 tests on every pull request.
- [ ] **[When]** When code is merged to `main`, the pipeline SHALL execute Nível 3 tests against staging.
- [ ] **[Ubiquitous]** The pipeline SHALL enforce gates: ≥80% coverage, zero critical test failures, zero IAM wildcards, zero `detect-secrets` findings.
- [ ] **[Ubiquitous]** The pipeline SHALL include security scanning: `checkov`, `tfsec`, `cfn-nag`, `trivy`, `pip-audit`.

---

## Requisitos Não-Funcionais

### Segurança

#### US-17: Input validation genérica (Fix C5)

**Como** security engineer,
**quero** que todos os inputs de ferramentas sejam validados com Pydantic,
**para que** dados malformados não cheguem às APIs externas.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When a tool receives input, the system SHALL validate it against a Pydantic model before processing.
- [ ] **[When]** When a tool receives a CPF-like field, the system SHALL validate the format (11 dígitos numéricos) and reject invalid values.
- [ ] **[When]** When input validation fails, the system SHALL return a user-friendly error message in the language configured in `domain.yaml`.
- [ ] **[Ubiquitous]** The system SHALL NOT pass unvalidated user input directly to URL paths or API parameters.

#### US-18: Proteção dual de PII — Guardrails + Log Masking (Fix C6)

**Como** DPO (Data Protection Officer),
**quero** que dados pessoais sejam protegidos em duas camadas (conversa LLM + logs),
**para que** o sistema esteja em conformidade com a LGPD em qualquer domínio.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL use Bedrock Guardrails sensitive information filter to redact PII in LLM input and output (Camada 1 — conversa).
- [ ] **[Ubiquitous]** The system SHALL provide a `PIIMaskingFilter` logging filter that masks CPF, phone numbers, and email in all log output (Camada 2 — logs).
- [ ] **[Ubiquitous]** The `PIIMaskingFilter` SHALL be applied to all loggers at startup.
- [ ] **[When]** When logging user messages or API responses, the system SHALL pass content through the PII masking filter before writing to CloudWatch.
- [ ] **[Ubiquitous]** The system SHALL NOT log raw phone numbers, CPFs, or full names in any log level (DEBUG through CRITICAL).
- [ ] **[Ubiquitous]** Guardrails PII types SHALL be configurable per domain via `domain.yaml` (`guardrails` section).
- [ ] **[Ubiquitous]** The two layers SHALL be complementary: Guardrails protects the conversation, regex protects the logs.

#### US-19: Bedrock Guardrails integration

**Como** compliance officer,
**quero** que o assistente use Bedrock Guardrails para filtrar conteúdo,
**para que** respostas inadequadas sejam bloqueadas.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When `BEDROCK_GUARDRAIL_ID` is set, the system SHALL configure the Supervisor Agent's BedrockModel with guardrail parameters.
- [ ] **[When]** When `BEDROCK_GUARDRAIL_ID` is not set, the system SHALL operate normally without guardrails (optional feature).
- [ ] **[When]** When a guardrail blocks a response, the system SHALL return the `error_messages.generic` from `domain.yaml`.


#### US-31: Secrets Management (sem hardcoded secrets)

**Como** security engineer,
**quero** que todos os secrets residam no AWS Secrets Manager ou SSM Parameter Store,
**para que** não haja credenciais expostas em código, variáveis de ambiente ou logs.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL store all secrets (WhatsApp tokens, OAuth secrets, API keys) in AWS Secrets Manager with paths `${DomainSlug}/<service>/<secret-name>`.
- [ ] **[Ubiquitous]** The system SHALL store non-secret configuration (Guardrail ID, KB ID, Memory ID) in SSM Parameter Store (SecureString).
- [ ] **[Ubiquitous]** The system SHALL NOT contain hardcoded secrets, fallback values, or default tokens in any source file.
- [ ] **[When]** When a secret cannot be retrieved, the system SHALL fail-fast with a descriptive error — never fall back to a placeholder value.
- [ ] **[Ubiquitous]** Secrets SHALL have automatic rotation configured (90 days) via Secrets Manager rotation schedules.

> **Ref**: [security_requirements.md §2](./security_requirements.md#2-secrets-management)

#### US-32: Network Security (VPC, PrivateLink, WAF)

**Como** security engineer,
**quero** que o AgentCore Runtime opere em subnet privada com VPC Endpoints,
**para que** o tráfego para serviços AWS nunca saia da rede privada.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The AgentCore Runtime SHALL run in a private subnet without a public IP.
- [ ] **[Ubiquitous]** The system SHALL use VPC Endpoints (PrivateLink) for: Bedrock, Secrets Manager, DynamoDB, CloudWatch Logs, SSM.
- [ ] **[Ubiquitous]** Security Groups SHALL NOT have `0.0.0.0/0` in ingress rules.
- [ ] **[When]** When the WhatsApp webhook API Gateway is deployed, it SHALL have WAF with rate limiting (1000 req/5min per IP).
- [ ] **[Ubiquitous]** All communications SHALL use TLS 1.2+.

> **Ref**: [security_requirements.md §3](./security_requirements.md#3-network-security)

#### US-33: Container Security (hardened Dockerfile)

**Como** security engineer,
**quero** que o container de produção siga best practices de segurança,
**para que** a superfície de ataque seja minimizada.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The Dockerfile SHALL use a non-root user (`bedrock_agentcore`, UID 1000).
- [ ] **[Ubiquitous]** The container SHALL run with read-only root filesystem (`--read-only`).
- [ ] **[Ubiquitous]** The ECR repository SHALL have `ScanOnPush: true` and `ImageTagMutability: IMMUTABLE`.
- [ ] **[When]** When Trivy scans the container image, it SHALL produce zero CRITICAL/HIGH findings.
- [ ] **[Ubiquitous]** The container SHALL drop ALL Linux capabilities and run without `--privileged`.

> **Ref**: [security_requirements.md §6](./security_requirements.md#6-container-security)

#### US-34: LGPD Compliance (data protection)

**Como** DPO (Data Protection Officer),
**quero** que o sistema esteja em conformidade com a LGPD,
**para que** dados pessoais sejam protegidos conforme a legislação brasileira.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL encrypt all data at rest (DynamoDB, S3, Secrets Manager) using KMS.
- [ ] **[Ubiquitous]** The system SHALL apply PII masking (CPF, phone, email, name) in ALL log output before writing to CloudWatch.
- [ ] **[When]** When Bedrock Guardrails are configured, they SHALL include PII anonymization filters for CPF, phone, name, email, and address.
- [ ] **[Ubiquitous]** DynamoDB dedup table SHALL have TTL configured (24h) for data minimization.
- [ ] **[When]** When a user requests data deletion, the system SHALL provide a mechanism to delete user data from AgentCore Memory.

> **Ref**: [security_requirements.md §4](./security_requirements.md#4-data-protection--lgpd)

#### US-35: IaC Security Scanning

**Como** security engineer,
**quero** que todos os templates IaC sejam validados por ferramentas de segurança,
**para que** vulnerabilidades de infraestrutura sejam detectadas antes do deploy.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The CI pipeline SHALL run `checkov` on all IaC templates (Terraform, CFN, CDK output).
- [ ] **[Ubiquitous]** The CI pipeline SHALL run `tfsec` on Terraform modules.
- [ ] **[Ubiquitous]** The CI pipeline SHALL run `cfn-nag` on CloudFormation templates.
- [ ] **[Ubiquitous]** CDK stacks SHALL have `cdk-nag AwsSolutionsChecks` applied — suppressions require documented justification.
- [ ] **[Ubiquitous]** The CI pipeline SHALL run `detect-secrets` to prevent accidental secret commits.
- [ ] **[Ubiquitous]** The CI pipeline SHALL run `pip-audit` weekly for Python dependency vulnerabilities.
- [ ] **[When]** When any security scanner finds HIGH/CRITICAL issues, the CI build SHALL fail.

> **Ref**: [security_requirements.md §8](./security_requirements.md#8-iac-security)

### Performance

#### US-20: Latência e throughput

**Como** product owner,
**quero** que o assistente responda em tempo aceitável para conversação,
**para que** a experiência do usuário seja fluida.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL respond to user messages within 10 seconds end-to-end (WhatsApp receive → WhatsApp send), with a target of < 5 seconds for simple queries.
- [ ] **[Ubiquitous]** The system SHALL support at least 10 concurrent user sessions without degradation.
- [ ] **[Ubiquitous]** The system SHALL use Bedrock prompt caching (`SystemContentBlock` + `cachePoint`) to reduce latency and cost on repeated system prompts.

### Observabilidade

#### US-21: Structured logging e tracing

**Como** SRE,
**quero** observabilidade completa com logs estruturados e traces distribuídos,
**para que** eu possa diagnosticar problemas em produção.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL emit structured JSON logs with fields: `timestamp`, `level`, `agent_name`, `session_id`, `request_id`, `duration_ms`.
- [ ] **[Ubiquitous]** The system SHALL integrate with AgentCore Observability for distributed tracing across Supervisor and sub-agents.
- [ ] **[When]** When an error occurs, the system SHALL log the error with full stack trace, agent context, and correlation ID.
- [ ] **[When]** When a tool is invoked, the system SHALL log tool name, input (PII-masked), duration, and success/failure status.

#### US-22: Health checks

**Como** operador de produção,
**quero** health checks que verifiquem a saúde real do sistema,
**para que** o load balancer possa rotear tráfego corretamente.

**Acceptance Criteria (EARS):**

- [ ] **[When]** When `/ping` is called, the system SHALL return HTTP 200 with `"Healthy"` if the application is ready to process requests.
- [ ] **[When]** When the Bedrock model is unreachable, the health check SHALL still return 200 (the agent will handle errors per-request).

### Extensibilidade

#### US-23: Extensibilidade para novos canais

**Como** arquiteto,
**quero** que o framework suporte novos canais sem alterar a orquestração,
**para que** equipes possam adicionar Telegram, Slack, Teams ou Google Chat no futuro.

**Acceptance Criteria (EARS):**

- [ ] **[Ubiquitous]** The system SHALL define a `ChannelAdapter` protocol/ABC with a stable interface that new channels implement.
- [ ] **[When]** When a new channel type is added to `domain.yaml` under `channels`, the system SHALL load the corresponding adapter if it exists.
- [ ] **[Ubiquitous]** The orchestration layer (agents, memory, tools) SHALL have zero dependencies on any specific channel implementation.


---

## Rastreabilidade: Critical Issues → User Stories

| Issue | Descrição | User Story | Severidade |
|-------|-----------|------------|------------|
| C1 | Race condition no `_supervisor_context` (dict global mutável) | US-06 | 🔴 Critical |
| C2 | MCP Client nunca fechado (resource leak) | US-07 | 🔴 Critical |
| C3 | Fallback silencioso para `"fallback_token"` | US-09, US-31 | 🔴 Critical |
| C4 | IAM Policy com `Resource: '*'` | US-16, US-24, US-25, US-26, US-35 | 🔴 Critical |
| C5 | Zero validação de CPF nas tools | US-17 | 🔴 Critical |
| C6 | PII logado em texto claro | US-18, US-34 | 🔴 Critical |
| C7 | Webhook signature validation retorna `True` sempre | US-12 | 🔴 Critical |

---

## Rastreabilidade: Novas User Stories → Documentos de Referência

| US | Descrição | Documento de Referência |
|----|-----------|------------------------|
| US-24 | Deploy via CloudFormation | [security_requirements.md §1, §8](./security_requirements.md) |
| US-25 | Deploy via CDK Python | [security_requirements.md §1, §8](./security_requirements.md) |
| US-26 | Deploy via Terraform | [security_requirements.md §1, §8](./security_requirements.md) |
| US-27 | Testes Nível 1 — Dev Local | [testing_strategy.md §1.1, §3](./testing_strategy.md) |
| US-28 | Testes Nível 2 — Container Local | [testing_strategy.md §1.2](./testing_strategy.md) |
| US-29 | Testes Nível 3 — Staging AWS | [testing_strategy.md §1.3](./testing_strategy.md) |
| US-30 | Pipeline CI/CD | [testing_strategy.md §5](./testing_strategy.md) |
| US-31 | Secrets Management | [security_requirements.md §2](./security_requirements.md) |
| US-32 | Network Security | [security_requirements.md §3](./security_requirements.md) |
| US-33 | Container Security | [security_requirements.md §6](./security_requirements.md) |
| US-34 | LGPD Compliance | [security_requirements.md §4](./security_requirements.md) |
| US-35 | IaC Security Scanning | [security_requirements.md §8](./security_requirements.md) |

---

## Restrições Técnicas e Dependências

### Restrições

1. **Python 3.12+** — versão mínima exigida pelo Strands Agent Framework
2. **ARM64** — AgentCore Runtime requer containers ARM64 (`linux/arm64`)
3. **Porta 8080** — AgentCore Runtime espera a aplicação na porta 8080
4. **UV** — gerenciador de dependências obrigatório (substituindo pip/poetry)
5. **Bedrock region** — modelos Claude Sonnet 4 disponíveis em `us-east-1` (US inference profiles)
6. **SAM CLI** — WhatsApp Lambda requer SAM CLI para deploy
7. **Pydantic v2** — validação de configuração e input (não v1)

### Dependências Externas

| Dependência | Versão | Propósito |
|-------------|--------|-----------|
| `strands-agents` | latest | Framework de agentes |
| `strands-agents-tools` | latest | Tools built-in (retrieve, agent_core_memory) |
| `bedrock-agentcore-runtime` | latest | AgentCore Runtime SDK |
| `bedrock-agentcore-memory` | latest | AgentCore Memory SDK |
| `pydantic` | >=2.0 | Validação de config e input |
| `pydantic-settings` | >=2.0 | Settings com env vars |
| `pyyaml` | >=6.0 | Parsing do domain.yaml |
| `chainlit` | latest | Interface dev/teste (opcional) |
| `boto3` | latest | AWS SDK |
| `opentelemetry-*` | latest | Observabilidade |

### Dependências AWS

| Serviço | Propósito |
|---------|-----------|
| Amazon Bedrock | Foundation Models (Claude Sonnet 4) |
| Bedrock Knowledge Base | RAG para General Agent |
| AgentCore Runtime | Deploy e execução dos agentes |
| AgentCore Memory | STM + LTM (preferences, facts, summaries) |
| AgentCore Gateway | MCP para tools externas |
| AgentCore Observability | Tracing distribuído |
| Bedrock Guardrails | Content filtering (opcional) |
| Lambda + API Gateway | WhatsApp webhook |
| DynamoDB | Deduplicação de mensagens WhatsApp |
| S3 | Vector database para Knowledge Base |
| CloudWatch | Logs e métricas |
| IAM | Roles e policies |

---

## Out of Scope (NÃO será implementado agora)

1. **Canais além de WhatsApp e Chainlit** — Telegram, Slack, Teams e Google Chat são extensões futuras; apenas a interface abstrata `ChannelAdapter` será criada
2. **Cache Redis para Knowledge Base** — otimização de performance para fase posterior
3. **Circuit breaker para APIs externas** — resiliência avançada para fase posterior
4. **Rate limiting por usuário** — proteção contra abuso para fase posterior
5. **Dashboard CloudWatch personalizado** — monitoramento avançado para fase posterior
6. **Métricas de negócio** (conversões, satisfação) — analytics para fase posterior
7. **Suporte a mídia no WhatsApp** (imagens, áudio, documentos) — apenas texto na v1
8. **Multi-tenancy** — um deploy por domínio; não há isolamento multi-tenant no mesmo deploy
9. **Wizard interativo de setup** (`scripts/setup.py`) — será um script simples, não interativo
10. **Exemplos de domínios** (healthcare, retail) — apenas a estrutura genérica; o domínio banking serve como exemplo de referência
11. **Testes de carga automatizados** — testes unitários e integração sim; load testing é manual
12. **Graceful shutdown** — otimização de produção para fase posterior
13. **Internacionalização (i18n)** — o `language_default` no YAML é informativo para os prompts; não há framework de tradução

---

## Faseamento de Entrega

### Fase 1: Core Framework (MVP)
- US-01, US-02, US-03, US-04 (Domain config)
- US-05, US-06, US-07, US-08, US-09 (Orquestração + fixes C1/C2/C3)
- US-17, US-18 (Segurança: fixes C5/C6)
- US-21, US-22 (Observabilidade básica)
- US-27 (Testes Nível 1 — unit tests + fixtures)

### Fase 2: Canais
- US-10 (Channel adapter pattern)
- US-11, US-12 (WhatsApp + fix C7)
- US-13 (Chainlit)
- US-27 (Testes Nível 1 — testes de canais)

### Fase 3: Infraestrutura + IaC Completa
- US-14 (AgentCore Runtime)
- US-15 (Terraform/CFN/CDK — base)
- US-16 (IAM least-privilege, fix C4)
- US-24 (CloudFormation com recursos AgentCore completos)
- US-25 (CDK Python com L2 constructs)
- US-26 (Terraform com modules AgentCore)
- US-27 (Testes Nível 1 — IaC validation)

### Fase 4: Segurança + Testes + CI/CD
- US-19 (Guardrails)
- US-20 (Performance tuning)
- US-23 (Extensibilidade validada)
- US-28 (Testes Nível 2 — container local)
- US-29 (Testes Nível 3 — staging AWS)
- US-30 (Pipeline CI/CD com gates)
- US-31 (Secrets Management)
- US-32 (Network Security)
- US-33 (Container Security)
- US-34 (LGPD Compliance)
- US-35 (IaC Security Scanning)
