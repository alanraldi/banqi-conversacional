# banQi Conversacional — Solução Completa para AWS

Guia completo para subir o agente conversacional de empréstimo consignado do banQi em produção na AWS. Tudo que você precisa está nesta pasta.

---

## O que é esta solução

Um agente de IA que atende clientes no WhatsApp e conduz o fluxo completo de contratação de empréstimo consignado — do primeiro "oi" até o depósito na conta.

**Tecnologias principais:**
- **Claude Sonnet 4.6** como Supervisor (roteador de intenções)
- **Claude Haiku 4.5** como agente especializado em consignado e agente geral
- **AWS Bedrock AgentCore** — Runtime (container), Memory (LTM), Gateway (MCP)
- **AWS Lambda + API Gateway** — canal WhatsApp
- **Terraform** — toda a infraestrutura como código

---

## Estrutura da Pasta

```
Solução completa para subir na AWS/
├── README.md                          ← este arquivo
├── .env.example                       ← variáveis de ambiente necessárias
├── Dockerfile                         ← container do AgentCore Runtime (ARM64)
├── pyproject.toml                     ← dependências Python
│
├── infrastructure/terraform/
│   ├── main.tf                        ← orquestrador dos 7 módulos
│   ├── variables.tf                   ← variáveis de entrada do Terraform
│   ├── outputs.tf                     ← outputs (URLs, ARNs) após o apply
│   ├── terraform.tfvars.example       ← exemplo de configuração (copiar e preencher)
│   └── modules/
│       ├── network/main.tf            ← VPC + subnets + VPC Endpoints + WAF
│       ├── iam/main.tf                ← IAM roles (Runtime, Lambda, Gateway)
│       ├── memory/main.tf             ← AgentCore Memory (SEMANTIC + SUMMARIZATION)
│       ├── guardrails/main.tf         ← Bedrock Guardrails (LGPD + prompt attack)
│       ├── gateway/main.tf            ← AgentCore Gateway MCP (8 targets banQi)
│       ├── runtime/main.tf            ← ECR + AgentCore Runtime (ARM64)
│       └── whatsapp/main.tf           ← Lambda + API GW + DynamoDB + WAF
│
├── src/
│   ├── main.py                        ← entrypoint do AgentCore Runtime
│   ├── agents/
│   │   ├── factory.py                 ← cria Supervisor + sub-agentes (Agents-as-Tools)
│   │   └── context.py                 ← thread-safe session context
│   ├── config/
│   │   └── settings.py               ← configurações (Pydantic Settings)
│   ├── tools/
│   │   ├── consent_term.py            ← APIs: criar/aceitar termo de consentimento
│   │   ├── simulation.py              ← APIs: criar/buscar simulações
│   │   ├── proposal.py                ← APIs: criar proposta
│   │   └── biometry.py                ← APIs: iniciar/continuar biometria
│   ├── utils/
│   │   ├── logging.py                 ← JSON logging + PII masking
│   │   ├── pii.py                     ← PIIMaskingFilter + funções mask_*
│   │   ├── validation.py              ← validações de CPF, email, CEP, etc.
│   │   └── secrets.py                 ← Secrets Manager helper
│   ├── webhook/
│   │   ├── handler.py                 ← Lambda handler (WhatsApp + banQi)
│   │   ├── models.py                  ← Pydantic models para payloads
│   │   ├── router.py                  ← roteamento de eventos banQi
│   │   ├── events.py                  ← handlers de cada evento banQi
│   │   ├── session.py                 ← gestão de sessões via DynamoDB
│   │   ├── signature.py               ← HMAC-SHA256 webhook validation
│   │   ├── whatsapp_client.py         ← WhatsApp Cloud API client
│   │   └── agentcore_client.py        ← AgentCore Runtime + Memory client
│   └── gateway/
│       └── token_manager.py           ← OAuth2 token manager (Cognito)
│
└── domains/consignado/
    ├── domain.yaml                    ← configuração dos agentes e memória
    └── prompts/
        ├── supervisor.md              ← prompt do Supervisor (routing + memória)
        ├── consignado.md              ← prompt do Agente Consignado (7 etapas)
        └── general.md                 ← prompt do Agente Geral (fora de escopo)
```

---

## Pré-requisitos

| Item | Versão | Para que serve |
|------|--------|----------------|
| AWS CLI | ≥ 2.x | autenticação + deploy |
| Terraform | ≥ 1.7 | provisionar infraestrutura |
| Docker | ≥ 24 | build do container (ARM64) |
| Python | ≥ 3.12 | desenvolvimento e testes |
| Conta AWS | — | com acesso a Bedrock, AgentCore, Lambda |
| Meta Developer Portal | — | conta WhatsApp Business API |
| Acesso ao Bedrock | — | modelos Claude Sonnet 4.6 e Haiku 4.5 habilitados |

### Habilitar modelos no Bedrock

Antes de começar, habilite os modelos na região `us-east-1`:
1. Acesse [AWS Bedrock → Model access](https://us-east-1.console.aws.amazon.com/bedrock/home#/modelaccess)
2. Habilite: **Claude Sonnet 4.6** e **Claude Haiku 4.5**
3. Aguarde o status ficar "Access granted" (pode levar alguns minutos)

---

## Passo a Passo de Configuração

### Etapa 1 — Configurar variáveis de ambiente

```bash
# Na raiz desta pasta (Solução completa para subir na AWS/)
cp .env.example .env
```

Edite o `.env` e preencha:

```bash
# Obrigatório — sua conta AWS
AWS_ACCOUNT_ID=123456789012
AWS_REGION=us-east-1

# API banQi
BANQI_API_BASE_URL=https://api.banqi.com.br

# WhatsApp (obter no Meta Developer Portal)
WHATSAPP_TOKEN=EAAxxxxxxxxxx
WHATSAPP_APP_SECRET=abc123def456
WHATSAPP_VERIFY_TOKEN=meu-token-secreto
WHATSAPP_PHONE_NUMBER_ID=123456789012345
```

Os campos AgentCore (AGENTCORE_MEMORY_ID, etc.) são preenchidos **após** o `terraform apply`.

### Etapa 2 — Configurar Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edite o `terraform.tfvars`:

```hcl
aws_account_id     = "123456789012"
environment        = "staging"          # dev | staging | prod
banqi_api_base_url = "https://api.banqi.com.br"
whatsapp_token           = "EAAxxxxxxxxxx"
whatsapp_app_secret      = "abc123def456"
whatsapp_verify_token    = "meu-token-secreto"
whatsapp_phone_number_id = "123456789012345"
```

### Etapa 3 — Provisionar a infraestrutura

```bash
# Na pasta infrastructure/terraform/
terraform init
terraform plan    # revisar antes de aplicar
terraform apply   # provisiona tudo (~10-15 minutos)
```

O `terraform apply` vai:
1. Criar VPC + subnets + VPC Endpoints + WAF
2. Criar IAM roles (Runtime, Lambda, Gateway)
3. Criar AgentCore Memory (SEMANTIC + SUMMARIZATION)
4. Criar Bedrock Guardrails
5. Criar AgentCore Gateway MCP (8 targets banQi)
6. Fazer build do Docker (linux/arm64) e push para ECR
7. Criar AgentCore Runtime a partir do container
8. Criar Lambda + API Gateway + DynamoDB + WAF

**Outputs importantes após o apply:**

```
runtime_arn         = "arn:aws:bedrock-agentcore:us-east-1:..."
memory_id           = "mem-xxxxxxxxxxxxxxxx"
gateway_url         = "https://gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp/..."
whatsapp_webhook_url = "https://xxxxxx.execute-api.us-east-1.amazonaws.com/staging/webhook"
```

### Etapa 4 — Atualizar .env com os outputs

```bash
# Copie os valores dos outputs para o .env:
AGENTCORE_MEMORY_ID=mem-xxxxxxxxxxxxxxxx
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:...
AGENTCORE_GATEWAY_ENDPOINT=https://gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp/...
GATEWAY_CLIENT_ID=<valor do output>
GATEWAY_CLIENT_SECRET=<valor do output>
GATEWAY_TOKEN_ENDPOINT=<valor do output>
GATEWAY_SCOPE=banqi-consignado-staging-gateway/invoke
BEDROCK_GUARDRAIL_ID=<valor do output>
```

### Etapa 5 — Configurar webhook no Meta Developer Portal

1. Acesse [developers.facebook.com](https://developers.facebook.com)
2. Vá em **WhatsApp → Configuration → Webhook**
3. Configure:
   - **Callback URL**: `<whatsapp_webhook_url>` (output do terraform)
   - **Verify Token**: mesmo valor do `WHATSAPP_VERIFY_TOKEN`
4. Selecione o campo **messages**
5. Clique em **Verify and Save**

---

## Descrição Detalhada de Cada Componente

### `src/main.py` — Entrypoint do AgentCore Runtime
**O que faz:** Ponto de entrada chamado pelo AgentCore Runtime quando recebe uma mensagem. Recebe `user_input`, `user_id` (telefone E.164) e `session_id`, cria o Supervisor e retorna a resposta.

**Como conecta:** O AgentCore Runtime chama `invoke()` automaticamente com base no protocolo HTTP que o container expõe na porta 8080.

### `src/agents/factory.py` — Agent Factory
**O que faz:** Cria o Supervisor Agent usando o padrão **Agents-as-Tools**: cada sub-agente (consignado, geral) é registrado como uma `@tool` do Supervisor. O Supervisor decide qual invocar baseado na intenção do usuário.

**Como conecta:**
- Lê a configuração de `domains/consignado/domain.yaml`
- Cria modelos BedrockModel com os model IDs das variáveis de ambiente
- Conecta ao AgentCore Gateway via MCP para as tools do consignado
- Conecta ao AgentCore Memory para memória de longo prazo (LTM)
- Cache com `@lru_cache` para modelos, prompts e tools (performance)

**Detalhe importante:** Sub-agentes são **stateless**. O Supervisor sempre injeta o contexto completo (dados da memória, current_step) ao delegar.

### `src/agents/context.py` — Session Context
**O que faz:** Armazena `user_id` e `session_id` de forma thread-safe usando `threading.local()`. Permite que os sub-agentes acessem o contexto do usuário atual sem parâmetros explícitos.

### `src/config/settings.py` — Configurações
**O que faz:** Singleton de configurações via Pydantic Settings. Carrega de `.env` em dev e de variáveis de ambiente em prod.

**Como conecta:** Toda a aplicação usa `get_settings()` para acessar configurações. Em prod, as credenciais sensíveis vêm do Secrets Manager via `src/utils/secrets.py`.

### `src/tools/consent_term.py` — Ferramentas de Consentimento
**O que faz:** Dois `@tool` decorados para o Strands SDK:
- `create_consent_term(name, phone, cpf)` — POST `/v1/whatsapp/consent-term` — inicia geração do PDF (assíncrono, aguarda webhook CONSENT_TERM_FILE_READY)
- `accept_consent_term(phone, cpf, ip, user_agent)` — POST `/v1/whatsapp/consent-term/accept`

**Headers obrigatórios em todas as chamadas banQi:** `x-whatsapp-phone`, `x-document` (CPF), `x-partner: "banqi-wpp"`

### `src/tools/simulation.py` — Ferramentas de Simulação
**O que faz:**
- `create_simulation(phone, cpf, amount?, num_installments?)` — cria simulação personalizada ou automática
  - HTTP 200: simulação imediata (status "READY")
  - HTTP 202: assíncrono, aguarda webhook SIMULATION_COMPLETED (status "WAITING")
- `get_simulations(phone, cpf, id_correlation?)` — busca simulações existentes (fallback)

### `src/tools/proposal.py` — Ferramentas de Proposta
**O que faz:**
- `create_proposal(phone, cpf, id_simulation, email, address, bank_account)` — POST `/v1/whatsapp/proposals`
  - HTTP 202: proposta submetida, aguarda webhook PROPOSAL_CREATED com o `idProposal`

### `src/tools/biometry.py` — Ferramentas de Biometria
**O que faz:**
- `start_biometry(phone, cpf, id_proposal)` — retorna BioLink para o cliente fazer liveness
- `continue_biometry(phone, cpf, id_proposal, id_anti_fraud, id_biometric, provider)` — consulta resultado
  - Status: APPROVED (prosseguir) | BIOMETRICS (aguardar) | DENIED (encerrar)

### `src/webhook/handler.py` — Lambda Handler
**O que faz:** Entrypoint do Lambda. Detecta o tipo de request e roteia:
1. `GET /webhook` → verificação hub.challenge do WhatsApp
2. `POST /webhook` → mensagem WhatsApp → valida assinatura → deduplica → invoca AgentCore → envia resposta
3. `POST /webhook/banqi` → evento assíncrono banQi → busca sessão → roteia para handler correto

**Segurança:**
- Valida assinatura HMAC-SHA256 (timing-safe) de todas as mensagens WhatsApp
- Deduplicação via DynamoDB (TTL 120s) para evitar processar a mesma mensagem duas vezes

### `src/webhook/signature.py` — Validação de Assinatura
**O que faz:** Valida o header `X-Hub-Signature-256` usando `hmac.compare_digest` (timing-safe). Evita timing attacks.

### `src/webhook/session.py` — Gestão de Sessões
**O que faz:** Persiste e recupera sessões ativas no DynamoDB (tabela `banqi-consignado-staging-sessions`). Permite correlacionar webhooks banQi com a sessão do usuário certo.

### `src/webhook/agentcore_client.py` — Cliente AgentCore
**O que faz:**
- `invoke_agent_runtime()` — chama o AgentCore Runtime via `bedrock-agentcore-runtime` boto3
- `save_conversation_to_memory()` — persiste turnos na LTM do AgentCore Memory

### `src/webhook/events.py` — Handlers de Eventos banQi
**O que faz:** Uma função por tipo de evento webhook. Retorna a mensagem a enviar ao cliente (ou None se nenhuma mensagem).

| Evento | O que acontece |
|--------|---------------|
| CONSENT_TERM_FILE_READY | Envia PDF + pede aceitação |
| NO_OFFER_AVAILABLE | Mensagem de erro amigável por código |
| SIMULATION_READY | Apresenta oferta com valores |
| SIMULATION_COMPLETED | Igual ao SIMULATION_READY |
| PROPOSAL_CREATED | Silencioso (agente prossegue internamente) |
| PROPOSAL_STATUS_UPDATE | Mensagem de status da proposta (SIGNED, CCB_GENERATED, DISBURSED...) |

### `src/gateway/token_manager.py` — OAuth2 Token Manager
**O que faz:** Singleton thread-safe que gerencia o token OAuth2 do Cognito para autenticar no AgentCore Gateway MCP. Renova automaticamente 60s antes da expiração.

**Como conecta:** Usado por `src/agents/factory.py` ao criar o MCPClient para o agente consignado.

### `src/utils/pii.py` — PII Masking (LGPD)
**O que faz:** `PIIMaskingFilter` aplica regex em todos os logs para mascarar CPF, telefone, email, CEP, conta bancária antes de gravar no CloudWatch.

**Regra fundamental:** Preferimos mascarar demais do que vazar dados pessoais.

### `domains/consignado/domain.yaml` — Configuração dos Agentes
**O que faz:** Define a estrutura de agentes (Supervisor + sub-agentes), configuração de memória (namespaces LTM), canais e mensagens de erro. É o arquivo central que `factory.py` lê para criar os agentes.

### `domains/consignado/prompts/supervisor.md` — Prompt do Supervisor
**O que faz:** Define o comportamento do agente Supervisor:
- Routing: quando delegar para `consignado_assistant` vs `general_assistant`
- Memória: como usar a LTM para retomar fluxos
- Segurança: regras de PII no chat (nunca exibir CPF completo)
- Como injetar contexto ao delegar (inclui todos os dados da memória)

### `domains/consignado/prompts/consignado.md` — Prompt do Agente Consignado
**O que faz:** Guia completo das 7 etapas do fluxo de contratação:
1. Consentimento LGPD
2. Simulação
3. Dados bancários
4. Proposta
5. Biometria
6. Aceite formal
7. Conclusão

### `infrastructure/terraform/modules/network/main.tf` — Rede
**O que faz:** VPC com 2 subnets privadas + 1 pública, NAT Gateway, Internet Gateway, 5 Interface VPC Endpoints (Bedrock, SecretsManager, CloudWatch Logs, SSM) + 2 Gateway Endpoints (DynamoDB, S3), 3 Security Groups, WAF com rate limit (1000 req/IP/5min) + managed rules.

**Por que VPC Endpoints:** O Runtime e Lambda ficam em subnets privadas (sem IP público). Os VPC Endpoints permitem que eles acessem serviços AWS sem sair para a internet.

### `infrastructure/terraform/modules/iam/main.tf` — Permissões
**O que faz:** 3 IAM Roles com o princípio do menor privilégio:

| Role | Principal | Permissões |
|------|-----------|-----------|
| Runtime Role | bedrock-agentcore.amazonaws.com | ECR pull + Bedrock InvokeModel + AgentCore Memory CRUD |
| Lambda Role | lambda.amazonaws.com | DynamoDB (dedup + sessions) + AgentCore InvokeRuntime + Secrets Manager |
| Gateway Role | bedrock-agentcore.amazonaws.com | CloudWatch apenas |

### `infrastructure/terraform/modules/memory/main.tf` — Memória LTM
**O que faz:** Cria o AgentCore Memory store com 2 estratégias:
- **SEMANTIC** (`/users/{actorId}/consignado`) — dados do usuário (CPF, simulação, proposta, current_step)
- **SUMMARIZATION** (`/summaries/{actorId}/{sessionId}`) — resumos de sessão

### `infrastructure/terraform/modules/guardrails/main.tf` — Segurança
**O que faz:** Bedrock Guardrails com:
- Detecção de prompt attack (HIGH sensitivity)
- Topic policy: bloqueia qualquer assunto fora do escopo consignado
- PII anonymization nos logs (CPF, email, telefone, nome)
- Filtros de conteúdo (hate, sexual, violence, insults)

### `infrastructure/terraform/modules/gateway/main.tf` — MCP Gateway
**O que faz:** AgentCore Gateway com protocolo MCP (Model Context Protocol) e 8 targets HTTP para as APIs banQi. Usa Cognito OAuth2 Client Credentials para autenticação.

| Target MCP | Endpoint banQi |
|------------|---------------|
| consent-term-get | GET /consent-term |
| consent-term-accept | POST /consent-term/accept |
| simulations-get | GET /simulations |
| simulations-post | POST /simulations |
| proposals-get | GET /proposals |
| biometry-start | POST /biometry |
| biometry-continue | POST /biometry/continue |
| proposals-accept | POST /proposals/accept |

### `infrastructure/terraform/modules/runtime/main.tf` — Container Runtime
**O que faz:** ECR repository (IMMUTABLE, scan_on_push, lifecycle 10 imagens), build Docker (linux/arm64) e push automático, criação do AgentCore Runtime com o container.

**Importante:** O build Docker roda localmente (`null_resource` + `local-exec`). Você precisa ter Docker e AWS CLI configurados na máquina onde executa o terraform.

### `infrastructure/terraform/modules/whatsapp/main.tf` — Canal WhatsApp
**O que faz:** DynamoDB (dedup + sessions), Secrets Manager (credenciais WhatsApp), Lambda (python3.12, arm64, 256MB, 120s, 10 concurrent), API Gateway HTTP v2 (GET+POST /webhook + POST /webhook/banqi), CloudWatch Logs, WAF association.

---

## Cenários de Teste

### Cenário 1 — Fluxo Completo (Happy Path)

**Objetivo:** Verificar que o cliente consegue contratar empréstimo do início ao fim.

**Pré-condição:** Solução deployada, WhatsApp configurado, API banQi disponível.

**Passos:**

```
1. Cliente envia: "Oi, quero fazer um empréstimo consignado"
   → Resposta esperada: "Olá! Para começar, preciso do seu CPF."

2. Cliente envia o CPF
   → Resposta esperada: "Perfeito! E seu nome completo?"

3. Cliente envia o nome
   → Sistema: cria termo de consentimento (assíncrono)
   → Webhook CONSENT_TERM_FILE_READY chega
   → Resposta esperada: "Seu Termo de Consentimento está pronto! [link PDF]
                         Você aceita os termos? (SIM ou NÃO)"

4. Cliente envia: "Sim"
   → Sistema: aceita termo (assíncrono)
   → Webhook SIMULATION_READY chega com oferta
   → Resposta esperada: "✅ Proposta disponível:
                         💰 Valor a receber: R$ 5.000,00
                         📅 Parcelas: 24x
                         💳 Valor de cada parcela: R$ 245,50
                         📊 Taxa mensal: 1,89%
                         Deseja prosseguir?"

5. Cliente: "Sim, quero contratar"
   → Resposta: "Ótimo! Qual é o seu banco?"

6. Cliente informa banco, agência, conta, tipo de conta (um por mensagem)

7. Sistema cria proposta → Webhook PROPOSAL_CREATED
   → Sistema inicia biometria → envia BioLink ao cliente

8. Cliente faz liveness no link
   → Webhook BIOMETRY_STATUS_UPDATE: APPROVED (ou simulado)
   → Resposta: "Biometria aprovada! Confirma a contratação?"

9. Cliente: "Confirmo"
   → Sistema aceita proposta
   → Webhooks SIGNED → CCB_GENERATED → DISBURSED
   → Resposta final: "R$ 5.000,00 creditado na sua conta banQi! Bom proveito! 🎉"
```

**Verificações:**
- [ ] Cada etapa responde em menos de 10 segundos
- [ ] CPF nunca aparece completo nas mensagens
- [ ] Dados bancários apenas últimos 4 dígitos nas confirmações
- [ ] Memory LTM retém dados entre sessões (fechar e reabrir WhatsApp)

---

### Cenário 2 — Retomada de Fluxo (Memória LTM)

**Objetivo:** Verificar que o cliente pode retomar de onde parou em outra sessão.

```
1. Cliente começa o fluxo, chega até a etapa 3 (dados bancários)
2. Cliente fecha o WhatsApp e abre no dia seguinte
3. Cliente envia: "Oi, quero continuar meu empréstimo"
   → Resposta esperada: "Olá de volta! Você estava na etapa de dados bancários.
                         Qual é o número da sua agência?"
   (sem pedir CPF nem nome novamente)
```

**Verificação:** O campo `current_step` na LTM deve ser 3.

---

### Cenário 3 — Mensagem Fora de Escopo

**Objetivo:** Verificar que o guardrail e o general_agent funcionam.

```
1. Cliente envia: "Qual o saldo da minha conta?"
   → Resposta esperada: "Posso te ajudar apenas com empréstimo consignado banQi.
                         Quer simular um valor ou iniciar uma contratação?"

2. Cliente envia: "Qual a capital da França?"
   → Resposta esperada: (igual ao item 1)
```

---

### Cenário 4 — Sem Oferta Disponível

**Objetivo:** Verificar tratamento quando o cliente não tem elegibilidade.

```
1. Cliente inicia fluxo e aceita o termo
   → Webhook NO_OFFER_AVAILABLE com errorCode: "ELIGIBILITY_REJECTED"
   → Resposta esperada: "Infelizmente não encontramos uma oferta de empréstimo
                         consignado disponível para você agora.
                         Qualquer dúvida, estamos aqui para ajudar."
```

---

### Cenário 5 — Teste via curl (API Gateway)

Substitua `<API_URL>` pela URL do output `whatsapp_webhook_url`.

**Verificar health:**
```bash
curl -X GET "<API_URL>/ping"
# Esperado: {"status": "ok"}
```

**Simular mensagem WhatsApp:**
```bash
curl -X POST "<API_URL>/webhook" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=fake" \
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
            "text": {"body": "Oi, quero fazer um empréstimo"},
            "timestamp": "1716000000"
          }]
        },
        "field": "messages"
      }]
    }]
  }'
# Esperado: {"status": "processed"}
```

**Simular webhook banQi:**
```bash
curl -X POST "<API_URL>/webhook/banqi" \
  -H "Content-Type: application/json" \
  -d '{
    "event": "SIMULATION_READY",
    "phone": "+5511999990001",
    "data": {
      "simulations": [{
        "amount": 5000.00,
        "numInstallments": 24,
        "installmentAmount": 245.50,
        "monthlyRate": 1.89,
        "disbursementDate": "2026-06-01"
      }]
    }
  }'
# Esperado: {"status": "processed", "event": "SIMULATION_READY"}
```

---

### Cenário 6 — Verificação de Logs no CloudWatch

```bash
# Ver logs da Lambda
aws logs tail /aws/lambda/banqi-consignado-staging-whatsapp --follow

# Ver logs do AgentCore Runtime
aws logs tail /aws/bedrock-agentcore/banqi-consignado-staging --follow

# Buscar erros
aws logs filter-log-events \
  --log-group-name /aws/lambda/banqi-consignado-staging-whatsapp \
  --filter-pattern "ERROR"
```

---

## Mapeamento: Variáveis de Ambiente

| Variável | Fonte em Dev | Fonte em Prod | Obrigatória |
|----------|-------------|---------------|-------------|
| AWS_REGION | .env | IAM Role (automático) | Sim |
| AWS_ACCOUNT_ID | .env | IAM Role (automático) | Sim |
| AGENTCORE_MEMORY_ID | output terraform | Lambda env var | Sim |
| AGENTCORE_RUNTIME_ARN | output terraform | Lambda env var | Sim |
| AGENTCORE_GATEWAY_ENDPOINT | output terraform | Runtime env var | Sim |
| GATEWAY_CLIENT_ID | output terraform | Runtime env var | Sim |
| GATEWAY_CLIENT_SECRET | output terraform | Secrets Manager | Sim |
| GATEWAY_TOKEN_ENDPOINT | output terraform | Runtime env var | Sim |
| GATEWAY_SCOPE | output terraform | Runtime env var | Sim |
| BEDROCK_GUARDRAIL_ID | output terraform | Runtime env var | Recomendado |
| WHATSAPP_TOKEN | .env | Secrets Manager | Sim |
| WHATSAPP_APP_SECRET | .env | Secrets Manager | Sim |
| WHATSAPP_VERIFY_TOKEN | .env | Secrets Manager | Sim |
| WHATSAPP_PHONE_NUMBER_ID | .env | Lambda env var | Sim |
| BANQI_API_BASE_URL | .env | Runtime env var | Sim |
| DEDUP_TABLE_NAME | output terraform | Lambda env var | Sim |
| SESSION_TABLE_NAME | output terraform | Lambda env var | Sim |

---

## Segurança e LGPD

Esta solução implementa controles obrigatórios:

| Controle | Implementação |
|----------|---------------|
| PII nos logs | `PIIMaskingFilter` — regex em todos os handlers do logging |
| Assinatura webhook | HMAC-SHA256 timing-safe (`hmac.compare_digest`) |
| Deduplicação | DynamoDB conditional put com TTL 120s |
| Guardrails | Bedrock Guardrails — prompt attack HIGH + topic policy |
| CPF no chat | Apenas últimos 3 dígitos exibidos (`***.***.*XX-YY`) |
| Dados bancários | Apenas últimos 4 dígitos da conta |
| Credenciais | AWS Secrets Manager (nunca em variáveis de ambiente em prod) |
| Rede | VPC privada + VPC Endpoints (sem internet para serviços AWS) |
| WAF | Rate limit 1000 req/IP/5min + AWSManagedRulesCommonRuleSet |

---

## Troubleshooting

### Erro: "AGENTCORE_GATEWAY_ENDPOINT não configurado — modo degradado"
**Causa:** Variável de ambiente não preenchida.
**Solução:** Copiar o `gateway_url` do output do terraform para o `.env`.

### Erro: "Falha ao obter token do Gateway"
**Causa:** Cognito pool não criado ou client credentials incorretos.
**Solução:** Verificar outputs `oauth_client_id`, `oauth_client_secret`, `token_endpoint` do módulo gateway.

### Erro: Lambda timeout
**Causa:** AgentCore Runtime demorando mais de 120s.
**Solução:** Verificar logs do Runtime. O timeout padrão da Lambda é 120s — suficiente para a maioria dos casos.

### Mensagem duplicada processada
**Causa:** DynamoDB dedup não configurado (`DEDUP_TABLE_NAME` vazio).
**Solução:** Verificar output `dedup_table_name` e configurar na Lambda.

### Webhook banQi não recebido
**Causa:** Sessão expirou na tabela `sessions` (TTL 24h).
**Solução:** Normal para sessões muito longas. O cliente pode reiniciar a conversa.

### Container build falha no terraform apply
**Causa:** Docker não está rodando ou sem credenciais AWS para ECR.
**Solução:** Verificar que Docker está rodando e que `aws ecr get-login-password` funciona.

---

## Custos Estimados (staging/mês)

| Serviço | Estimativa |
|---------|-----------|
| AgentCore Runtime (ARM64) | ~$50-200 (depende do uso) |
| Bedrock (Claude tokens) | ~$10-100 (depende do volume) |
| Lambda (100k invocações) | ~$0.20 |
| API Gateway HTTP | ~$1.00 |
| DynamoDB (PAY_PER_REQUEST) | ~$1-5 |
| Secrets Manager | ~$0.40 |
| VPC Endpoints (5 Interface) | ~$35 |
| NAT Gateway | ~$33 |
| **Total estimado** | **~$130-375/mês** |

Para reduzir custos em dev: use `vpc_mode = "none"` (elimina VPC Endpoints e NAT Gateway).

---

## Comandos Úteis

```bash
# Ver todos os outputs do terraform
terraform output

# Destruir infraestrutura (CUIDADO — irreversível)
terraform destroy

# Forçar rebuild do container
terraform apply -replace=module.runtime.null_resource.container_build

# Ver logs em tempo real
aws logs tail /aws/lambda/banqi-consignado-staging-whatsapp --follow --format short

# Invocar Lambda diretamente (teste)
aws lambda invoke \
  --function-name banqi-consignado-staging-whatsapp \
  --payload '{"httpMethod":"GET","path":"/webhook","queryStringParameters":{"hub.mode":"subscribe","hub.verify_token":"SEU_TOKEN","hub.challenge":"test123"}}' \
  response.json && cat response.json
```
