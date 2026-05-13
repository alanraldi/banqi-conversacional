# banQi Conversacional — Empréstimo Consignado via WhatsApp

Agente de IA conversacional que guia o cliente banQi pelo fluxo completo de **simulação e contratação de empréstimo consignado via WhatsApp** — do primeiro "Oi" até o depósito na conta, sem intervenção humana.

---

## Como funciona

```
Cliente manda "Oi" no WhatsApp
        ↓
Agente coleta CPF e nome
        ↓
Gera e envia o Termo de Consentimento (PDF)
        ↓
Cliente aceita → sistema verifica elegibilidade e simula automaticamente
        ↓
Cliente escolhe os valores (ou ajusta)
        ↓
Agente coleta e-mail, endereço e dados bancários
        ↓
Cliente faz biometria facial (selfie via link)
        ↓
Cliente confirma o contrato
        ↓
Agente acompanha e notifica: Assinado → CCB → Formalizado → Depositado
```

---

## Arquitetura

### Produção (AWS)

```
WhatsApp → API Gateway + WAF → Lambda Handler
                                      ↓
                           AWS Bedrock AgentCore Runtime
                                      ↓
                            SUPERVISOR AGENT (Claude Sonnet 4.6)
                           ┌──────────┴──────────┐
               CONSIGNADO AGENT             GENERAL AGENT
               (Claude Haiku 4.5)          (Claude Haiku 4.5)
                       ↓
            APIs banQi via AgentCore Gateway (MCP)
```

### Desenvolvimento Local (sem ambiente AWS)

```
simulate_flow.py / curl
        ↓
src/local_server.py :8080   ←  substitui Lambda + API Gateway
        ↓
src/main.py (Strands Agents) ←  substitui AgentCore Runtime
        ↓
mock_api/server.py :8000    ←  substitui APIs reais banQi
        ↓
DynamoDB Local :8001         ←  substitui DynamoDB AWS

        ↕ AWS Bedrock (única chamada externa — precisa de credenciais AWS)
```

**Stack principal:** Python 3.12 · Strands Agents SDK · AWS Bedrock · FastAPI · Docker

---

## Estrutura do Repositório

```
banqi-conversacional/
├── README.md                     ← este arquivo
├── Dockerfile                    ← imagem ARM64 para AgentCore Runtime (produção)
├── docker-compose.yml            ← ambiente local completo (mock + dynamo + agente)
├── pyproject.toml                ← dependências Python e ferramentas
├── .env.example                  ← variáveis de ambiente (copiar para .env)
│
├── infrastructure/               ← E1: Infraestrutura AWS (Terraform)
│   └── terraform/
│       ├── main.tf               ← orquestra os 7 módulos
│       ├── variables.tf          ← todas as variáveis de entrada
│       ├── outputs.tf            ← outputs exportados
│       ├── providers.tf          ← provider AWS + backend S3
│       ├── terraform.tfvars.example
│       └── modules/
│           ├── network/          ← VPC, subnets, 7 VPC Endpoints, WAF
│           ├── iam/              ← roles para Runtime, Lambda e Gateway
│           ├── runtime/          ← AgentCore Runtime (container ARM64)
│           ├── memory/           ← AgentCore Memory (STM + LTM)
│           ├── gateway/          ← AgentCore Gateway MCP (8 targets banQi)
│           ├── guardrails/       ← Bedrock Guardrails (prompt injection / jailbreak)
│           └── whatsapp/         ← Lambda + API GW + DynamoDB dedup + WAF
│
├── domains/                      ← E2: Configuração de domínio
│   └── consignado/
│       ├── domain.yaml           ← config: agentes, modelos, memória, mensagens
│       └── prompts/
│           ├── supervisor.md     ← prompt do Supervisor (routing + delegação)
│           ├── consignado.md     ← prompt do Consignado Agent (etapas 1-7)
│           └── general.md        ← prompt do General Agent (fora do escopo)
│
├── src/                          ← E2/E3/E4: Código Python da aplicação
│   ├── main.py                   ← entrypoint do AgentCore Runtime
│   ├── local_server.py           ← servidor FastAPI para testes locais
│   ├── agents/
│   │   ├── factory.py            ← cria Supervisor + sub-agentes (Agents-as-Tools)
│   │   └── context.py            ← SessionContext thread-local
│   ├── tools/                    ← E3: 8 tools MCP (chamadas às APIs banQi)
│   │   ├── consent_term.py       ← etapas 1-2: criar e aceitar termo
│   │   ├── simulation.py         ← etapa 3: criar simulação e buscar fallback
│   │   ├── proposal.py           ← etapas 4 e 6: criar proposta e aceite formal
│   │   └── biometry.py           ← etapa 5: iniciar e continuar biometria
│   ├── webhook/                  ← E4: Handler de webhooks
│   │   ├── handler.py            ← Lambda entrypoint (WhatsApp + banQi)
│   │   ├── router.py             ← roteador de eventos banQi → handler
│   │   ├── events.py             ← handlers para cada tipo de evento
│   │   ├── session.py            ← correlação de sessão por telefone
│   │   ├── models.py             ← modelos Pydantic dos payloads
│   │   ├── signature.py          ← validação HMAC-SHA256 timing-safe
│   │   ├── whatsapp_client.py    ← cliente HTTP WhatsApp Business API
│   │   └── agentcore_client.py   ← invoke AgentCore + save memory
│   ├── config/
│   │   └── settings.py           ← Settings (pydantic-settings, dual env/Secrets Manager)
│   └── utils/
│       ├── pii.py                ← PII masking nos logs (LGPD)
│       ├── validation.py         ← validadores de CPF, e-mail, CEP etc.
│       ├── logging.py            ← configuração de logging estruturado
│       └── secrets.py            ← carregamento de secrets (dev: env / prod: Secrets Manager)
│
├── mock_api/                     ← Servidor mock das APIs banQi
│   ├── server.py                 ← FastAPI com 8 endpoints + 6 webhooks simulados
│   ├── test_flow.py              ← 40 testes automatizados (4 cenários)
│   ├── Dockerfile                ← containeriza o mock para docker-compose
│   └── requirements.txt          ← fastapi, uvicorn, httpx
│
├── scripts/
│   └── simulate_flow.py          ← simula fluxo completo etapas 1-7 sem WhatsApp
│
├── api/                          ← contratos OpenAPI das APIs banQi
├── specs/                        ← especificações técnicas e fluxo conversacional
├── cod_poc/                      ← código de referência da PoC (CI&T)
├── fluxo_trabalho/               ← PDFs com diagramas das 7 etapas
└── arquitetura/                  ← diagramas arquiteturais
```

---

## Pré-requisitos

| Ferramenta | Versão | Para quê |
|---|---|---|
| Python | 3.12+ | Executar o agente e os testes |
| Docker + Docker Compose | 24+ | Ambiente local completo |
| AWS CLI | 2+ | Credenciais para o Bedrock |
| Terraform | 1.7+ | Provisionamento AWS (produção) |
| uv | qualquer | Gerenciador de pacotes Python |

> **Conta AWS com acesso ao Bedrock é o único requisito de nuvem para desenvolvimento local.**
> Todos os demais serviços rodam via Docker.

---

## Configuração Local (Passo a Passo)

### 1. Clonar e instalar dependências

```powershell
git clone https://github.com/alanraldi/banqi-conversacional.git
cd banqi-conversacional

# Instalar dependências (incluindo dev)
uv pip install -e ".[dev]"
```

### 2. Configurar variáveis de ambiente

```powershell
copy .env.example .env
```

Editar o `.env` com os valores mínimos para rodar localmente:

```env
# Obrigatório — perfil AWS com acesso ao Bedrock
APP_ENV=dev
AWS_REGION=us-east-1
AWS_PROFILE=seu-perfil-aws

# Modelos Claude (valores padrão já funcionam)
SUPERVISOR_AGENT_MODEL_ID=us.anthropic.claude-sonnet-4-6-20250514-v1:0
CONSIGNADO_AGENT_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
GENERAL_AGENT_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0

# Mock local (docker-compose define automaticamente)
BANQI_API_BASE_URL=http://localhost:8000
DEDUP_TABLE_NAME=banqi-dedup
SESSION_TABLE_NAME=banqi-sessions
```

> Os demais campos (AgentCore, Gateway, WhatsApp) ficam vazios em dev.
> O agente entra em **modo degradado** e funciona sem memória persistente.

### 3. Verificar credenciais AWS

```powershell
aws sts get-caller-identity --profile seu-perfil-aws
```

Confirmar que o perfil tem acesso ao Bedrock:

```powershell
aws bedrock list-foundation-models --region us-east-1 --profile seu-perfil-aws
```

---

## Como Testar Localmente

Há três formas de testar, da mais simples para a mais completa:

---

### Opção A — Só o Mock (sem agente, sem AWS)

Testa as APIs banQi simuladas de forma isolada. Não precisa de credenciais AWS.

```powershell
# Instalar dependências do mock
pip install -r mock_api/requirements.txt

# Iniciar o servidor mock
python -m uvicorn mock_api.server:app --port 8000 --reload
```

Documentação interativa: **http://localhost:8000/docs**

```powershell
# Rodar os 40 testes automatizados
python -X utf8 mock_api/test_flow.py
```

**Cenários cobertos:**

| Cenário | Testes |
|---|---|
| Fluxo completo (etapas 1-7, do termo ao DISBURSED) | 30 |
| Cliente sem elegibilidade (ELIGIBILITY_REJECTED) | 4 |
| Biometria reprovada (DENIED) | 3 |
| Erros síncronos (409, 412) | 3 |
| **Total** | **40** |

**Padrões especiais para simular erros:**

| Como provocar | Comportamento simulado |
|---|---|
| CPF começando com `000` | Sem elegibilidade (ELIGIBILITY_REJECTED) |
| CPF começando com `999` | Erro na geração do PDF (PDF_GENERATION_ERROR) |
| `idBiometric: "denied-*"` | Biometria reprovada (DENIED) |
| Chamar `/consent-term/accept` duas vezes | Erro 409 (já aceito) |
| `idSimulation` inexistente na proposta | Erro 412 (simulação inválida) |

---

### Opção B — Ambiente completo via Docker Compose

Sobe mock + DynamoDB Local + agente. Testa o sistema inteiro com Claude real.

```powershell
# Subir todo o ambiente local
docker-compose up

# Aguardar todos os serviços ficarem healthy (30-60 segundos)
# mock-api:   http://localhost:8000/docs
# dynamodb:   http://localhost:8001/shell
# agent:      http://localhost:8080/ping
```

**Serviços iniciados:**

| Serviço | Porta | O que faz |
|---|---|---|
| `mock-api` | 8000 | Simula todas as APIs banQi + webhooks |
| `dynamodb` | 8001 | DynamoDB Local (dedup + sessões) |
| `dynamodb-setup` | — | Cria as tabelas automaticamente (roda e sai) |
| `agent` | 8080 | Agente local com Claude real via Bedrock |

```powershell
# Testar se o agente está respondendo
curl http://localhost:8080/ping
# Resposta esperada: {"status": "ok", "env": "dev"}
```

---

### Opção C — Simulação do fluxo completo

Simula uma conversa real de ponta a ponta (etapas 1-7) sem precisar de WhatsApp.

```powershell
# Com o docker-compose rodando em outro terminal:
python scripts/simulate_flow.py
```

O script executa automaticamente:
1. Cliente manda "Oi" e inicia a conversa
2. Envia CPF e nome
3. Dispara webhook `CONSENT_TERM_FILE_READY`
4. Cliente aceita o termo
5. Dispara webhook `SIMULATION_READY` com oferta
6. Cliente aceita a simulação e envia e-mail
7. Dispara webhook `PROPOSAL_CREATED`
8. Dispara webhooks de status: `SIGNED` → `CCB_GENERATED` → `DISBURSED`

**Você verá os logs do agente no terminal do docker-compose.**

---

### Opção D — Testes unitários

Testa validações, PII masking, roteamento e handlers sem AWS.

```powershell
# Rodar todos os testes unitários
pytest tests/ -v

# Só testes de uma pasta específica
pytest tests/unit/ -v

# Com cobertura
pytest tests/ --cov=src --cov-report=term-missing
```

---

## Testar Endpoints Manualmente

Com o `docker-compose up` rodando, use os exemplos abaixo:

### Simular mensagem WhatsApp recebida

```powershell
curl -X POST http://localhost:8080/whatsapp `
  -H "Content-Type: application/json" `
  -H "X-Hub-Signature-256: sha256=fake" `
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "123",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "messages": [{
            "id": "msg_001",
            "from": "+5511999990001",
            "type": "text",
            "text": {"body": "Oi, quero simular um emprestimo consignado"},
            "timestamp": "1234567890"
          }]
        },
        "field": "messages"
      }]
    }]
  }'
```

### Simular webhook banQi recebido

```powershell
curl -X POST http://localhost:8080/webhook/banqi `
  -H "Content-Type: application/json" `
  -d '{
    "event": "SIMULATION_READY",
    "phone": "+5511999990001",
    "data": {
      "simulations": [{
        "amount": 5000.00,
        "numInstallments": 24,
        "installmentAmount": 245.50,
        "monthlyRate": 1.89,
        "disbursementDate": "2026-05-20"
      }]
    }
  }'
```

### Verificar webhooks recebidos pelo mock

```powershell
curl http://localhost:8000/test/webhooks/+5511999990001
```

### Resetar estado do usuário no mock

```powershell
curl -X DELETE http://localhost:8000/test/state/+5511999990001
```

---

## Mapeamento: AWS (Produção) vs Local (Desenvolvimento)

| Componente AWS | Substituto Local | Observação |
|---|---|---|
| AgentCore Runtime | `src/main.py` direto | Strands Agents roda local |
| AgentCore Memory | Desabilitado (modo degradado) | Sem persistência entre sessões |
| AgentCore Gateway (MCP) | Mock API `:8000` | `BANQI_API_BASE_URL=localhost:8000` |
| Lambda Handler | `src/local_server.py` `:8080` | FastAPI simula o Lambda |
| DynamoDB (dedup + sessão) | DynamoDB Local `:8001` | Imagem oficial AWS |
| API Gateway + WAF | FastAPI direto | Sem rate limiting local |
| Secrets Manager | Arquivo `.env` | `APP_ENV=dev` |
| WhatsApp Business API | `curl` / `simulate_flow.py` | Mensagens simuladas |
| Bedrock (Claude) | **AWS real** | Único serviço de nuvem obrigatório |

---

## As 7 Etapas do Fluxo

| Etapa | O que acontece | API chamada | Webhook recebido |
|---|---|---|---|
| 1 | Agente gera o Termo de Consentimento | `POST /consent-term` | `CONSENT_TERM_FILE_READY` |
| 2 | Cliente aceita → simulação automática | `POST /consent-term/accept` | `SIMULATION_READY` |
| 3 | Cliente ajusta valor (opcional) | `POST /simulations` | `SIMULATION_COMPLETED` |
| 4 | Agente coleta dados e cria proposta | `POST /proposals` | `PROPOSAL_CREATED` |
| 5 | Cliente faz biometria facial (Único) | `POST /biometry` + `/continue` | — |
| 6 | Cliente confirma o contrato | `POST /proposals/{id}/accept` | — |
| 7 | Agente notifica cada status | — | `PROPOSAL_STATUS_UPDATE` |

---

## Deploy em Produção (quando ambiente banQi estiver disponível)

### 1. Infraestrutura AWS (Terraform)

```powershell
cd infrastructure/terraform

# Copiar e preencher variáveis
copy terraform.tfvars.example terraform.tfvars

# Inicializar com backend S3
terraform init -backend-config=backend.tfvars

# Revisar o que será criado
terraform plan -var-file=terraform.tfvars

# Aplicar (cria VPC, AgentCore, Lambda, DynamoDB, etc.)
terraform apply -var-file=terraform.tfvars
```

### 2. Build e push do container

```powershell
# Build ARM64 para AgentCore (Graviton)
docker buildx build --platform linux/arm64 -t banqi-conversacional:latest .

# Tag e push para ECR (ARN do ECR gerado pelo Terraform)
docker tag banqi-conversacional:latest <ecr-uri>:latest
docker push <ecr-uri>:latest
```

### 3. Apontar o agente para as APIs reais

Atualizar `.env` ou variáveis de ambiente do AgentCore Runtime:

```env
APP_ENV=prod
BANQI_API_BASE_URL=https://api.banqi.com.br
AGENTCORE_MEMORY_ID=<id gerado pelo terraform>
AGENTCORE_GATEWAY_ENDPOINT=<url gerada pelo terraform>
```

---

## Backlog — Épicos e Histórias

### E1 — Infraestrutura e Setup AWS
*Critério de aceite: Lambda recebe webhook do WhatsApp sem erro. AgentCore status ACTIVE.*

| História | O que entrega | Tasks |
|---|---|---|
| H-01 Conta AWS e Networking | VPC privada, subnets em 2 AZs, 7 VPC Endpoints PrivateLink, Security Groups | T-01 a T-04 |
| H-02 Repositório de Container | ECR com scan automático, Dockerfile ARM64, build via CodeBuild | T-05 a T-07 |
| H-03 AgentCore Runtime | Runtime provisionado via Terraform, variáveis de ambiente, health check `/ping` | T-08 a T-10 |
| H-04 AgentCore Memory | Memory store criado, namespace `users/{phone}/consignado`, estratégias LTM | T-11 a T-13 |
| H-05 AgentCore Gateway | Cognito OAuth, 8 targets MCP apontando para APIs banQi | T-14 a T-16 |
| H-06 Lambda WhatsApp | Lambda + API Gateway + DynamoDB dedup (TTL 120s) + WAF (1.000 req/5min) | T-17 a T-20 |
| H-07 Bedrock Guardrails | Prompt attack detection HIGH, topic policy DENY fora do escopo | T-21 a T-22 |
| H-08 Secrets Manager | Secret JSON com credenciais WhatsApp, carregamento dual env/Secrets Manager | T-23 a T-24 |

### E2 — Estrutura dos Agentes
*Critério de aceite: Conversa básica funciona localmente. Routing correto em 10 mensagens de teste.*

| História | O que entrega | Tasks |
|---|---|---|
| H-09 domain.yaml | Config do domínio: agent_name, model IDs, prompts e namespaces de memória | T-25 a T-26 |
| H-10 Supervisor Agent | Routing por intenção, recuperação LTM, injeção de contexto, retomada por `current_step` | T-27 a T-30 |
| H-11 Consignado Agent | Controle de etapas (1-7), coleta progressiva, validações, mascaramento PII | T-31 a T-34 |
| H-12 General Agent | Mensagem padrão de fora do escopo, log de intenção | T-35 |
| H-13 Prompts | `supervisor.md`, `consignado.md`, `general.md` | T-36 a T-37 |
| H-14 Memória e Persistência | STM sliding window, LTM tools `memory_read/write` | T-38 a T-40 |

### E3 — Integração com APIs banQi (Tools MCP)
*Critério de aceite: Cada tool retorna resposta esperada contra sandbox banQi.*

| História | O que entrega | Tasks |
|---|---|---|
| H-15 create_consent_term | POST /consent-term, trata 406/409, aguarda `CONSENT_TERM_FILE_READY` | T-41 a T-44 |
| H-16 accept_consent_term | POST /consent-term/accept, roteia `SIMULATION_READY` ou `NO_OFFER_AVAILABLE` | T-45 a T-47 |
| H-17 create_simulation | POST /simulations, cache hit vs miss, trata TOKEN_EXPIRED | T-48 a T-51 |
| H-18 get_simulations | GET /simulations como fallback quando webhook é perdido | T-52 |
| H-19 create_proposal | POST /proposals, monta payload completo, aguarda `PROPOSAL_CREATED` | T-53 a T-56 |
| H-20 start_biometry | POST /biometry, formata e envia BioLink ao cliente | T-57 a T-58 |
| H-21 continue_biometry | POST /biometry/continue, trata APPROVED/BIOMETRICS/DENIED | T-59 a T-61 |
| H-22 accept_proposal | POST /accept com headers `x-remote-address` e `user-agent` | T-62 a T-63 |

### E4 — Handler de Webhooks
*Critério de aceite: Todos os 6 tipos de evento processados corretamente.*

| História | O que entrega | Tasks |
|---|---|---|
| H-23 Roteamento de Eventos | Switch por tipo: 6 handlers de eventos banQi | T-64 a T-70 |
| H-24 Correlação de Sessão | Lookup de sessão por `phone`, log de eventos órfãos | T-71 a T-72 |
| H-25 Sessão Expirada | HTTP 200 para webhooks sem sessão (evita retry) | T-73 a T-74 |
| H-26 Retry e DLQ | SQS DLQ, 3 tentativas com backoff, alarme CloudWatch | T-75 a T-77 |

### E5 — Qualidade e Produção
*Critério de aceite: P95 < 5s. Zero PII em logs. Pipeline CI/CD automático.*

| História | O que entrega | Tasks |
|---|---|---|
| H-27 Testes Unitários | CPF, campos, PII masking, routing, retomada por current_step | T-78 a T-82 |
| H-28 Testes de Integração | 8 tools contra sandbox, pipeline de webhook E2E | T-83 a T-85 |
| H-29 Testes End-to-End | 7 cenários: fluxo completo, retomada, erros, WhatsApp real | T-86 a T-92 |
| H-30 CI/CD | GitHub Actions (pytest + ruff + Trivy), deploy staging automático | T-93 a T-95 |
| H-31 Monitoramento | Dashboard CloudWatch (latência P95, erros, conversão), alarmes SNS | T-96 a T-97 |
| H-32 Carga e Segurança | 1.000 conversas simultâneas (Locust), prompt injection, auditoria PII | T-98 a T-102 |
| H-33 Documentação | Runbook operacional, script LGPD `delete_user_data.py`, handover | T-103 a T-105 |

---

## Roadmap

| Épico | Tasks | Prazo |
|---|---|---|
| E1 — Infraestrutura AWS | T-01 a T-24 | 1 semana |
| E2 — Agentes | T-25 a T-40 | 1 semana |
| E3 — Tools / APIs banQi | T-41 a T-63 | 2 semanas |
| E4 — Webhooks | T-64 a T-77 | 1 semana |
| E5 — Qualidade e Produção | T-78 a T-105 | 2 semanas |
| **Total** | **105 tasks** | **~8 semanas** |

---

## Status Atual

| Entregável | Status |
|---|---|
| Especificação da arquitetura (`specs/spec.md`) | Concluído |
| Fluxo conversacional turno a turno (`specs/pipeline/po-brief.md`) | Concluído |
| Mock API — 40/40 testes passando (`mock_api/`) | Concluído |
| Infraestrutura AWS — E1 (`infrastructure/terraform/`) | Código pronto, aguardando ambiente |
| Implementação dos agentes — E2 (`domains/` + `src/agents/`) | Código pronto |
| Integração com APIs banQi — E3 (`src/tools/`) | Código pronto, aguardando sandbox |
| Handler de webhooks — E4 (`src/webhook/`) | Código pronto |
| Ambiente local completo (`docker-compose.yml`) | Concluído |
| Testes E2E e go-live — E5 | Aguardando ambiente banQi |

---

## Referências

| Arquivo | Conteúdo |
|---|---|
| `specs/banQi_conversacional/spec.md` | Arquitetura técnica completa dos agentes e tools |
| `specs/banQi_conversacional/pipeline/po-brief.md` | Fluxo conversacional turno a turno |
| `api/openapi-wpp-etapas-1-2-3-4.yaml` | Contratos das APIs (etapas 1-4) |
| `api/openapi-wpp-etapas-5-6-7.yaml` | Contratos das APIs (etapas 5-7) |
| `fluxo_trabalho/*.pdf` | Diagramas de sequência fornecidos pela banQi |
| `cod_poc/` | Código da PoC de referência (CI&T) |

---

*Desenvolvido por CI&T para banQi · Python · Strands Agents SDK · AWS Bedrock AgentCore*
