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
Agente acompanha e notifica: Assinado → CCB → Formalizado → Depositado 🎉
```

---

## Arquitetura

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

**Stack principal:** Python · Strands Agents SDK · AWS Bedrock AgentCore · FastAPI (mock)

---

## Estrutura do Repositório

```
banqi-conversacional/
├── README.md               ← este arquivo
├── projeto.md              ← documentação completa do projeto
│
├── api/                    ← contratos das APIs banQi
├── specs/                  ← especificações técnicas e fluxo conversacional
├── mock_api/               ← servidor mock para desenvolvimento e testes
└── fluxo_trabalho/         ← PDFs com os diagramas de fluxo das etapas
```

---

## Pastas em Detalhe

### `projeto.md`

Documento central do projeto na visão de PO. Contém:

- Visão do produto, escopo do MVP e público-alvo
- Arquitetura completa com diagramas
- Fluxo conversacional das 7 etapas
- **5 épicos e 22 histórias de usuário** com critérios de aceite
- Especificações técnicas (payloads, validações, tratamento de erros)
- Guia de provisionamento de serviços AWS (Terraform, 8 módulos, 36 recursos)
- Estratégia do mock e de desenvolvimento
- Segurança e conformidade LGPD
- Estimativa e roadmap (~8 semanas)

---

### `api/`

Contratos OpenAPI (YAML) das APIs banQi que o agente consome.

| Arquivo | Conteúdo |
|---|---|
| `openapi-wpp-etapas-1-2-3-4.yaml` | Termo de consentimento, aceite, simulação e proposta |
| `openapi-wpp-etapas-5-6-7.yaml` | Biometria, aceite formal e acompanhamento de status |

Use esses arquivos para entender os payloads, códigos de retorno e webhooks de cada etapa antes de implementar as tools do agente.

---

### `specs/`

Especificações técnicas do projeto organizadas em subpastas.

```
specs/banQi_conversacional/
├── spec.md          ← arquitetura dos agentes, tools e webhooks
├── tasks.md         ← 41 tasks em 5 fases de desenvolvimento
└── pipeline/
    └── po-brief.md  ← fluxo conversacional turno a turno (cliente × agente × API)
```

**`spec.md`** — Referência técnica completa:
- Hierarquia de agentes (Supervisor → Consignado Agent → General Agent)
- Regra de delegação com contexto completo (sub-agentes são stateless)
- Namespace de memória LTM com os 13 campos persistidos entre sessões
- Assinatura das 8 tools MCP que chamam as APIs banQi
- Tabela de roteamento de webhooks e mensagens por status
- Validações de campos, prompts e regras de segurança

**`tasks.md`** — Backlog de 41 tasks divididas em 5 fases:
- Fase 0: Infraestrutura AWS (T-01 a T-09)
- Fase 1: Estrutura dos agentes (T-10 a T-16)
- Fase 2: Tools / integração APIs (T-17 a T-24)
- Fase 3: Webhook handler (T-25 a T-28)
- Fase 4: Testes end-to-end (T-29 a T-33)
- Fase 5: Qualidade e produção (T-34 a T-41)

**`po-brief.md`** — Roteiro turno a turno do que o agente fala, o que o cliente responde, qual API é chamada e qual webhook é esperado em cada momento do fluxo.

---

### `mock_api/`

Servidor local que simula todas as APIs banQi para desenvolvimento e testes sem depender do ambiente real.

```
mock_api/
├── server.py          ← servidor FastAPI com os 8 endpoints simulados
├── test_flow.py       ← script de testes com 4 cenários (40/40 passando)
└── requirements.txt   ← dependências: fastapi, uvicorn, httpx
```

**Como iniciar o mock:**

```powershell
pip install -r mock_api/requirements.txt
python -m uvicorn mock_api.server:app --port 8000 --reload
```

Documentação interativa disponível em: **http://localhost:8000/docs**

**Como rodar os testes:**

```powershell
python -X utf8 mock_api/test_flow.py
```

**Cenários cobertos:**

| Cenário | Checks |
|---|---|
| Fluxo completo (Etapas 1–7, do termo ao DISBURSED) | 30 ✅ |
| Cliente sem elegibilidade (ELIGIBILITY_REJECTED) | 4 ✅ |
| Biometria reprovada (DENIED) | 3 ✅ |
| Erros síncronos (409, 412) | 3 ✅ |

**Padrões especiais para simular erros:**

| Como provocar | Comportamento simulado |
|---|---|
| CPF começando com `000` | Sem elegibilidade (ELIGIBILITY_REJECTED) |
| CPF começando com `999` | Erro na geração do PDF (PDF_GENERATION_ERROR) |
| `idBiometric: "denied-*"` | Biometria reprovada (DENIED) |
| Chamar `/consent-term/accept` duas vezes | Erro 409 (já aceito) |
| `idSimulation` inexistente na proposta | Erro 412 (simulação inválida) |

**Verificar webhooks recebidos:**
```
GET http://localhost:8000/test/webhooks/+5511999990001
```

**Resetar estado de um usuário:**
```
DELETE http://localhost:8000/test/state/+5511999990001
```

---

### `fluxo_trabalho/`

PDFs com os diagramas de sequência das 7 etapas do fluxo de contratação, fornecidos pela equipe banQi como referência para o desenvolvimento.

| Arquivo | Etapas |
|---|---|
| `fluxo-etapas-1-2-3-4-consignado-whatsapp.pdf` | Termo, aceite, simulação e proposta |
| `fluxo-etapas-5-6-7-consignado-whatsapp.pdf` | Biometria, aceite formal e status |

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

## Backlog Consolidado — Épicos e Histórias

> Detalhamento completo com 105 tasks e dependências em [`backlog.md`](backlog.md)

---

### E1 — Infraestrutura e Setup AWS
*Critério de aceite: Lambda recebe webhook do WhatsApp sem erro. AgentCore status ACTIVE.*

| História | O que entrega | Tasks |
|---|---|---|
| H-01 Conta AWS e Networking | VPC privada, subnets em 2 AZs, 7 VPC Endpoints PrivateLink, Security Groups | T-01 a T-04 |
| H-02 Repositório de Container | ECR com scan automático, Dockerfile ARM64, build via CodeBuild sem Docker local | T-05 a T-07 |
| H-03 AgentCore Runtime | Runtime provisionado via Terraform, variáveis de ambiente, health check `/ping` validado | T-08 a T-10 |
| H-04 AgentCore Memory | Memory store criado, namespace `users/{phone}/consignado` configurado, estratégias LTM ativas | T-11 a T-13 |
| H-05 AgentCore Gateway | Cognito OAuth, 8 targets MCP apontando para APIs banQi, autenticação validada | T-14 a T-16 |
| H-06 Lambda WhatsApp | Lambda + API Gateway + DynamoDB dedup (TTL 120s) + WAF (1.000 req/5min) + Meta webhook | T-17 a T-20 |
| H-07 Bedrock Guardrails | Prompt attack detection HIGH, topic policy DENY fora do escopo consignado | T-21 a T-22 |
| H-08 Secrets Manager | Secret JSON com credenciais WhatsApp, carregamento dual env var (dev) / Secrets Manager (prod) | T-23 a T-24 |

---

### E2 — Estrutura dos Agentes
*Critério de aceite: Conversa básica funciona no Chainlit local. Routing correto em 10 mensagens de teste.*

| História | O que entrega | Tasks |
|---|---|---|
| H-09 domain.yaml | Arquivo de configuração do domínio com agent_name, model IDs, prompts e namespaces de memória | T-25 a T-26 |
| H-10 Supervisor Agent | Routing por intenção, recuperação LTM, injeção de contexto completo na delegação, retomada por `current_step` | T-27 a T-30 |
| H-11 Consignado Agent | Controle de etapas (1–7), coleta progressiva (1 campo/mensagem), validações, mascaramento PII no chat | T-31 a T-34 |
| H-12 General Agent | Mensagem padrão de fora do escopo, log de intenção para análise futura | T-35 |
| H-13 Prompts | `supervisor.md` com routing e delegação, `consignado.md` com tom, etapas e tratamento de erros | T-36 a T-37 |
| H-14 Memória e Persistência | STM sliding window, LTM tools `memory_read/write`, `save_conversation_to_memory()` no Lambda | T-38 a T-40 |

---

### E3 — Integração com APIs banQi (Tools MCP)
*Critério de aceite: Cada tool retorna resposta esperada contra sandbox banQi.*

| História | O que entrega | Tasks |
|---|---|---|
| H-15 create_consent_term | POST /consent-term, trata 406/409, aguarda webhook `CONSENT_TERM_FILE_READY` e envia PDF | T-41 a T-44 |
| H-16 accept_consent_term | POST /consent-term/accept, captura IP/user-agent automático, roteia `SIMULATION_READY` ou `NO_OFFER_AVAILABLE` | T-45 a T-47 |
| H-17 create_simulation | POST /simulations, cache hit (200 imediato) vs cache miss (202 + webhook), trata TOKEN_EXPIRED | T-48 a T-51 |
| H-18 get_simulations | GET /simulations como fallback quando webhook `SIMULATION_COMPLETED` é perdido | T-52 |
| H-19 create_proposal | POST /proposals, monta payload completo, aguarda `PROPOSAL_CREATED`, trata 412/422 | T-53 a T-56 |
| H-20 start_biometry | POST /biometry, formata e envia BioLink ao cliente via WhatsApp | T-57 a T-58 |
| H-21 continue_biometry | POST /biometry/continue, trata APPROVED/BIOMETRICS/DENIED, retry automático em BIOMETRICS | T-59 a T-61 |
| H-22 accept_proposal | POST /accept com headers extras `x-remote-address` e `user-agent` | T-62 a T-63 |

---

### E4 — Handler de Webhooks
*Critério de aceite: Todos os 6 tipos de evento processados corretamente em testes de integração.*

| História | O que entrega | Tasks |
|---|---|---|
| H-23 Roteamento de Eventos | Switch por tipo de evento: handlers para `CONSENT_TERM_FILE_READY`, `NO_OFFER_AVAILABLE`, `SIMULATION_READY`, `SIMULATION_COMPLETED`, `PROPOSAL_CREATED`, `PROPOSAL_STATUS_UPDATE` | T-64 a T-70 |
| H-24 Correlação de Sessão | Lookup de sessão ativa por `phone`, log auditável de eventos órfãos com PII mascarado | T-71 a T-72 |
| H-25 Sessão Expirada | HTTP 200 para webhooks sem sessão (evita retry desnecessário), fila de eventos pendentes para reconexão | T-73 a T-74 |
| H-26 Retry e DLQ | SQS DLQ, 3 tentativas com backoff exponencial, alarme CloudWatch para DLQ acumulando | T-75 a T-77 |

---

### E5 — Qualidade e Produção
*Critério de aceite: P95 < 5s. Zero PII em logs. Pipeline CI/CD automático.*

| História | O que entrega | Tasks |
|---|---|---|
| H-27 Testes Unitários | CPF, campos, PII masking, routing (10 in-scope + 10 out-of-scope), retomada por current_step | T-78 a T-82 |
| H-28 Testes de Integração | 8 tools contra sandbox (happy path + erro), pipeline de webhook E2E | T-83 a T-85 |
| H-29 Testes End-to-End | 7 cenários: fluxo completo, retomada, ELIGIBILITY_REJECTED, DENIED, TOKEN_EXPIRED, deduplicação, WhatsApp real | T-86 a T-92 |
| H-30 CI/CD | GitHub Actions (pytest + ruff + Trivy), pipeline de deploy staging (build ARM64 → ECR → agentcore launch) | T-93 a T-95 |
| H-31 Monitoramento | Dashboard CloudWatch (latência P95, erros, conversas, conversão), alarmes com SNS | T-96 a T-97 |
| H-32 Carga e Segurança | 1.000 conversas simultâneas (Locust), prompt injection, jailbreak, fuzz, auditoria PII em logs | T-98 a T-102 |
| H-33 Documentação | Runbook operacional, script LGPD `delete_user_data.py`, handover para o time banQi | T-103 a T-105 |

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

- [x] Especificação da arquitetura (`specs/spec.md`)
- [x] Fluxo conversacional turno a turno (`specs/pipeline/po-brief.md`)
- [x] Backlog detalhado — 105 tasks (`backlog.md`)
- [x] Documentação completa do projeto (`projeto.md`)
- [x] Mock API — 40/40 testes passando (`mock_api/`)
- [ ] Infraestrutura AWS — E1
- [ ] Implementação dos agentes — E2
- [ ] Integração com APIs banQi — E3
- [ ] Handler de webhooks — E4
- [ ] Testes E2E e go-live — E5

---

*Desenvolvido por CI&T para banQi · Stack: Python · Strands Agents SDK · AWS Bedrock AgentCore*
