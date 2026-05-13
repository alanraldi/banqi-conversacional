# Guia de Deploy

Deploy passo a passo do framework conversational-agents na AWS. Cada etapa depende da anterior — siga a ordem.

```
1. Configuração local
2. Scripts de setup (Memory, Guardrails, AgentCore YAML)
3. IaC — Terraform OU CloudFormation OU CDK
4. Deploy AgentCore Runtime
5. WhatsApp Lambda (opcional)
6. Validação
```

---

## Pre-requisitos

```bash
# Python 3.12+
python3 --version

# uv (gerenciador de pacotes)
pip install uv

# AWS CLI configurado
aws --version
aws sts get-caller-identity

# AgentCore CLI
pip install bedrock-agentcore-starter-toolkit
agentcore --version

# SAM CLI (apenas se usar WhatsApp)
pip install aws-sam-cli
sam --version
```

**Permissões IAM mínimas:**
- `bedrock-agentcore:*` — Runtime, Memory, Gateway
- `bedrock:*` — Models, Knowledge Base, Guardrails
- `iam:CreateRole`, `iam:PassRole`, `iam:PutRolePolicy` — Roles do AgentCore
- `iam:CreateServiceLinkedRole` — Service-linked roles (runtime-identity, network)
- `ecr:*` — Container images
- `logs:*` — CloudWatch Logs

**Regiões suportadas para AgentCore:** us-east-1 (recomendado), us-east-2, us-west-2, eu-west-1, eu-central-1, ap-southeast-1, ap-southeast-2, ap-south-1, ap-northeast-1.

---

## Passo 1 — Configuração Local

```bash
# Clone e instale dependências
git clone <repo-url>
cd conversational-agents
uv venv && source .venv/bin/activate
uv sync

# Configure variáveis de ambiente
cp .env.example .env
```

Edite `.env` com valores obrigatórios:

```bash
AWS_PROFILE=seu-profile
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012

# Model IDs (Bedrock cross-region inference profiles)
SUPERVISOR_AGENT_MODEL_ID=us.anthropic.claude-sonnet-4-6
SERVICES_AGENT_MODEL_ID=us.anthropic.claude-sonnet-4-6
KNOWLEDGE_AGENT_MODEL_ID=us.anthropic.claude-sonnet-4-6
```

Edite `domains/banqi-banking/domain.yaml` se necessário (nome do domínio, sub-agents, namespaces de memória).

**Checkpoint:** `python -c "from src.domain.loader import load_domain_config; load_domain_config()"` sem erros.

---

## Passo 2 — Scripts de Setup

Os scripts provisionam recursos AWS necessários antes do deploy.

### 2.1 Bedrock Knowledge Base

A Knowledge Base deve existir antes do deploy. Se ainda não criou:

```bash
# Criar bucket S3
aws s3 mb s3://seu-projeto-kb-docs --region us-east-1

# Upload de documentos
aws s3 sync ./domains/banqi-banking/kb-docs/ s3://seu-projeto-kb-docs/

# Criar KB via Console AWS: Bedrock > Knowledge Bases > Create
# - Data Source: S3 bucket criado
# - Embeddings: Titan Embeddings G1
```

Atualize `.env`:

```bash
BEDROCK_KB_ID=seu-kb-id
```

### 2.2 AgentCore Memory

```bash
python scripts/setup_memory.py
```

Saída esperada:

```
INFO: Creating memory: BanQiMemory
INFO: Memory created: BanQiMemory-XXXXXXXXXX
INFO: Add to .env:
INFO:   AGENTCORE_MEMORY_ID=BanQiMemory-XXXXXXXXXX
```

Atualize `.env` com o `AGENTCORE_MEMORY_ID`.

### 2.3 Bedrock Guardrails (opcional)

```bash
python scripts/setup_guardrails.py
```

Atualize `.env` com o `BEDROCK_GUARDRAIL_ID`.

### 2.4 Gerar .bedrock_agentcore.yaml

```bash
python scripts/setup.py
```

Gera `.bedrock_agentcore.yaml` com agent name, memory e region extraídos do `domain.yaml`.

**Checkpoint:** Arquivo `.bedrock_agentcore.yaml` gerado na raiz do projeto.

---

## Passo 3 — IaC (Escolha um)

A infraestrutura pode ser provisionada via Terraform, CloudFormation ou CDK. Todos criam os mesmos recursos: IAM roles, ECR repo, AgentCore Runtime/Memory/Gateway.

### Opção A — Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edite terraform.tfvars com seus valores

terraform init
terraform plan
terraform apply
```

Outputs: `runtime_arn`, `memory_id`, `gateway_arn`, `ecr_uri`.

### Opção B — CloudFormation

```bash
# Edite parameters/dev.json com seus valores

aws cloudformation deploy \
  --template-file infrastructure/cloudformation/template.yaml \
  --parameter-overrides file://infrastructure/cloudformation/parameters/dev.json \
  --stack-name seu-projeto-dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

### Opção C — CDK Python

```bash
cd infrastructure/cdk
pip install -r requirements.txt

cdk bootstrap  # primeira vez na conta/região

cdk deploy --all \
  -c domain_slug=seu-projeto \
  -c agent_name=seu_multi_agent \
  -c memory_name=SeuProjetoMemory \
  -c environment=dev
```

**Checkpoint:** Recursos criados na conta AWS (verificar via Console ou CLI).

---

## Passo 4 — Deploy AgentCore Runtime

```bash
source .venv/bin/activate

# Deploy via CodeBuild (recomendado — não requer Docker local)
agentcore launch

# Se o agente já existe:
agentcore launch --auto-update-on-conflict
```

Saída esperada:

```
🚀 Launching Bedrock AgentCore (codebuild mode)...
🎉 CodeBuild completed successfully
✅ Agent created: arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/seu_agent-XXXXXXXXXX
```

Verificar:

```bash
# Status
agentcore status

# Teste rápido
agentcore invoke '{"prompt": "Olá, quais serviços você oferece?"}'

# Logs
aws logs tail /aws/bedrock-agentcore/runtimes/<agent-id>-DEFAULT --follow
```

Atualize `.env` com o Agent ID se necessário.

**Checkpoint:** `agentcore invoke` retorna resposta do agente.

---

## Passo 5 — WhatsApp Lambda (Opcional)

### 5.1 Configurar parâmetros

Crie um arquivo de parâmetros para o SAM deploy ou passe via CLI:

| Parâmetro | Descrição |
|---|---|
| `AgentName` | Nome/ARN do agente no AgentCore |
| `WhatsAppToken` | Token da WhatsApp Business API |
| `WhatsAppAppSecret` | App secret para validação HMAC |
| `WhatsAppVerifyToken` | Token de verificação do webhook |
| `WhatsAppPhoneNumberId` | Phone Number ID do WhatsApp Business |

### 5.2 Deploy via SAM

```bash
cd infrastructure/whatsapp

sam build

sam deploy --guided \
  --stack-name seu-projeto-whatsapp-dev \
  --parameter-overrides \
    AgentName=seu_multi_agent \
    WhatsAppToken=seu-token \
    WhatsAppAppSecret=seu-app-secret \
    WhatsAppVerifyToken=seu-verify-token \
    WhatsAppPhoneNumberId=seu-phone-id
```

Anote a `WebhookUrl` do output.

### 5.3 Configurar Meta Developer Console

1. Acesse [developers.facebook.com](https://developers.facebook.com/) > seu app
2. WhatsApp > Configuration > Webhook URL: cole a `WebhookUrl`
3. Verify Token: o mesmo passado como `WhatsAppVerifyToken`
4. Subscribe ao evento `messages`

### 5.4 Testar

```bash
# Logs da Lambda
aws logs tail /aws/lambda/seu-projeto-whatsapp-dev --follow

# Envie uma mensagem pelo WhatsApp para o número configurado
```

**Checkpoint:** Mensagem enviada via WhatsApp recebe resposta do agente.

---

## Passo 6 — Validação

### 6.1 Teste via Chainlit (local)

```bash
chainlit run src/channels/chainlit/app.py
# Acesse http://localhost:8000
```

Teste:
- Saudação inicial (welcome message do domain.yaml)
- Consulta que aciona Services Agent
- Consulta que aciona Knowledge Agent
- Continuidade de conversa (memória)

### 6.2 Teste via CLI

```bash
# Mensagem simples
agentcore invoke '{"prompt": "Olá", "phone_number": "5511999999999"}'

# Testar memória (segunda chamada deve lembrar contexto)
agentcore invoke '{"prompt": "Qual meu saldo?", "phone_number": "5511999999999"}'
```

### 6.3 Verificar memória

```bash
agentcore memory list --region us-east-1
```

### 6.4 Monitorar logs

```bash
# Runtime
aws logs tail /aws/bedrock-agentcore/runtimes/<agent-id>-DEFAULT --follow

# WhatsApp Lambda
aws logs tail /aws/lambda/<function-name> --follow
```

---

## Troubleshooting

### Erro: Service-Linked Role

```
Error: Failed creating service linked role for runtime-identity.bedrock-agentcore.amazonaws.com
```

Adicione permissão IAM:

```json
{
  "Effect": "Allow",
  "Action": "iam:CreateServiceLinkedRole",
  "Resource": "arn:aws:iam::*:role/aws-service-role/runtime-identity.bedrock-agentcore.amazonaws.com/*",
  "Condition": {
    "StringEquals": {
      "iam:AWSServiceName": "runtime-identity.bedrock-agentcore.amazonaws.com"
    }
  }
}
```

### Erro: Platform Mismatch (AMD64 vs ARM64)

Warning normal. O `agentcore launch` usa CodeBuild para build ARM64 na nuvem. Ignore.

### Erro: Missing env var no startup

```
EnvironmentError: Missing required environment variables: SUPERVISOR_AGENT_MODEL_ID (Supervisor)
```

A aplicação valida model IDs no startup. Verifique `.env` e garanta que as variáveis `*_MODEL_ID` estão preenchidas.

### Memory não encontrada

```bash
# Verificar se existe
agentcore memory list --region us-east-1

# Verificar .env
grep AGENTCORE_MEMORY_ID .env

# Recriar se necessário
python scripts/setup_memory.py
```

### Gateway retorna 401

Verifique credenciais do Gateway no `.env`:

```bash
grep GATEWAY_ .env
```

Teste o token endpoint isoladamente:

```bash
curl -s -X POST "$GATEWAY_TOKEN_ENDPOINT" \
  -d "grant_type=client_credentials&client_id=$GATEWAY_CLIENT_ID&client_secret=$GATEWAY_CLIENT_SECRET&scope=$GATEWAY_SCOPE"
```

### Agent não responde

```bash
# Status
agentcore status

# Logs com filtro de erro
aws logs filter-log-events \
  --log-group-name /aws/bedrock-agentcore/runtimes/<agent-id>-DEFAULT \
  --filter-pattern "ERROR"
```

### WhatsApp não recebe resposta

```bash
# Verificar se webhook está recebendo
aws logs tail /aws/lambda/<function-name> --follow

# Testar webhook manualmente
curl -X POST https://<webhook-url>/webhook \
  -H "Content-Type: application/json" \
  -d '{"object":"whatsapp_business_account","entry":[{"changes":[{"value":{"messages":[{"from":"5511999999999","text":{"body":"Olá"},"type":"text","id":"test123","timestamp":"1234567890"}]}}]}]}'
```
