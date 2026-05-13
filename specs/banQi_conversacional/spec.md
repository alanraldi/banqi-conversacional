# Spec — Agente Conversacional: Empréstimo Consignado via WhatsApp

## 1. Visão Geral

Assistente de IA conversacional via WhatsApp que guia o cliente pelo fluxo completo de simulação e contratação de crédito consignado em 7 etapas. Baseado na arquitetura da PoC (Strands Agents + AWS Bedrock AgentCore), adaptado para as APIs reais do banQi.

**Escopo:** Apenas simulação e contratação de empréstimo consignado.
**Canal:** WhatsApp Business via Lambda webhook.
**Runtime:** AWS Bedrock AgentCore + Strands Agents SDK.

---

## 2. Arquitetura de Agentes

### Padrão: Agents-as-Tools (herdado da PoC)

```
WhatsApp (cliente)
    ↓ webhook
Lambda Handler
    ↓ invoke
AgentCore Runtime
    ↓
SUPERVISOR AGENT
    ├─→ CONSIGNADO AGENT  ← foco deste MVP (substitui Services Agent da PoC)
    └─→ GENERAL AGENT     ← fallback para mensagens fora do fluxo
```

> Na PoC havia também um Knowledge Agent para dúvidas gerais. No MVP, o General Agent apenas informa que só atende empréstimo consignado e encerra.

### Responsabilidades por agente

| Agente | Modelo | Responsabilidade |
|---|---|---|
| Supervisor | Claude Sonnet 4.6 | Classifica intenção, gerencia memória, delega |
| Consignado Agent | Claude Haiku 4.5 | Conduz as 7 etapas, chama as APIs via tools |
| General Agent | Claude Haiku 4.5 | Responde fora do escopo com mensagem padrão |

### Regra crítica de delegação (herdada da PoC)

Sub-agentes são **stateless**. O Supervisor sempre injeta o contexto completo ao delegar:

```
❌ ERRADO:  consignado_agent("15/03/1990")
✅ CORRETO: consignado_agent("Data de nascimento do cliente: 15/03/1990.
            CPF: 12345678900. Nome: João Silva. Etapa atual: 4 - coletando endereço.")
```

---

## 3. Memória (LTM — AgentCore Memory)

Dados persistidos entre sessões por namespace:

### Namespace: `users/{phone}/consignado`

| Chave | Tipo | Quando salvar |
|---|---|---|
| `cpf` | string (11 dígitos) | Etapa 1 — após coleta |
| `name` | string | Etapa 1 — após coleta |
| `ip` | string | Etapa 2 — IP do device |
| `user_agent` | string | Etapa 2 — user-agent do app |
| `id_simulation` | UUID | Etapa 3 — após simulação escolhida |
| `simulation_amount` | number | Etapa 3 — valor escolhido |
| `simulation_installments` | integer | Etapa 3 — parcelas escolhidas |
| `email` | string | Etapa 4 — após coleta |
| `address` | object | Etapa 4 — após coleta completa |
| `bank_account` | object | Etapa 4 — após coleta completa |
| `id_proposal` | UUID | Etapa 4 — após PROPOSAL_CREATED |
| `current_step` | integer (1–7) | Atualizar a cada avanço |
| `flow_status` | string | `active` \| `completed` \| `error` |

**Regra:** Antes de pedir qualquer dado ao cliente, checar a memória. Se já existe, usar sem perguntar.

---

## 4. Tools do Consignado Agent

Cada tool representa uma chamada à API do banQi. Chamadas via **AgentCore Gateway (MCP)**.

### Headers obrigatórios em todas as tools

```python
headers = {
    "x-whatsapp-phone": phone,   # E.164 — vem da sessão
    "x-document": cpf,           # CPF — vem da memória
    "x-partner": "banqi-wpp"     # fixo
}
```

### Tool: `create_consent_term`

```python
def create_consent_term(name: str) -> dict:
    """POST /v1/whatsapp/consent-term — Etapa 1"""
```

Retorna: `202` (assíncrono) → aguardar webhook `CONSENT_TERM_FILE_READY`.

Erros síncronos a tratar:
- `406` → telefone com 3+ CPFs vinculados
- `409` → termo já ativo — pular para verificar etapa atual

---

### Tool: `accept_consent_term`

```python
def accept_consent_term(ip: str, user_agent: str) -> dict:
    """POST /v1/whatsapp/consent-term/accept — Etapa 2"""
```

Retorna: `200` → aguardar webhook `SIMULATION_READY` ou `NO_OFFER_AVAILABLE`.

---

### Tool: `create_simulation`

```python
def create_simulation(amount: float = None, num_installments: list[int] = None) -> dict:
    """POST /v1/whatsapp/simulations — Etapa 3"""
```

Retorna:
- `200` (cache hit) → simulação imediata
- `202` (cache miss) → aguardar webhook `SIMULATION_COMPLETED`

Erros a tratar:
- `422 TOKEN_EXPIRED` → informar cliente e reiniciar do termo

---

### Tool: `get_simulations`

```python
def get_simulations(id_correlation: str = None) -> dict:
    """GET /v1/whatsapp/simulations — Etapa 3 fallback"""
```

Usar quando o agente perder o webhook `SIMULATION_COMPLETED` e precisar verificar o status.

---

### Tool: `create_proposal`

```python
def create_proposal(
    id_simulation: str,
    email: str,
    address: dict,
    bank_account: dict
) -> dict:
    """POST /v1/whatsapp/proposals — Etapa 4"""
```

Retorna: `202` → aguardar webhook `PROPOSAL_CREATED`.

---

### Tool: `start_biometry`

```python
def start_biometry(id_proposal: str) -> dict:
    """POST /v1/whatsapp/proposals/{idProposal}/biometry — Etapa 5"""
```

Retorna: `idAntiFraud` + BioLink para enviar ao cliente.

---

### Tool: `continue_biometry`

```python
def continue_biometry(
    id_proposal: str,
    id_anti_fraud: str,
    id_biometric: str,
    provider: str
) -> dict:
    """POST /v1/whatsapp/proposals/{idProposal}/biometry/continue — Etapa 5"""
```

Status possíveis: `APPROVED` | `BIOMETRICS` | `DENIED`

---

### Tool: `accept_proposal`

```python
def accept_proposal(
    id_proposal: str,
    id_biometric: str,
    remote_address: str,
    user_agent: str
) -> dict:
    """POST /v1/whatsapp/proposals/{idProposal}/accept — Etapa 6"""
```

---

## 5. Webhooks recebidos pelo agente

O backend faz POST no endpoint do agente. O Lambda handler roteia pelo campo `event`.

| Evento | Etapa | Ação do agente |
|---|---|---|
| `CONSENT_TERM_FILE_READY` | 1 | Envia PDF ao cliente, solicita aceite |
| `NO_OFFER_AVAILABLE` | 1/2 | Informa erro conforme `errorCode` |
| `SIMULATION_READY` | 2 | Apresenta simulação automática, pergunta se aceita ou quer ajustar |
| `SIMULATION_COMPLETED` | 3 | Apresenta nova simulação com os valores escolhidos |
| `PROPOSAL_CREATED` | 4 | Salva `idProposal` na memória, inicia Etapa 5 |
| `PROPOSAL_STATUS_UPDATE` | 7 | Envia mensagem de status ao cliente |

### Tratamento de `NO_OFFER_AVAILABLE`

| `errorCode` | Mensagem ao cliente |
|---|---|
| `PDF_GENERATION_ERROR` | "Tivemos um problema técnico. Tente novamente em alguns instantes." |
| `TOKEN_GENERATION_ERROR` | "Não conseguimos verificar seus dados no momento. Tente mais tarde." |
| `ELIGIBILITY_REJECTED` | "Infelizmente não encontramos uma oferta disponível para você agora." |
| `SIMULATION_ERROR` | "Tivemos um problema ao simular o empréstimo. Tente novamente." |

### Tratamento de `PROPOSAL_STATUS_UPDATE`

| `newStatus` | Mensagem ao cliente |
|---|---|
| `ACCEPTED` | "Proposta recebida! Estamos processando seu contrato." |
| `SIGNED` | "Ótima notícia! Seu contrato foi assinado digitalmente." |
| `CCB_GENERATED` | "Cédula de Crédito registrada com sucesso." |
| `FORMALIZED` | "Averbação aprovada! Aguardando o desembolso." |
| `PENDING_DISBURSEMENT` | "Desembolso agendado para [data]." |
| `DISBURSED` | "R$ [valor] creditado na sua conta! Bom proveito!" |
| `CANCELED` | "Sua proposta foi cancelada. Precisa de ajuda?" |
| `ERROR` | "Ocorreu um erro no processamento. Entre em contato com o suporte." |

---

## 6. Dados coletados por etapa

### Etapa 1 — Agente coleta
- CPF (11 dígitos, sem pontuação)
- Nome completo

### Etapa 2 — Capturado automaticamente
- IP do dispositivo (extraído do request do WhatsApp)
- User-agent (extraído do header do request)

### Etapa 3 — Agente apresenta, cliente escolhe
- Aceitar simulação automática OU
- Informar valor desejado e número de parcelas

### Etapa 4 — Agente coleta progressivamente (um campo por mensagem)
1. E-mail
2. CEP (para buscar endereço via API de CEP)
3. Confirmar/corrigir: rua, número, complemento, bairro, cidade, estado
4. Banco (código ou nome)
5. Agência
6. Número da conta + dígito
7. Tipo de conta (Corrente / Poupança / Pagamento / Salário)

> Nome, sexo, nacionalidade e ocupação: **não solicitar** — vêm do account service automaticamente.

### Etapa 5 — Agente envia link, cliente age externamente
- BioLink enviado ao cliente para liveness + face match (Único)
- Agente aguarda retorno do SDK via `idBiometric`

### Etapa 6 — Agente registra aceite
- Confirmar com o cliente antes de assinar
- Enviar o `idBiometric` aprovado

---

## 7. Validações do agente

| Campo | Regra |
|---|---|
| CPF | 11 dígitos numéricos |
| Nome | Mínimo 2 palavras |
| E-mail | Formato válido (regex) |
| CEP | 8 dígitos numéricos |
| Estado | 2 letras (sigla) |
| Código do banco | 3 dígitos |
| Agência | Numérico |
| Conta | Numérico |
| Tipo de conta | Um dos: CHECKING, SAVINGS, PAYMENT, SALARY |
| Valor do empréstimo | Número positivo |
| Parcelas | Inteiro positivo |

---

## 8. Prompt do Supervisor — Diretrizes

```markdown
Você é o assistente financeiro do banQi no WhatsApp.
Seu único objetivo é ajudar o cliente a simular e contratar um empréstimo consignado.

## Routing
- Intenção relacionada a empréstimo consignado → consignado_agent
- Qualquer outra intenção → general_agent (mensagem padrão de escopo)

## Memória
1. Antes de QUALQUER delegação, recupere os dados do cliente da memória LTM.
2. Nunca peça um dado que já está na memória.
3. Ao delegar, inclua TODOS os dados disponíveis na memória.

## Regra de continuidade
Se o cliente já iniciou o fluxo (current_step > 0), retome do ponto onde parou.
Não reinicie o fluxo se já houver dados na memória.
```

---

## 9. Prompt do Consignado Agent — Diretrizes

```markdown
Você conduz o fluxo de contratação de empréstimo consignado do banQi via WhatsApp.

## Tom e estilo
- Linguagem simples, amigável e direta
- Mensagens curtas (máx. 3 linhas por mensagem)
- Um passo por mensagem — não sobrecarregue o cliente

## Etapa atual
Sempre saiba em qual etapa está. Use current_step da memória.

## Coleta de dados
- Peça um dado por vez
- Valide antes de avançar
- Se inválido, explique o erro e peça novamente

## Apresentação de simulação
Sempre mostrar:
- Valor a receber
- Número de parcelas
- Valor de cada parcela
- Taxa mensal (CET)
- Data prevista do depósito
Perguntar: "Deseja prosseguir com esses valores ou prefere simular outro?"

## Erros de API
- Erro técnico → mensagem amigável + sugestão de retry
- ELIGIBILITY_REJECTED → encerrar com empatia, não insistir

## Segurança
- Nunca repetir CPF completo no chat — usar apenas últimos 3 dígitos
- Nunca repetir dados bancários completos — confirmar apenas banco + tipo de conta
```

---

## 10. Segurança e LGPD (herdado da PoC)

- **PII Masking:** CPF, telefone e e-mail mascarados nos logs (regex filter)
- **Signature validation:** HMAC-SHA256 timing-safe em todos os webhooks
- **Deduplicação:** DynamoDB com TTL 24h previne processamento duplo de mensagens
- **Guardrails:** Bedrock Guardrails bloqueiam prompt injection e jailbreak
- **Secrets:** Credenciais via AWS Secrets Manager (nunca em variáveis de ambiente em prod)

---

## 11. Infraestrutura (herdada da PoC, adaptada)

| Componente | Serviço AWS | Observação |
|---|---|---|
| Runtime dos agentes | AgentCore Runtime (ARM64) | Container Docker Python 3.12 |
| Canal WhatsApp | Lambda + API Gateway + WAF | Webhook handler |
| Memória | AgentCore Memory | STM (sliding window) + LTM (namespaces) |
| APIs banQi | AgentCore Gateway (MCP) | Tools do Consignado Agent |
| Observabilidade | AgentCore Observability + CloudWatch | Traces + logs |
| Segurança | Bedrock Guardrails | Proteção contra abuso |
| Deduplicação | DynamoDB | TTL 24h |
| Segredos | Secrets Manager | WhatsApp token, credenciais banQi |

---

## 12. Diferenças da PoC → MVP

| Aspecto | PoC | MVP (consignado) |
|---|---|---|
| Agente de serviços | Services Agent (genérico) | Consignado Agent (especializado) |
| APIs | Mocks via Lambda | APIs reais banQi (7 etapas) |
| Fluxo | Multi-intenção (saldo, extrato, empréstimo) | Apenas empréstimo consignado |
| Autenticação cliente | Não havia | Biometria via Único (Etapa 5) |
| Webhooks | Não havia | 6 eventos assíncronos |
| Dados coletados | CPF, nome, renda, consentimento SPC | CPF, nome, e-mail, endereço, conta bancária |
| Knowledge Agent | Sim (dúvidas gerais) | Não (fora do escopo do MVP) |
