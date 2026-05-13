# Projeto — Agente Conversacional: Empréstimo Consignado via WhatsApp
**banQi × CI&T — MVP v1.0**
*Última atualização: 2026-05-12*

---

## Índice

1. [Visão do Produto](#1-visão-do-produto)
2. [Arquitetura da Solução](#2-arquitetura-da-solução)
3. [Fluxo Conversacional (7 Etapas)](#3-fluxo-conversacional-7-etapas)
4. [Épicos e Histórias de Usuário](#4-épicos-e-histórias-de-usuário)
5. [Critérios de Aceite por Épico](#5-critérios-de-aceite-por-épico)
6. [Especificações Técnicas](#6-especificações-técnicas)
7. [Provisionamento de Serviços AWS](#7-provisionamento-de-serviços-aws)
8. [Estratégia do Mock](#8-estratégia-do-mock)
9. [Estratégia de Desenvolvimento](#9-estratégia-de-desenvolvimento)
10. [Segurança e LGPD](#10-segurança-e-lgpd)
11. [Estimativa e Roadmap](#11-estimativa-e-roadmap)

---

## 1. Visão do Produto

### Objetivo

Construir um assistente de IA conversacional no WhatsApp que guia o cliente do banQi pelo fluxo completo de simulação e contratação de empréstimo consignado — do primeiro "Oi" até o depósito do dinheiro na conta — sem intervenção humana.

### Escopo do MVP

| Incluído | Excluído |
|---|---|
| Simulação de empréstimo consignado | Consulta de saldo |
| Contratação completa (7 etapas) | Extrato e pagamentos |
| Retomada de conversa interrompida | Empréstimo pessoal |
| Tratamento de erros e elegibilidade | FAQ geral do banco |
| Biometria facial (Único) | Suporte a atendente humano |

### Proposta de Valor

O cliente contrata um empréstimo consignado pelo WhatsApp, no horário que quiser, sem ir a uma agência, sem ligar para uma central, com resposta em segundos em cada etapa.

### Público-Alvo

Clientes banQi com renda via folha de pagamento (servidores públicos, beneficiários INSS) que já usam WhatsApp e têm acesso ao aplicativo banQi.

---

## 2. Arquitetura da Solução

### Visão Geral

```
CLIENTE (WhatsApp)
    │
    ▼  mensagem de texto
┌─────────────────────────────────────────────────────────────┐
│  Meta WhatsApp Business API                                 │
└─────────────────────────────────────────────────────────────┘
    │  webhook POST
    ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS API Gateway + WAF                                      │
│  Rate limit: 1.000 req/5min por IP                          │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│  Lambda Handler                                             │
│  1. Valida assinatura HMAC-SHA256                           │
│  2. Deduplica mensagem (DynamoDB, TTL 120s)                 │
│  3. Invoca AgentCore Runtime                                │
│  4. Persiste memória (create_event)                         │
│  5. Envia resposta ao cliente via WhatsApp API              │
└─────────────────────────────────────────────────────────────┘
    │  invoke_agent_runtime
    ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS Bedrock AgentCore Runtime (container ARM64)            │
│                                                             │
│  SUPERVISOR AGENT  (Claude Sonnet 4.6)                      │
│  ├─ Classifica intenção                                     │
│  ├─ Gerencia memória LTM                                    │
│  ├─→ CONSIGNADO AGENT  (Claude Haiku 4.5) ← foco do MVP    │
│  └─→ GENERAL AGENT     (Claude Haiku 4.5) ← fora do escopo │
└─────────────────────────────────────────────────────────────┘
    │  tools MCP via AgentCore Gateway
    ▼
┌─────────────────────────────────────────────────────────────┐
│  APIs banQi (via AgentCore Gateway / MCP)                   │
│  POST /consent-term  →  POST /consent-term/accept           │
│  POST /simulations   →  POST /proposals                     │
│  POST /biometry      →  POST /biometry/continue             │
│  POST /proposals/{id}/accept                                │
└─────────────────────────────────────────────────────────────┘
    │  webhooks assíncronos
    ▼
┌─────────────────────────────────────────────────────────────┐
│  6 Eventos de Webhook                                       │
│  CONSENT_TERM_FILE_READY  SIMULATION_READY                  │
│  SIMULATION_COMPLETED     PROPOSAL_CREATED                  │
│  NO_OFFER_AVAILABLE       PROPOSAL_STATUS_UPDATE            │
└─────────────────────────────────────────────────────────────┘
```

### Hierarquia de Agentes

| Agente | Modelo | Função |
|---|---|---|
| Supervisor | Claude Sonnet 4.6 | Classifica intenção, recupera memória LTM, delega |
| Consignado Agent | Claude Haiku 4.5 | Conduz as 7 etapas, chama APIs via tools MCP |
| General Agent | Claude Haiku 4.5 | Responde fora do escopo com mensagem padrão |

### Regra Crítica: Delegação com Contexto Completo

Sub-agentes são **stateless** — não têm memória entre chamadas. O Supervisor sempre injeta o contexto completo ao delegar:

```
ERRADO:  consignado_agent("12345-6")
CORRETO: consignado_agent("Número de conta informado: 12345-6.
          CPF: ***.456.789-**, Nome: João Silva,
          Etapa atual: 4 — coletando dados bancários,
          Banco: Itaú (341), Agência: 1234.")
```

---

## 3. Fluxo Conversacional (7 Etapas)

### Diagrama Completo

```
CLIENTE                  AGENTE                   API / WEBHOOK
  │                        │                           │
  │ "Oi" / "Quero empréstimo"│                         │
  │───────────────────────►│                           │
  │                        │ Solicita CPF              │
  │◄───────────────────────│                           │
  │ CPF + Nome             │                           │
  │───────────────────────►│                           │
  │                        │── POST /consent-term ────►│
  │                        │◄── CONSENT_TERM_FILE_READY│
  │ Recebe PDF do termo    │                           │
  │◄───────────────────────│                           │
  │ "ACEITO"               │                           │
  │───────────────────────►│                           │
  │                        │── POST /consent-term/accept►│
  │                        │◄────── SIMULATION_READY  │
  │ Recebe oferta automática│                          │
  │◄───────────────────────│                           │
  │ "Quero R$ 5.000 em 12x"│                           │
  │───────────────────────►│                           │
  │                        │── POST /simulations ─────►│
  │                        │◄── SIMULATION_COMPLETED  │
  │ Confirma simulação     │                           │
  │◄───────────────────────│                           │
  │ "Sim, quero prosseguir"│                           │
  │───────────────────────►│                           │
  │                        │ Coleta e-mail, CEP, banco │
  │◄──────────────────────►│                           │
  │ Confirma dados         │                           │
  │───────────────────────►│                           │
  │                        │── POST /proposals ───────►│
  │                        │◄──── PROPOSAL_CREATED    │
  │                        │── POST /biometry ────────►│
  │ Recebe link biometria  │                           │
  │◄───────────────────────│                           │
  │ (faz selfie no link)   │                           │
  │ "Pronto"               │                           │
  │───────────────────────►│                           │
  │                        │── POST /biometry/continue►│
  │                        │◄──── { APPROVED }        │
  │ "CONFIRMAR"            │                           │
  │───────────────────────►│                           │
  │                        │── POST /accept ──────────►│
  │                        │◄── ACCEPTED → DISBURSED  │
  │ Updates de status      │                           │
  │◄───────────────────────│                           │
```

### Etapa por Etapa

#### Etapa 1 — Termo de Consentimento
- Agente coleta CPF e nome completo
- Chama `POST /v1/whatsapp/consent-term`
- Aguarda webhook `CONSENT_TERM_FILE_READY` com PDF em base64
- Envia PDF ao cliente e solicita aceite ("ACEITO" / "sim")

**Erros possíveis:**
- `406` — 3+ CPFs no mesmo número → encerrar com orientação de suporte
- `409` — já tem termo ativo → retomar do ponto salvo na memória
- `NO_OFFER_AVAILABLE (PDF_GENERATION_ERROR)` → "Problema técnico, tente novamente"

#### Etapa 2 — Aceite e Simulação Automática
- Chama `POST /v1/whatsapp/consent-term/accept` com IP e user-agent
- Aguarda webhook `SIMULATION_READY` (oferta pré-calculada: R$ 8.000 / 24x)
- Apresenta: valor, parcelas, CET, data do depósito
- Pergunta: "Deseja prosseguir ou prefere simular outro valor?"

**Erros possíveis:**
- `NO_OFFER_AVAILABLE (ELIGIBILITY_REJECTED)` → encerrar com empatia

#### Etapa 3 — Simulação Manual (opcional)
- Se cliente quiser ajustar: coleta valor desejado e número de parcelas
- Chama `POST /v1/whatsapp/simulations`
- Resposta `200` (cache hit) → apresenta imediatamente
- Resposta `202` (cache miss) → aguarda webhook `SIMULATION_COMPLETED`

#### Etapa 4 — Dados Cadastrais e Proposta
Agente coleta progressivamente (um campo por mensagem):
1. E-mail
2. CEP → busca endereço → confirma/corrige
3. Número e complemento
4. Banco (código ou nome)
5. Agência
6. Conta + dígito
7. Tipo de conta (Corrente / Poupança / Pagamento / Salário)

Após confirmação do cliente, chama `POST /v1/whatsapp/proposals`.
Aguarda webhook `PROPOSAL_CREATED` → salva `idProposal` na memória.

> **Importante:** Nome, sexo, nacionalidade e ocupação **não são coletados** — vêm do account service automaticamente.

#### Etapa 5 — Biometria (Único)
- Chama `POST /proposals/{idProposal}/biometry` → recebe `idAntiFraud` + BioLink
- Envia link ao cliente: "Acesse e faça uma selfie rápida (menos de 1 min)"
- Cliente conclui e avisa o agente
- Chama `POST /biometry/continue` com `idAntiFraud` + `idBiometric`
- `APPROVED` → avança | `DENIED` → encerra com instrução de suporte

#### Etapa 6 — Aceite Formal
- Exibe resumo: valor, parcelas, taxa
- Cliente responde "CONFIRMAR"
- Chama `POST /proposals/{idProposal}/accept` com IP + user-agent + idBiometric

#### Etapa 7 — Acompanhamento de Status
Webhooks `PROPOSAL_STATUS_UPDATE` chegam automaticamente:

| Status | Mensagem ao Cliente |
|---|---|
| ACCEPTED | "Proposta recebida! Processando seu contrato. 🔄" |
| SIGNED | "Contrato assinado digitalmente! ✍️" |
| CCB_GENERATED | "Cédula de Crédito Bancária registrada. 📄" |
| FORMALIZED | "Averbação aprovada! Aguardando desembolso. ⏳" |
| PENDING_DISBURSEMENT | "Desembolso agendado para [data]. 📅" |
| DISBURSED | "🎉 R$ [valor] depositado na sua conta! Bom proveito!" |
| CANCELED | "Proposta cancelada. Posso ajudar a entender ou iniciar nova simulação?" |
| ERROR | "Erro no processamento. Entre em contato com o suporte banQi." |

### Retomada de Conversa

| `current_step` | Comportamento ao Retornar |
|---|---|
| 0 | Iniciar do zero |
| 1 | "Ainda estou gerando seu termo. Um momento..." |
| 2 | "Processando seu aceite. Aguarde..." |
| 3 | Reapresentar simulação disponível |
| 4 | Continuar coletando dados de onde parou |
| 5 | "Ainda precisamos concluir a biometria. Posso reenviar o link?" |
| 6 | "Ainda precisa confirmar o contrato. Deseja prosseguir?" |
| 7 | Verificar status atual e informar o cliente |

---

## 4. Épicos e Histórias de Usuário

---

### ÉPICO 1 — Infraestrutura e Setup AWS

**Objetivo:** Prover a base técnica na AWS para hospedar os agentes, gerenciar memória e conectar as APIs banQi.

---

**H-01 — Conta AWS e Landing Zone**
> *Como engenheiro de infraestrutura, preciso que a conta AWS esteja configurada com VPC, subnets privadas e VPC Endpoints para que os agentes se comuniquem com os serviços AWS sem trafegar pela internet pública.*

Detalhes técnicos:
- VPC com subnets privadas em 2 AZs (us-east-1a, us-east-1b)
- 7 VPC Endpoints (PrivateLink): Bedrock, Bedrock Runtime, Bedrock Agent, BedrockAgentCore, ECR API, ECR DKR, Secrets Manager
- Parâmetro `vpc_mode`: `create` (nova VPC) / `existing` (reusar) / `none` (sem VPC)

---

**H-02 — Repositório de Container (ECR)**
> *Como engenheiro, preciso de um repositório ECR para armazenar a imagem Docker ARM64 do agente para que o AgentCore Runtime possa fazer pull e executar.*

Detalhes técnicos:
- ECR repository `{domain_slug}-agent`
- Scan automático de vulnerabilidades habilitado
- Lifecycle policy: manter últimas 10 imagens
- Build via CodeBuild (ARM64 Graviton — sem necessidade de Docker local)

---

**H-03 — AgentCore Runtime**
> *Como engenheiro, preciso provisionar o AgentCore Runtime para que os agentes rodem em container gerenciado pela AWS, com escala automática e observabilidade integrada.*

Detalhes técnicos:
- Container ARM64 Python 3.12, usuário não-root (UID 1000)
- Health check endpoint: `GET /ping`
- Variáveis de ambiente: model IDs, memory ID, guardrail ID
- IAM Role com permissões: Bedrock, Memory, Gateway, Logs, ECR

---

**H-04 — AgentCore Memory**
> *Como PO, preciso que o agente lembre informações do cliente entre sessões (CPF, nome, etapa atual) para que o cliente não precise repetir dados caso a conversa seja interrompida.*

Detalhes técnicos:
- Memory store `BanQiMemory`
- STM: sliding window por sessão (AgentCoreMemorySessionManager)
- LTM: namespace `users/{phone}/consignado` com 13 chaves (ver seção 6.2)
- Estratégias: SEMANTIC, USER_PREFERENCE, SUMMARIZATION
- Namespace criado via script `setup_memory.py`

---

**H-05 — AgentCore Gateway (MCP)**
> *Como engenheiro, preciso de um Gateway MCP para que o Consignado Agent chame as APIs banQi como tools sem expor credenciais no código do agente.*

Detalhes técnicos:
- Cognito User Pool com OAuth 2.0 client credentials
- Targets MCP apontando para os 8 endpoints banQi
- Headers de autenticação banQi injetados pelo Gateway
- Zero credenciais no código do agente

---

**H-06 — Lambda Webhook WhatsApp**
> *Como engenheiro, preciso de uma Lambda que receba mensagens do WhatsApp e as encaminhe ao AgentCore Runtime para que o canal WhatsApp funcione como ponto de entrada do agente.*

Detalhes técnicos:
- Lambda Python 3.12, timeout 29s (limite API Gateway)
- API Gateway REST com rota `POST /webhook` e `GET /webhook` (verificação Meta)
- WAF: rate limit 1.000 req/5min
- DynamoDB dedup: TTL 120s, conditional put atômico
- Validação HMAC-SHA256 do header `X-Hub-Signature-256`

---

**H-07 — Bedrock Guardrails**
> *Como PO, preciso que o agente não responda perguntas fora do escopo de empréstimo consignado e que seja resistente a tentativas de manipulação (prompt injection) para garantir a segurança do produto.*

Detalhes técnicos:
- Prompt attack detection: sensibilidade HIGH
- Topic policy: DENY para tudo fora de "empréstimo consignado"
- Aplicado no nível do modelo (BedrockModel)
- `guardrail_latest_message=True` — evalua apenas última mensagem

---

**H-08 — Secrets Manager e Configurações**
> *Como engenheiro de segurança, preciso que credenciais (WhatsApp token, chaves banQi) sejam armazenadas no Secrets Manager e não em variáveis de ambiente em produção, para estar em conformidade com as políticas de segurança.*

Detalhes técnicos:
- Secret `{domain_slug}/whatsapp` com JSON: `access_token`, `app_secret`, `verify_token`, `phone_number_id`
- Carregamento: env var (dev) → Secrets Manager (prod), sem fallback, fail-fast
- `lru_cache(maxsize=32)` para evitar chamadas repetidas ao Secrets Manager

---

### ÉPICO 2 — Estrutura dos Agentes

**Objetivo:** Implementar a hierarquia de agentes com routing correto, memória integrada e prompts ajustados para o fluxo consignado.

---

**H-09 — domain.yaml do Domínio Consignado**
> *Como engenheiro, preciso de um arquivo de configuração `domain.yaml` que defina os agentes, modelos, namespaces de memória e ferramentas disponíveis para que toda a lógica de domínio fique separada do código Python.*

Estrutura mínima:
```yaml
domain_slug: banqi-consignado
agent_name: banqi_consignado_agent
supervisor:
  model_id: us.anthropic.claude-sonnet-4-6
  prompt_file: prompts/supervisor.md
sub_agents:
  - name: consignado_agent
    model_id: us.anthropic.claude-haiku-4-5-20251001
    prompt_file: prompts/consignado.md
  - name: general_agent
    model_id: us.anthropic.claude-haiku-4-5-20251001
    prompt_file: prompts/general.md
memory:
  namespaces:
    - path: users/{user_id}/consignado
      top_k: 10
      score_threshold: 0.4
```

---

**H-10 — Supervisor Agent**
> *Como PO, preciso que o agente principal classifique a intenção do cliente e delegue para o sub-agente correto, sempre injetando o contexto completo da memória, para que o cliente tenha uma experiência coesa.*

Regras de routing:
- Intenção de empréstimo consignado → `consignado_agent`
- Qualquer outra intenção → `general_agent`
- Retomada: se `current_step > 0` na memória, retomar do ponto salvo

Comportamentos obrigatórios:
- Nunca pedir dado que já está na memória LTM
- Sempre injetar contexto completo ao delegar
- Atualizar `current_step` e `flow_status` na memória após cada avanço

---

**H-11 — Consignado Agent**
> *Como PO, preciso que o Consignado Agent conduza o cliente pelas 7 etapas com mensagens curtas, amigáveis e um passo por vez, para que o cliente não fique confuso ou sobrecarregado.*

Comportamentos obrigatórios:
- Máximo 3 linhas por mensagem
- Um campo coletado por mensagem
- Validar campo antes de avançar (ver tabela de validações na seção 6.4)
- Mascarar PII nas respostas (CPF → últimos 3 dígitos, conta → apenas banco + tipo)
- Apresentar simulação com: valor, parcelas, valor da parcela, CET, data do depósito

---

**H-12 — General Agent**
> *Como PO, preciso que o agente informe claramente quando não pode ajudar com algo fora do escopo, sem deixar o cliente sem resposta.*

Mensagem padrão:
> "Olá! Posso te ajudar exclusivamente com simulação e contratação de empréstimo consignado banQi. Para outros serviços, acesse o app banQi ou fale com nossa central."

---

**H-13 — Prompts (supervisor.md + consignado.md)**
> *Como engenheiro de IA, preciso de prompts precisos para cada agente para garantir que o comportamento seja consistente e alinhado com o fluxo definido pelo PO.*

Diretrizes do `supervisor.md`:
- Routing explícito com exemplos
- Instrução de recuperação de memória antes de qualquer delegação
- Regra de não repetir dados já coletados

Diretrizes do `consignado.md`:
- Tom amigável, simples, direto
- Sistema de etapas com `current_step`
- Tratamento de cada erro de API com mensagem específica
- Regras de mascaramento de PII no chat

---

### ÉPICO 3 — Integração com APIs banQi (Tools)

**Objetivo:** Implementar as 8 tools que o Consignado Agent usa para chamar os endpoints banQi via AgentCore Gateway.

---

**H-14 — Tool: create_consent_term (Etapa 1)**
> *Como Consignado Agent, preciso de uma tool que chame POST /consent-term e aguarde o webhook CONSENT_TERM_FILE_READY para enviar o PDF ao cliente.*

```python
def create_consent_term(name: str) -> dict
# POST /v1/whatsapp/consent-term
# Retorna: 202 (async) → aguarda CONSENT_TERM_FILE_READY
# Erros: 406 (limite CPFs), 409 (termo ativo)
```

---

**H-15 — Tool: accept_consent_term (Etapa 2)**
> *Como Consignado Agent, preciso de uma tool que registre o aceite do cliente com IP e user-agent e aguarde o webhook de simulação automática.*

```python
def accept_consent_term(ip: str, user_agent: str) -> dict
# POST /v1/whatsapp/consent-term/accept
# Retorna: 200 → aguarda SIMULATION_READY ou NO_OFFER_AVAILABLE
```

---

**H-16 — Tool: create_simulation (Etapa 3)**
> *Como Consignado Agent, preciso de uma tool que simule valores personalizados e trate cache hit (200) e cache miss (202 + webhook) de forma transparente.*

```python
def create_simulation(amount: float, num_installments: list[int]) -> dict
# POST /v1/whatsapp/simulations
# 200 → cache hit, retorna simulação imediata
# 202 → cache miss, aguarda SIMULATION_COMPLETED
# 422 TOKEN_EXPIRED → reiniciar do termo
```

---

**H-17 — Tool: get_simulations (Etapa 3 — fallback)**
> *Como Consignado Agent, preciso de uma tool de fallback para buscar simulações quando o webhook SIMULATION_COMPLETED for perdido.*

```python
def get_simulations(id_correlation: str = None) -> dict
# GET /v1/whatsapp/simulations
```

---

**H-18 — Tool: create_proposal (Etapa 4)**
> *Como Consignado Agent, preciso de uma tool que monte o payload completo da proposta com endereço e dados bancários e aguarde o webhook PROPOSAL_CREATED.*

```python
def create_proposal(id_simulation: str, email: str,
                    address: dict, bank_account: dict) -> dict
# POST /v1/whatsapp/proposals
# Retorna: 202 → aguarda PROPOSAL_CREATED
# Erros: 412 (simulação inválida), 422 (token expirado)
```

---

**H-19 — Tool: start_biometry (Etapa 5)**
> *Como Consignado Agent, preciso de uma tool que inicie a sessão de biometria e retorne o BioLink para ser enviado ao cliente.*

```python
def start_biometry(id_proposal: str) -> dict
# POST /v1/whatsapp/proposals/{idProposal}/biometry
# Retorna: idAntiFraud + provider (unico)
```

---

**H-20 — Tool: continue_biometry (Etapa 5)**
> *Como Consignado Agent, preciso de uma tool que confirme o resultado da biometria e trate os status APPROVED, BIOMETRICS e DENIED.*

```python
def continue_biometry(id_proposal: str, id_anti_fraud: str,
                      id_biometric: str, provider: str) -> dict
# POST /v1/whatsapp/proposals/{idProposal}/biometry/continue
# APPROVED → avança | BIOMETRICS → aguarda | DENIED → encerra
```

---

**H-21 — Tool: accept_proposal (Etapa 6)**
> *Como Consignado Agent, preciso de uma tool que registre o aceite formal do contrato com IP, user-agent e idBiometric para que o contrato seja assinado digitalmente.*

```python
def accept_proposal(id_proposal: str, id_biometric: str,
                    remote_address: str, user_agent: str) -> dict
# POST /v1/whatsapp/proposals/{idProposal}/accept
# Headers extras: x-remote-address, user-agent
```

---

### ÉPICO 4 — Handler de Webhooks

**Objetivo:** Rotear os webhooks assíncronos do banQi para as ações corretas do agente e do cliente no WhatsApp.

---

**H-22 — Roteamento de Webhooks por Evento**
> *Como engenheiro, preciso que o Lambda handler processe cada tipo de webhook do banQi e dispare a ação correta no agente para que o cliente receba as mensagens de forma automática e em tempo real.*

Tabela de roteamento:

| Evento | Ação |
|---|---|
| `CONSENT_TERM_FILE_READY` | Envia PDF ao cliente + solicita aceite |
| `NO_OFFER_AVAILABLE` | Mensagem de erro conforme `errorCode` |
| `SIMULATION_READY` | Apresenta simulação automática |
| `SIMULATION_COMPLETED` | Apresenta simulação manual com valores escolhidos |
| `PROPOSAL_CREATED` | Salva `idProposal` na memória + inicia biometria |
| `PROPOSAL_STATUS_UPDATE` | Envia mensagem de status ao cliente |

---

**H-23 — Correlação de Webhooks com Sessão Ativa**
> *Como engenheiro, preciso correlacionar cada webhook com o `phone` e `idCorrelation` corretos para que o evento seja processado pela sessão certa, mesmo com múltiplos clientes simultâneos.*

Detalhes:
- Chave de correlação: `phone` (E.164) presente em todos os webhooks
- Lookup na memória LTM pelo `phone` para recuperar sessão ativa
- Log de webhooks sem sessão ativa para auditoria

---

**H-24 — Tratamento de Webhooks com Sessão Expirada**
> *Como engenheiro, preciso que webhooks recebidos após a sessão do cliente expirar sejam tratados graciosamente, sem erros, para não gerar alertas falsos.*

Comportamento:
- Log do evento recebido sem sessão correspondente
- Não retornar erro 5xx (evitar reenvio pelo banQi)
- Retornar 200 OK com body `{"status": "session_expired"}`

---

**H-25 — Retry e Dead Letter Queue (DLQ)**
> *Como engenheiro, preciso de uma fila DLQ para webhooks não processados para garantir que nenhum evento crítico (como DISBURSED) seja perdido.*

Detalhes:
- SQS DLQ associada ao Lambda
- Retry: 3 tentativas com backoff exponencial
- Alarme CloudWatch: DLQ com mensagens > 0 por mais de 5 minutos

---

### ÉPICO 5 — Qualidade e Produção

**Objetivo:** Garantir que o sistema seja confiável, seguro e monitorável antes de ir ao ar.

---

**H-26 — Testes Unitários**
> *Como engenheiro, preciso de testes unitários para validações de campo, mascaramento PII e roteamento de intenção para garantir que a lógica core esteja correta e não regrida.*

Cobertura mínima: 80%
Casos obrigatórios:
- Validação de CPF (formato, dígito verificador)
- Validação de e-mail, CEP, banco, conta
- Mascaramento PII (CPF, telefone, e-mail)
- Routing Supervisor: intenções in-scope vs out-of-scope

---

**H-27 — Testes de Integração**
> *Como engenheiro, preciso de testes de integração que chamem as APIs banQi (sandbox) para cada tool individualmente para garantir que a integração está funcionando antes do E2E.*

Cada tool testada isoladamente contra sandbox banQi.
Cenários: happy path + pelo menos um cenário de erro por tool.

---

**H-28 — Testes End-to-End**
> *Como PO, preciso que o fluxo completo de contratação seja testado do "oi" ao DISBURSED, incluindo retomada de conversa e todos os caminhos de erro, para garantir que o produto entrega o prometido.*

Cenários obrigatórios:
1. Fluxo completo (Etapas 1–7)
2. Retomada após abandono na Etapa 3
3. ELIGIBILITY_REJECTED
4. Biometria DENIED
5. TOKEN_EXPIRED + reinício
6. Deduplicação (mesma mensagem enviada 2x)

---

**H-29 — Monitoramento e Alertas**
> *Como engenheiro de operações, preciso de dashboards e alertas no CloudWatch para monitorar a saúde do sistema em produção.*

Métricas obrigatórias:
- Latência P50/P95/P99 por etapa
- Taxa de erros por tipo (4xx, 5xx)
- Conversas ativas e concluídas
- Taxa de conversão (iniciou → DISBURSED)
- DLQ com mensagens acumuladas

---

**H-30 — Testes de Segurança**
> *Como engenheiro de segurança, preciso validar que o sistema é resistente a prompt injection, jailbreak e vazamento de PII para garantir conformidade com LGPD e políticas de segurança.*

Casos de teste:
- Prompt injection via campo de nome
- Jailbreak (tentar fazer o agente sair do escopo)
- PII leak (agente nunca deve repetir CPF completo nos logs)
- Fuzz testing nos campos de entrada

---

## 5. Critérios de Aceite por Épico

| Épico | Critério de Aceite |
|---|---|
| E1 — Infraestrutura | Lambda recebe e processa webhook de teste do WhatsApp sem erro. `agentcore status` retorna ACTIVE. |
| E2 — Agentes | Conversa básica funciona via Chainlit local sem chamar APIs banQi. Routing correto em 10 mensagens de teste. |
| E3 — Tools/APIs | Cada tool chamada individualmente retorna resposta esperada contra sandbox banQi. |
| E4 — Webhooks | Todos os 6 eventos processados corretamente em testes de integração. |
| E5 — Qualidade | Fluxo completo do "oi" ao DISBURSED sem intervenção humana. Latência P95 < 5s. Zero PII em logs. |

---

## 6. Especificações Técnicas

### 6.1 Headers Obrigatórios nas Chamadas à API banQi

```
x-whatsapp-phone : número do cliente em formato E.164 (+5511...)
x-document       : CPF do cliente (11 dígitos, sem pontuação)
x-partner        : "banqi-wpp" (fixo)
```

Etapa 6 requer headers adicionais:
```
x-remote-address : IP do dispositivo do cliente
user-agent       : user-agent do app WhatsApp
```

### 6.2 Memória LTM — Namespace `users/{phone}/consignado`

| Chave | Tipo | Quando Salvar |
|---|---|---|
| `cpf` | string (11 dígitos) | Etapa 1 — após coleta |
| `name` | string | Etapa 1 — após coleta |
| `ip` | string | Etapa 2 — IP do device |
| `user_agent` | string | Etapa 2 — user-agent do app |
| `id_simulation` | UUID | Etapa 2 ou 3 — após simulação escolhida |
| `simulation_amount` | number | Etapa 2 ou 3 |
| `simulation_installments` | integer | Etapa 2 ou 3 |
| `email` | string | Etapa 4 — após coleta |
| `address` | object | Etapa 4 — após confirmação |
| `bank_account` | object | Etapa 4 — após confirmação |
| `id_proposal` | UUID | Etapa 4 — após PROPOSAL_CREATED |
| `current_step` | integer (1–7) | Atualizar a cada avanço |
| `flow_status` | string | `active` / `completed` / `error` |

### 6.3 Payloads das APIs banQi

**POST /v1/whatsapp/consent-term**
```json
{ "name": "João da Silva" }
```

**POST /v1/whatsapp/consent-term/accept**
```json
{ "ip": "189.100.50.25", "userAgent": "WhatsApp/2.23.0" }
```

**POST /v1/whatsapp/simulations**
```json
{ "amount": 5000.00, "numInstallments": [12] }
```

**POST /v1/whatsapp/proposals**
```json
{
  "idSimulation": "uuid-da-simulacao",
  "email": "joao@email.com",
  "address": {
    "street": "Rua das Flores", "number": "789",
    "complement": "Apto 42", "neighborhood": "Centro",
    "city": "Rio de Janeiro", "state": "RJ",
    "country": "Brasil", "zipCode": "20040030"
  },
  "bankAccount": {
    "bankCode": "341", "bankBranch": "1234",
    "bankAccount": "12345", "bankAccountDigit": "6",
    "bankAccountType": "CHECKING"
  }
}
```

**POST /v1/whatsapp/proposals/{id}/biometry**
```json
{}
```

**POST /v1/whatsapp/proposals/{id}/biometry/continue**
```json
{
  "idAntiFraud": "uuid-anti-fraud",
  "idBiometric": "id-retornado-pelo-sdk-unico",
  "provider": "unico"
}
```

**POST /v1/whatsapp/proposals/{id}/accept**
```json
{ "idBiometric": "id-biometria-aprovada" }
```

### 6.4 Validações do Agente

| Campo | Regra de Validação |
|---|---|
| CPF | 11 dígitos numéricos + dígito verificador válido |
| Nome | Mínimo 2 palavras, sem caracteres especiais |
| E-mail | Formato RFC 5322 (regex) |
| CEP | 8 dígitos numéricos |
| Estado | 2 letras maiúsculas (sigla UF) |
| Código do banco | 3 dígitos numéricos |
| Agência | Numérico, sem dígito |
| Conta | Numérico |
| Dígito da conta | 1 caractere alfanumérico |
| Tipo de conta | CHECKING / SAVINGS / PAYMENT / SALARY |
| Valor do empréstimo | Número positivo, máximo 2 casas decimais |
| Parcelas | Inteiro positivo |

### 6.5 Tratamento de Erros de API

| Código / Evento | Mensagem ao Cliente |
|---|---|
| `406` | "Este número já atingiu o limite de CPFs vinculados. Entre em contato com o suporte banQi." |
| `409` (termo) | Retomar fluxo do ponto salvo na memória |
| `409` (aceite duplo) | Ignorar — já processado |
| `412` | "Houve um problema com sua simulação. Vamos tentar novamente." |
| `422 TOKEN_EXPIRED` | "Sua sessão expirou. Vou gerar um novo termo de consentimento." |
| `NO_OFFER_AVAILABLE / ELIGIBILITY_REJECTED` | "Infelizmente não encontramos uma oferta para você neste momento. Tente novamente em alguns dias." |
| `NO_OFFER_AVAILABLE / PDF_GENERATION_ERROR` | "Tivemos um problema técnico. Pode tentar novamente?" |
| `BIOMETRY DENIED` | "Não conseguimos confirmar sua identidade. Por segurança, não podemos prosseguir. Entre em contato com o suporte." |

---

## 7. Provisionamento de Serviços AWS

### 7.1 Visão Geral dos Módulos Terraform

```
infrastructure/terraform/
├── main.tf              ← Composição dos módulos
├── variables.tf
├── outputs.tf
├── providers.tf
├── terraform.tfvars     ← Valores por ambiente
└── modules/
    ├── iam/             ← IAM roles + policies (zero Resource: '*')
    ├── runtime/         ← ECR + AgentCore Runtime ARM64
    ├── memory/          ← AgentCore Memory (STM + LTM)
    ├── gateway/         ← AgentCore Gateway (Cognito OAuth + MCP)
    ├── network/         ← VPC + subnets + 7 VPC Endpoints
    ├── guardrails/      ← Bedrock Guardrails
    ├── knowledge_base/  ← Bedrock KB + S3 (não usado no MVP consignado)
    └── whatsapp/        ← Lambda + API Gateway + DynamoDB + WAF
```

### 7.2 Recursos Criados (36 no total)

| Módulo | Recursos Criados |
|---|---|
| iam | 2 IAM Roles (runtime + lambda), 4 policies |
| network | VPC, 2 subnets, Internet Gateway, 7 VPC Endpoints |
| runtime | ECR repo, AgentCore Runtime, CodeBuild project |
| memory | AgentCore Memory store, estratégias configuradas |
| gateway | Cognito User Pool, App Client, AgentCore Gateway |
| guardrails | Bedrock Guardrail com topic policy |
| whatsapp | Lambda, API Gateway, DynamoDB (dedup), WAF, Secrets Manager secret |

### 7.3 Variáveis Principais do Terraform

```hcl
domain_slug    = "banqi-consignado"
agent_name     = "banqi_consignado_agent"
environment    = "staging"          # dev | staging | prod
aws_account_id = "XXXXXXXXXXXX"
aws_region     = "us-east-1"
memory_name    = "BanQiConsignadoMemory"
image_tag      = "v1.0.0"
vpc_mode       = "create"           # create | existing | none
```

### 7.4 Pré-requisitos Locais

```bash
python3 --version          # 3.12+
pip install uv
aws sts get-caller-identity
pip install bedrock-agentcore-starter-toolkit
agentcore --version
```

**Permissões IAM mínimas:**
- `bedrock-agentcore:*`
- `bedrock:*`
- `iam:CreateRole`, `iam:PassRole`, `iam:PutRolePolicy`
- `iam:CreateServiceLinkedRole`
- `ecr:*`, `logs:*`

**Regiões suportadas (AgentCore):** us-east-1 (recomendado), us-east-2, us-west-2, eu-west-1, eu-central-1, ap-southeast-1, ap-southeast-2.

### 7.5 Sequência de Deploy

```
Passo 1 — Configuração local
  cp .env.example .env
  # Preencher: AWS_PROFILE, AWS_REGION, AWS_ACCOUNT_ID, model IDs

Passo 2 — Scripts de setup
  python scripts/setup_memory.py    # Cria BanQiConsignadoMemory
  python scripts/setup_guardrails.py
  python scripts/setup.py           # Gera .bedrock_agentcore.yaml

Passo 3 — IaC
  cd infrastructure/terraform
  terraform init && terraform apply

Passo 4 — Deploy do container
  agentcore launch
  agentcore invoke '{"prompt": "Olá"}'   # Teste rápido

Passo 5 — WhatsApp Lambda
  cd infrastructure/whatsapp
  sam build && sam deploy --guided

Passo 6 — Configurar Meta Developer Console
  # Webhook URL: URL do API Gateway
  # Verify Token: valor do Secrets Manager
  # Subscribe: evento "messages"
```

### 7.6 Verificação Pós-Deploy

```bash
# Runtime ativo
agentcore status

# Teste de mensagem
agentcore invoke '{"prompt": "Quero um empréstimo consignado", "phone_number": "5511999990001"}'

# Logs
aws logs tail /aws/bedrock-agentcore/runtimes/<agent-id>-DEFAULT --follow

# Lambda logs
aws logs tail /aws/lambda/banqi-consignado-whatsapp-staging --follow
```

---

## 8. Estratégia do Mock

### 8.1 Por que um Mock?

O desenvolvimento dos agentes e das tools não precisa aguardar o ambiente banQi estar disponível. O mock replica o comportamento exato das APIs — incluindo webhooks assíncronos — permitindo desenvolver e testar o agente localmente antes de conectar ao sandbox real.

### 8.2 Componentes do Mock

| Arquivo | Descrição |
|---|---|
| `mock_api/server.py` | Servidor FastAPI com todos os 8 endpoints |
| `mock_api/test_flow.py` | Script de testes com 4 cenários |
| `mock_api/requirements.txt` | fastapi, uvicorn, httpx |

### 8.3 Como Iniciar o Mock

```powershell
cd c:\Users\alanraldi\banQi_conversacional
python -X utf8 -m uvicorn mock_api.server:app --port 8000 --reload
```

Documentação interativa: **http://localhost:8000/docs**

### 8.4 Comportamento do Mock

**Webhooks assíncronos simulados via BackgroundTasks:**
- Delay de 0.8s (equivale ao processamento real do backend)
- Acessar em: `GET /test/webhooks/{phone}`
- Limpar estado: `DELETE /test/state/{phone}`

**Padrões especiais para cenários de erro:**

| Padrão | Comportamento |
|---|---|
| CPF iniciando com `999` | `NO_OFFER_AVAILABLE (PDF_GENERATION_ERROR)` |
| CPF iniciando com `000` | `NO_OFFER_AVAILABLE (ELIGIBILITY_REJECTED)` |
| `idBiometric: "denied-*"` | Retorna status `DENIED` |
| Aceitar termo 2x | Retorna `409` |
| `idSimulation` inexistente | Retorna `412` |

**Cache de simulação:**
- Mesmos parâmetros (amount + installments) → retorna `200` imediato (cache hit)
- Parâmetros diferentes → retorna `202` + webhook `SIMULATION_COMPLETED` (cache miss)

### 8.5 Cenários de Teste

**Executar todos os cenários:**
```powershell
python -X utf8 mock_api/test_flow.py
```

**Cenários cobertos:**

| Cenário | Checks | Resultado Esperado |
|---|---|---|
| Fluxo completo (happy path) | 30 | 30/30 ✅ |
| Elegibilidade rejeitada | 4 | 4/4 ✅ |
| Biometria reprovada | 3 | 3/3 ✅ |
| Erros síncronos (409, 412) | 3 | 3/3 ✅ |

**Resultado atual: 40/40 checks passando.**

### 8.6 Dados de Teste (Headers em todas as chamadas)

```
x-whatsapp-phone: +5511999990001
x-document:       12345678901
x-partner:        banqi-test
```

### 8.7 Evolução do Mock → Sandbox Real

Quando o ambiente sandbox banQi estiver disponível:
1. Trocar `BASE = "http://localhost:8000"` pela URL do sandbox
2. Atualizar as credenciais nos headers
3. Os mesmos testes funcionam sem alteração de código

---

## 9. Estratégia de Desenvolvimento

### 9.1 Fases e Dependências

```
Fase 0 (infra)  → Fase 1 (agentes)  → Fase 2 (tools)  → Fase 3 (webhooks)
                                                               ↓
                                                        Fase 4 (E2E)
                                                               ↓
                                                        Fase 5 (qualidade)
```

**Fase 1 pode rodar em paralelo com Fase 0** usando Chainlit local + mock.
**Fases 2 e 3 podem ser desenvolvidas em paralelo** após Fase 1 estável.

### 9.2 Fases Detalhadas

#### Fase 0 — Infraestrutura (1 semana)
Tasks T-01 a T-09: conta AWS, ECR, AgentCore Runtime/Memory/Gateway, Lambda, Guardrails, Secrets Manager, WhatsApp.

#### Fase 1 — Estrutura dos Agentes (1 semana)
Tasks T-10 a T-16: domain.yaml, Supervisor Agent, Consignado Agent, General Agent, prompts, namespaces LTM.

**Entrega:** Conversa básica funcionando via Chainlit local sem chamar APIs banQi.

#### Fase 2 — Tools / Integração APIs (2 semanas)
Tasks T-17 a T-24: 8 tools mapeando os endpoints banQi via AgentCore Gateway.

**Entrega:** Cada tool testada individualmente contra mock (e depois sandbox banQi).

#### Fase 3 — Webhook Handler (1 semana)
Tasks T-25 a T-28: roteamento de eventos, correlação com sessão, sessão expirada, DLQ retry.

**Entrega:** Todos os 6 eventos processados em testes de integração.

#### Fase 4 — End-to-End (1 semana)
Tasks T-29 a T-33: fluxo completo, retomada, erros, deduplicação, WhatsApp real.

**Entrega:** Fluxo completo funcionando do "oi" ao DISBURSED sem intervenção humana.

#### Fase 5 — Qualidade e Produção (2 semanas)
Tasks T-34 a T-41: testes unitários/integração/E2E, CI/CD, CloudWatch, carga, segurança, documentação.

**Entrega:** P95 < 5s. Zero PII em logs. Pipeline CI/CD automático.

### 9.3 Ambiente de Desenvolvimento Local

```
Chainlit (http://localhost:8001)
    │  simula WhatsApp
    ▼
Agentes (local, Strands Agents SDK)
    │  tools MCP
    ▼
Mock API (http://localhost:8000)
    │  dados simulados
    ▼
Webhooks (log em /test/webhooks/{phone})
```

### 9.4 Ambientes

| Ambiente | Agente | APIs banQi | WhatsApp |
|---|---|---|---|
| Local (dev) | Chainlit local | Mock (`localhost:8000`) | Não |
| Staging | AgentCore Runtime | Sandbox banQi | Número de teste |
| Produção | AgentCore Runtime | APIs reais banQi | Número oficial banQi |

### 9.5 CI/CD

**GitHub Actions:**
- `test.yml` — pytest + ruff no PR
- `security.yml` — Trivy container scan

**Bitbucket Pipelines (deploy staging):**
- lint → test → build Docker ARM64 → push ECR → `agentcore launch`

### 9.6 Decisões Técnicas

| Decisão | Escolha | Motivo |
|---|---|---|
| Framework de agentes | Strands Agents SDK | Herdado da PoC, integração nativa com AgentCore |
| Runtime | AgentCore (ARM64 Graviton) | Custo 20% menor que x86, melhor performance |
| Memória | AgentCore Memory | STM+LTM integrados, sem gerenciar banco de dados |
| Integração APIs | AgentCore Gateway (MCP) | Credenciais gerenciadas fora do código do agente |
| Canal | Lambda + API Gateway | Escala zero-para-N, sem servidor para gerenciar |
| HTTP no Lambda | `urllib.request` (stdlib) | Zero dependências extras no pacote Lambda |
| Deduplicação | DynamoDB conditional put | Atômico, serverless, TTL automático |
| IaC | Terraform | 8 módulos independentes, time familiar com a ferramenta |
| Build ARM64 | CodeBuild (cloud) | Não requer Docker local, funciona em qualquer OS |

---

## 10. Segurança e LGPD

### 10.1 Camadas de Segurança

```
Entrada do cliente
    │
    ▼
1. WAF — Rate limiting (1.000 req/5min)
    │
    ▼
2. HMAC-SHA256 — Assinatura do webhook Meta (timing-safe)
    │
    ▼
3. Validação de entrada — tamanho máx 4.096 chars (OWASP LLM04)
    │
    ▼
4. Bedrock Guardrails — Prompt injection + topic policy
    │
    ▼
5. Agente processa
    │
    ▼
6. PII masking em logs — CPF, telefone, e-mail (regex)
    │
    ▼
7. Logs estruturados JSON → CloudWatch
```

### 10.2 Mascaramento de PII

| Dado | Exibição em Logs | Exibição no Chat |
|---|---|---|
| CPF | `***.456.789-**` | Apenas 3 últimos dígitos |
| Telefone | `***-****-0001` | Não exibir |
| E-mail | `j***@email.com` | Apenas domínio |
| Conta bancária | Não logar | Apenas banco + tipo |

Implementação: `PIIMaskingFilter` aplicado em todos os handlers de log (regex prefer false positive — melhor mascarar um número que não é CPF do que vazar um CPF real).

### 10.3 LGPD — Direito ao Esquecimento

Script disponível: `scripts/delete_user_data.py`

Apaga:
- Namespace LTM do usuário (`users/{phone}/consignado`)
- Eventos de sessão STM
- Registros de deduplicação no DynamoDB

### 10.4 Gestão de Segredos

| Ambiente | Método |
|---|---|
| Dev local | Variáveis de ambiente (`.env`) |
| Staging/Prod | AWS Secrets Manager (JSON com todas as chaves) |

Nunca em código, nunca em variáveis de ambiente em produção. Fail-fast se o secret não for encontrado — sem fallback silencioso.

---

## 11. Estimativa e Roadmap

### Estimativa por Fase

| Fase | Tasks | Estimativa |
|---|---|---|
| 0 — Infraestrutura | T-01 a T-09 | 1 semana |
| 1 — Agentes | T-10 a T-16 | 1 semana |
| 2 — Tools/APIs | T-17 a T-24 | 2 semanas |
| 3 — Webhooks | T-25 a T-28 | 1 semana |
| 4 — E2E | T-29 a T-33 | 1 semana |
| 5 — Qualidade | T-34 a T-41 | 2 semanas |
| **Total** | **41 tasks** | **~8 semanas** |

### Status Atual do Projeto

| Item | Status |
|---|---|
| Especificação da arquitetura (`spec.md`) | ✅ Concluído |
| Fluxo conversacional (`po-brief.md`) | ✅ Concluído |
| Backlog de tasks (`tasks.md`) | ✅ Concluído |
| Mock API (server + testes) | ✅ Concluído (40/40 testes passando) |
| Infraestrutura AWS | ⬜ Pendente |
| Implementação dos agentes | ⬜ Pendente |
| Integração com APIs banQi | ⬜ Pendente |
| Testes E2E em staging | ⬜ Pendente |

### Próximos Passos Imediatos

1. **Provisionar infra AWS** — rodar `terraform apply` com módulos de runtime, memory e gateway
2. **Criar domain.yaml** do domínio consignado
3. **Implementar Supervisor Agent** e Consignado Agent (estrutura base sem tools)
4. **Validar agentes no Chainlit local** antes de conectar APIs reais
5. **Implementar tools** uma a uma, testando cada uma contra o mock

---

*Documento gerado em 2026-05-12. Mantido em `c:\Users\alanraldi\banQi_conversacional\projeto.md`.*
