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

## Roadmap

| Fase | Escopo | Prazo |
|---|---|---|
| 0 — Infraestrutura AWS | VPC, ECR, AgentCore, Lambda, Guardrails | 1 semana |
| 1 — Agentes | Supervisor, Consignado Agent, prompts, memória LTM | 1 semana |
| 2 — Tools / APIs | 8 tools MCP mapeando os endpoints banQi | 2 semanas |
| 3 — Webhooks | Handler dos 6 eventos assíncronos | 1 semana |
| 4 — End-to-End | Testes completos + WhatsApp real | 1 semana |
| 5 — Qualidade | CI/CD, carga, segurança, LGPD, documentação | 2 semanas |
| **Total** | **41 tasks** | **~8 semanas** |

---

## Status Atual

- [x] Especificação da arquitetura (`spec.md`)
- [x] Fluxo conversacional (`po-brief.md`)
- [x] Backlog de tasks (`tasks.md`)
- [x] Mock API — 40/40 testes passando
- [x] Documentação do projeto (`projeto.md`)
- [ ] Infraestrutura AWS (Terraform)
- [ ] Implementação dos agentes
- [ ] Integração com APIs banQi
- [ ] Testes E2E em staging

---

*Desenvolvido por CI&T para banQi · Stack: Python · Strands Agents SDK · AWS Bedrock AgentCore*
