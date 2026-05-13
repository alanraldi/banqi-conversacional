# Security Requirements — conversational-agents

> **Referência**: [requirements.md](./requirements.md) | [design.md](./design.md)
> **Stack**: Python 3.12+, Strands Agent Framework, AWS AgentCore Runtime, Bedrock, Pydantic v2
> **Compliance**: LGPD, OWASP Top 10, OWASP LLM Top 10
> **Última atualização**: 2026-04-15

---

## Sumário

1. [IAM Least Privilege](#1-iam-least-privilege)
2. [Secrets Management](#2-secrets-management)
3. [Network Security](#3-network-security)
4. [Data Protection & LGPD](#4-data-protection--lgpd)
5. [Webhook Security](#5-webhook-security)
6. [Container Security](#6-container-security)
7. [Observability Security](#7-observability-security)
8. [IaC Security](#8-iac-security)
9. [LLM/AI Security (OWASP LLM Top 10)](#9-llmai-security)
10. [Checklist de Compliance](#10-checklist-de-compliance)

---

## 1. IAM Least Privilege

> **Ref**: US-16 (Fix C4) — IAM policies com `Resource: '*'` identificado como 🔴 Critical.

### 1.1 Princípio

**NUNCA** usar `Resource: '*'` ou `Action: '*'` em qualquer policy. Todos os ARNs devem ser scoped com `${AWS::AccountId}`, `${AWS::Region}` e nome do recurso.

### 1.2 Policy — AgentCore Runtime Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "BedrockModelInvocation",
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${Region}:${AccountId}:inference-profile/us.anthropic.claude-sonnet-4-*"
      ]
    },
    {
      "Sid": "AgentCoreMemoryAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:GetMemory",
        "bedrock-agentcore:PutMemory",
        "bedrock-agentcore:DeleteMemory"
      ],
      "Resource": "arn:aws:bedrock-agentcore:${Region}:${AccountId}:memory/${MemoryName}"
    },
    {
      "Sid": "AgentCoreGatewayAccess",
      "Effect": "Allow",
      "Action": [
        "bedrock-agentcore:InvokeGateway"
      ],
      "Resource": "arn:aws:bedrock-agentcore:${Region}:${AccountId}:gateway/${GatewayName}"
    },
    {
      "Sid": "BedrockKnowledgeBase",
      "Effect": "Allow",
      "Action": [
        "bedrock:Retrieve"
      ],
      "Resource": "arn:aws:bedrock:${Region}:${AccountId}:knowledge-base/${KnowledgeBaseId}"
    },
    {
      "Sid": "BedrockGuardrails",
      "Effect": "Allow",
      "Action": [
        "bedrock:ApplyGuardrail"
      ],
      "Resource": "arn:aws:bedrock:${Region}:${AccountId}:guardrail/${GuardrailId}",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Project": "${DomainSlug}"
        }
      }
    }
  ]
}
```

### 1.3 Policy — WhatsApp Lambda Role

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeAgentCoreRuntime",
      "Effect": "Allow",
      "Action": "bedrock-agentcore:InvokeAgentRuntime",
      "Resource": "arn:aws:bedrock-agentcore:${Region}:${AccountId}:runtime/${RuntimeName}/endpoint/*"
    },
    {
      "Sid": "DynamoDBDedup",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:${Region}:${AccountId}:table/${DedupTableName}"
    },
    {
      "Sid": "SecretsAccess",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:${Region}:${AccountId}:secret:${DomainSlug}/whatsapp-*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Project": "${DomainSlug}"
        }
      }
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${Region}:${AccountId}:log-group:/aws/lambda/${FunctionName}:*"
    }
  ]
}
```

### 1.4 Condition Keys Obrigatórias

| Condition Key | Uso |
|---------------|-----|
| `aws:ResourceTag/Project` | Restringe acesso a recursos tagueados com o domínio |
| `aws:SourceArn` | Trust policy do Lambda — apenas API Gateway específico |
| `aws:PrincipalOrgID` | Cross-account — apenas contas da organização |
| `bedrock:InferenceProfileArn` | Restringe modelos Bedrock permitidos |

### 1.5 Anti-Patterns Proibidos

```json
// ❌ NUNCA FAZER
{ "Action": "bedrock-agentcore:*", "Resource": "*" }
{ "Action": "bedrock:*", "Resource": "*" }
{ "Action": "dynamodb:*", "Resource": "*" }
{ "Action": "secretsmanager:*", "Resource": "*" }

// ✅ SEMPRE FAZER
{ "Action": "bedrock-agentcore:GetMemory", "Resource": "arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/BanQiMemory" }
```

---

## 2. Secrets Management

> **Ref**: US-09 (Fix C3) — Fallback silencioso para `"fallback_token"` identificado como 🔴 Critical.

### 2.1 Princípio

**ZERO** secrets hardcoded em código, variáveis de ambiente em plain text, ou valores fallback. Todos os secrets devem residir no AWS Secrets Manager ou SSM Parameter Store (SecureString).

### 2.2 Mapeamento de Secrets

| Secret | Serviço | Path | Rotação |
|--------|---------|------|---------|
| WhatsApp Access Token | Secrets Manager | `${DomainSlug}/whatsapp/access-token` | 90 dias |
| WhatsApp App Secret | Secrets Manager | `${DomainSlug}/whatsapp/app-secret` | 90 dias |
| WhatsApp Verify Token | Secrets Manager | `${DomainSlug}/whatsapp/verify-token` | Manual |
| OAuth Client Secret (Gateway) | Secrets Manager | `${DomainSlug}/gateway/oauth-client-secret` | 90 dias |
| API Keys (tools externas) | Secrets Manager | `${DomainSlug}/tools/${tool-name}/api-key` | 90 dias |
| Bedrock Guardrail ID | SSM Parameter | `/${DomainSlug}/bedrock/guardrail-id` | N/A |
| Knowledge Base ID | SSM Parameter | `/${DomainSlug}/bedrock/kb-id` | N/A |
| AgentCore Memory ID | SSM Parameter | `/${DomainSlug}/agentcore/memory-id` | N/A |

### 2.3 Padrão de Acesso a Secrets (Python)

```python
import boto3
from functools import lru_cache

@lru_cache(maxsize=16)
def get_secret(secret_name: str, region: str = "us-east-1") -> str:
    """Obtém secret do Secrets Manager. Fail-fast se não encontrado."""
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return response["SecretString"]

# ❌ NUNCA FAZER
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "fallback_token")

# ✅ SEMPRE FAZER
WHATSAPP_TOKEN = get_secret(f"{domain_slug}/whatsapp/access-token")
```

### 2.4 Rotação Automática

```yaml
# CloudFormation — Rotação automática de secrets
WhatsAppSecretRotation:
  Type: AWS::SecretsManager::RotationSchedule
  Properties:
    SecretId: !Ref WhatsAppAccessTokenSecret
    RotationRules:
      AutomaticallyAfterDays: 90
```

### 2.5 Regras

- [ ] Nenhum secret em código-fonte, `.env` commitado, ou `domain.yaml`
- [ ] `.env.example` contém apenas placeholders: `WHATSAPP_TOKEN=<your-token-here>`
- [ ] `.gitignore` inclui `.env`, `*.pem`, `*.key`
- [ ] Secrets Manager com encryption via KMS CMK (não default key)
- [ ] Fail-fast se secret não pode ser obtido — **sem valores fallback**

---

## 3. Network Security

### 3.1 Arquitetura de Rede

```
┌─────────────────────────────────────────────────────────────┐
│  VPC (10.0.0.0/16)                                          │
│                                                             │
│  ┌─────────────────────┐  ┌──────────────────────────────┐  │
│  │  Public Subnet       │  │  Private Subnet              │  │
│  │  - NAT Gateway       │  │  - AgentCore Runtime (ECS)   │  │
│  │  - ALB (se aplicável)│  │  - VPC Endpoints             │  │
│  └─────────────────────┘  └──────────────────────────────┘  │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  VPC Endpoints (PrivateLink)                         │   │
│  │  - com.amazonaws.${Region}.bedrock-runtime           │   │
│  │  - com.amazonaws.${Region}.bedrock-agent-runtime     │   │
│  │  - com.amazonaws.${Region}.secretsmanager            │   │
│  │  - com.amazonaws.${Region}.dynamodb (Gateway)        │   │
│  │  - com.amazonaws.${Region}.logs (Interface)          │   │
│  │  - com.amazonaws.${Region}.ssm (Interface)           │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│  Lambda (WhatsApp)   │  ← Fora da VPC (latência) ou VPC com NAT
│  + API Gateway       │  ← WAF habilitado
└──────────────────────┘
```

### 3.2 Security Groups

**AgentCore Runtime SG:**

| Tipo | Protocolo | Porta | Origem | Descrição |
|------|-----------|-------|--------|-----------|
| Ingress | TCP | 8080 | Lambda SG / VPC CIDR | Invocações do runtime |
| Egress | TCP | 443 | VPC Endpoints SG | AWS APIs via PrivateLink |
| Egress | TCP | 443 | NAT Gateway | WhatsApp API (graph.facebook.com) |

**VPC Endpoints SG:**

| Tipo | Protocolo | Porta | Origem | Descrição |
|------|-----------|-------|--------|-----------|
| Ingress | TCP | 443 | AgentCore Runtime SG | Acesso aos endpoints |

```hcl
# Terraform — Security Group do AgentCore Runtime
resource "aws_security_group" "agentcore_runtime" {
  name_prefix = "${var.domain_slug}-runtime-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
    description     = "AgentCore invocations from Lambda"
  }

  egress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.vpc_endpoints.id]
    description     = "AWS APIs via PrivateLink"
  }

  # ❌ NUNCA: egress 0.0.0.0/0 all ports
}
```

### 3.3 WAF no API Gateway (WhatsApp Webhook)

```yaml
# CloudFormation — WAF para API Gateway
WebACL:
  Type: AWS::WAFv2::WebACL
  Properties:
    Scope: REGIONAL
    DefaultAction:
      Allow: {}
    Rules:
      - Name: RateLimitRule
        Priority: 1
        Action:
          Block: {}
        Statement:
          RateBasedStatement:
            Limit: 1000
            AggregateKeyType: IP
        VisibilityConfig:
          SampledRequestsEnabled: true
          CloudWatchMetricsEnabled: true
          MetricName: RateLimitMetric
      - Name: AWSManagedRulesCommonRuleSet
        Priority: 2
        OverrideAction:
          None: {}
        Statement:
          ManagedRuleGroupStatement:
            VendorName: AWS
            Name: AWSManagedRulesCommonRuleSet
        VisibilityConfig:
          SampledRequestsEnabled: true
          CloudWatchMetricsEnabled: true
          MetricName: CommonRuleSetMetric
```

### 3.4 Regras de Rede

- [ ] AgentCore Runtime em subnet privada — sem IP público
- [ ] VPC Endpoints para todos os serviços AWS consumidos (zero tráfego pela internet)
- [ ] Security Groups sem `0.0.0.0/0` em ingress (exceto ALB público se necessário)
- [ ] WAF no API Gateway do webhook com rate limiting por IP
- [ ] Lambda do WhatsApp: se em VPC, usar NAT Gateway para acessar WhatsApp API
- [ ] TLS 1.2+ em todas as comunicações

---

## 4. Data Protection & LGPD

> **Ref**: US-18 (Fix C6) — PII logado em texto claro identificado como 🔴 Critical.

### 4.1 Classificação de Dados

| Dado | Classificação | Tratamento |
|------|---------------|------------|
| CPF | PII Sensível | Mascarar em logs, criptografar at rest |
| Telefone (wa_id) | PII | Mascarar em logs, usar como user_id hasheado |
| Nome completo | PII | Mascarar em logs |
| Mensagens do usuário | PII Potencial | Não logar conteúdo completo |
| Respostas do agente | Dados internos | Não logar em produção |
| Session ID | Metadado | OK para logs |
| Model ID | Configuração | OK para logs |

### 4.2 PII Masking (Implementação)

```python
# src/utils/pii.py — Ref: design.md seção 4.9
import re
import logging

_PATTERNS = [
    # CPF: 123.456.789-00 → ***.***.***-00
    (re.compile(r"\b(\d{3})[.\s]?(\d{3})[.\s]?(\d{3})[-.\s]?(\d{2})\b"), r"***.***.***-\4"),
    # Telefone: +55 11 99999-9999 → ***-****-****
    (re.compile(r"\+?\d{1,3}[\s-]?\(?\d{2}\)?[\s-]?\d{4,5}[-.\s]?\d{4}"), "***-****-****"),
    # Email: user@domain.com → u***@domain.com
    (re.compile(r"\b([a-zA-Z])[a-zA-Z0-9._%+-]*@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b"), r"\1***@\2"),
]

class PIIMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = mask_pii(record.msg)
        return True

def mask_pii(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text
```

### 4.3 Encryption

| Camada | Mecanismo | Configuração |
|--------|-----------|--------------|
| At Rest — DynamoDB | AWS-owned key (padrão) ou KMS CMK | `SSESpecification: { SSEEnabled: true, SSEType: KMS }` |
| At Rest — S3 (KB) | SSE-KMS | `BucketEncryption: { ServerSideEncryptionByDefault: { SSEAlgorithm: aws:kms } }` |
| At Rest — Secrets Manager | KMS CMK | `KmsKeyId: !Ref SecretsKMSKey` |
| At Rest — AgentCore Memory | Gerenciado pelo serviço | Encryption habilitada por padrão |
| In Transit | TLS 1.2+ | Enforced em todos os endpoints |
| In Transit — VPC | PrivateLink | Tráfego nunca sai da rede AWS |

### 4.4 Bedrock Guardrails para PII

```python
# Configuração de Guardrails com filtro de PII
guardrail_config = {
    "sensitiveInformationPolicyConfig": {
        "piiEntitiesConfig": [
            {"type": "CPF", "action": "ANONYMIZE"},
            {"type": "PHONE", "action": "ANONYMIZE"},
            {"type": "NAME", "action": "ANONYMIZE"},
            {"type": "EMAIL", "action": "ANONYMIZE"},
            {"type": "ADDRESS", "action": "ANONYMIZE"},
        ]
    },
    "contentPolicyConfig": {
        "filtersConfig": [
            {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
            {"type": "INSULTS", "inputStrength": "HIGH", "outputStrength": "HIGH"},
        ]
    }
}
```

### 4.5 LGPD — Requisitos Específicos

- [ ] **Base legal**: Consentimento ou legítimo interesse documentado para cada dado coletado
- [ ] **Minimização**: Coletar apenas dados necessários para a funcionalidade
- [ ] **Retenção**: DynamoDB TTL para dados de dedup (24h). Memory com política de retenção configurável
- [ ] **Direito ao esquecimento**: Endpoint/processo para deletar dados do usuário no AgentCore Memory
- [ ] **Portabilidade**: Capacidade de exportar dados do usuário em formato legível
- [ ] **PII masking**: Aplicado em TODOS os logs antes de escrita no CloudWatch
- [ ] **Amazon Macie**: Habilitado em buckets S3 para detecção automática de PII

---

## 5. Webhook Security

> **Ref**: US-12 (Fix C7) — Webhook signature validation retorna `True` sempre, identificado como 🔴 Critical.

### 5.1 HMAC-SHA256 Validation (WhatsApp)

```python
# src/channels/whatsapp/signature.py — Ref: design.md seção 4.10
import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)

def validate_webhook_signature(
    payload_body: bytes,
    signature_header: str | None,
    app_secret: str,
) -> bool:
    """Valida X-Hub-Signature-256 do webhook Meta."""
    if not signature_header or not app_secret:
        logger.warning("Webhook rejected: missing signature or app_secret")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("Webhook rejected: invalid signature format")
        return False

    expected = signature_header[7:]
    computed = hmac.new(
        app_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, expected):
        logger.warning("Webhook rejected: HMAC mismatch")
        return False

    return True
```

### 5.2 Integração no Lambda Handler

```python
def lambda_handler(event, context):
    # 1. Validar signature ANTES de qualquer processamento
    body_raw = event.get("body", "").encode("utf-8")
    signature = event.get("headers", {}).get("x-hub-signature-256")
    app_secret = get_secret(f"{DOMAIN_SLUG}/whatsapp/app-secret")

    if not validate_webhook_signature(body_raw, signature, app_secret):
        return {"statusCode": 403, "body": "Forbidden"}

    # 2. Processar mensagem apenas se signature válida
    ...
```

### 5.3 Rate Limiting

| Camada | Mecanismo | Limite |
|--------|-----------|--------|
| WAF | Rate-based rule por IP | 1000 req/5min |
| API Gateway | Throttling | 100 req/s burst, 50 req/s sustained |
| Lambda | Reserved concurrency | 10-50 (ajustar por domínio) |
| Aplicação | DynamoDB dedup | 1 msg/message_id (idempotência) |

### 5.4 Proteções Adicionais

- [ ] Webhook verify token armazenado no Secrets Manager (não hardcoded)
- [ ] Rejeitar requests sem `X-Hub-Signature-256` com HTTP 403
- [ ] Logar tentativas de acesso inválidas (sem PII do payload)
- [ ] API Gateway com throttling configurado
- [ ] Lambda com reserved concurrency para evitar runaway costs
- [ ] DynamoDB TTL de 24h na tabela de dedup

---

## 6. Container Security

> **Ref**: US-14 — Dockerfile genérico ARM64 para AgentCore Runtime.

### 6.1 Dockerfile Hardened

```dockerfile
FROM --platform=linux/arm64 ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app

# Dependências primeiro (cache de layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-cache

COPY . .

# Usuário non-root (OBRIGATÓRIO)
RUN useradd -m -u 1000 -s /usr/sbin/nologin bedrock_agentcore
USER bedrock_agentcore

# Read-only filesystem (volumes para /tmp se necessário)
# Configurado no runtime: --read-only --tmpfs /tmp

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/ping')"

CMD ["opentelemetry-instrument", "python", "-m", "src.main"]
```

### 6.2 Regras de Container

- [ ] **Non-root**: Container executa como `bedrock_agentcore` (UID 1000), nunca como root
- [ ] **Read-only filesystem**: `--read-only` no runtime, com `tmpfs` para `/tmp` se necessário
- [ ] **No shell**: Imagem slim sem shell interativo em produção (considerar distroless para hardening extra)
- [ ] **Sem secrets no build**: Nenhum secret em `ENV`, `ARG`, ou layers da imagem
- [ ] **Multi-stage build**: Se necessário, usar multi-stage para reduzir superfície de ataque
- [ ] **Pinned base image**: Usar digest específico da imagem base, não apenas tag `latest`

### 6.3 Vulnerability Scanning

```yaml
# GitHub Actions — Scan de vulnerabilidades
- name: Trivy vulnerability scan
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.ECR_REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
    format: sarif
    severity: CRITICAL,HIGH
    exit-code: 1  # Falha o build se encontrar CRITICAL/HIGH

# ECR — Scan automático no push
ECRRepository:
  Type: AWS::ECR::Repository
  Properties:
    RepositoryName: !Sub "${DomainSlug}-agent"
    ImageScanningConfiguration:
      ScanOnPush: true
    ImageTagMutability: IMMUTABLE
    EncryptionConfiguration:
      EncryptionType: KMS
```

### 6.4 Runtime Security

| Controle | Configuração |
|----------|--------------|
| CPU/Memory limits | Definidos no ECS Task Definition |
| No privileged | `privileged: false` |
| No new privileges | `noNewPrivileges: true` |
| Drop capabilities | `drop: [ALL]` |
| Read-only root | `readOnlyRootFilesystem: true` |

---

## 7. Observability Security

> **Ref**: US-18 (Fix C6), US-21 — Nunca logar PII. Structured logging com campos mascarados.

### 7.1 O Que NUNCA Logar

| Dado | Nível | Ação |
|------|-------|------|
| CPF | ❌ Proibido | Mascarar: `***.***.***-XX` |
| Telefone completo | ❌ Proibido | Mascarar: `***-****-XXXX` |
| Nome completo | ❌ Proibido | Mascarar: `J***` |
| Mensagem do usuário (completa) | ❌ Proibido | Logar apenas tamanho e idioma detectado |
| Resposta do agente (completa) | ❌ Proibido | Logar apenas tamanho e agent_name |
| Tokens/secrets | ❌ Proibido | Nunca logar, nem parcialmente |
| System prompts | ❌ Proibido | Logar apenas hash/versão |

### 7.2 O Que Logar (Campos Seguros)

```json
{
  "timestamp": "2026-04-15T17:52:40.276Z",
  "level": "INFO",
  "logger": "src.agents.factory",
  "agent_name": "supervisor_agent",
  "session_id": "session-abc123",
  "request_id": "req-xyz789",
  "duration_ms": 2340,
  "tool_name": "services_assistant",
  "tool_success": true,
  "message_length": 142,
  "channel": "whatsapp"
}
```

### 7.3 Setup de Logging Seguro

```python
# src/utils/logging.py
import logging
import json
from src.utils.pii import PIIMaskingFilter

class JSONFormatter(logging.Formatter):
    def format(self, record):
        entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for f in ("agent_name", "session_id", "request_id", "duration_ms"):
            if hasattr(record, f):
                entry[f] = getattr(record, f)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    handler.addFilter(PIIMaskingFilter())
    logging.root.handlers = [handler]
    logging.root.setLevel(logging.INFO)
```

### 7.4 CloudWatch — Proteção de Logs

```yaml
# CloudFormation — Log group com encryption e retenção
AgentLogGroup:
  Type: AWS::Logs::LogGroup
  Properties:
    LogGroupName: !Sub "/agentcore/${DomainSlug}"
    RetentionInDays: 90
    KmsKeyId: !GetAtt LogsKMSKey.Arn

# Metric filter para alertas de segurança
WebhookRejectionFilter:
  Type: AWS::Logs::MetricFilter
  Properties:
    LogGroupName: !Ref AgentLogGroup
    FilterPattern: '"Webhook rejected"'
    MetricTransformations:
      - MetricName: WebhookRejections
        MetricNamespace: !Sub "${DomainSlug}/Security"
        MetricValue: "1"
```

### 7.5 Alertas de Segurança

| Alerta | Condição | Ação |
|--------|----------|------|
| Webhook rejections spike | > 10 rejeições em 5min | SNS → equipe de segurança |
| Auth failures | > 5 falhas de token em 1min | SNS → equipe de segurança |
| Error rate spike | > 20% de erros em 5min | SNS → equipe de operações |
| Lambda throttling | Throttles > 0 | SNS → equipe de operações |

---

## 8. IaC Security

> **Ref**: US-15 — Templates Terraform/CFN/CDK parametrizados e seguros.

### 8.1 Ferramentas de Validação

| Ferramenta | IaC | Comando | Quando |
|------------|-----|---------|--------|
| **checkov** | Terraform, CFN, CDK | `checkov -d infrastructure/` | CI + pre-commit |
| **cfn-nag** | CloudFormation | `cfn_nag_scan --input-path infrastructure/cloudformation/` | CI |
| **tfsec** | Terraform | `tfsec infrastructure/terraform/` | CI + pre-commit |
| **cdk-nag** | CDK | `Aspects.of(app).add(AwsSolutionsChecks())` | CDK synth |
| **pip-audit** | Python deps | `pip-audit -r requirements.txt` | CI semanal |
| **trivy** | Container + IaC | `trivy config infrastructure/` | CI |

### 8.2 CDK-Nag Integration

```python
# infrastructure/cdk/app.py
import cdk_nag
from aws_cdk import App, Aspects

app = App()
stack = ConversationalAgentsStack(app, "ConversationalAgents")

# Habilitar AwsSolutions checks
Aspects.of(app).add(cdk_nag.AwsSolutionsChecks(verbose=True))

# Suppressions explícitas (com justificativa documentada)
cdk_nag.NagSuppressions.add_stack_suppressions(stack, [
    cdk_nag.NagPackSuppression(
        id="AwsSolutions-IAM5",
        reason="Wildcard necessário apenas no suffix do ARN do runtime endpoint (blue-green)",
    ),
])

app.synth()
```

### 8.3 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/bridgecrewio/checkov
    rev: 3.2.0
    hooks:
      - id: checkov
        args: ["-d", "infrastructure/", "--quiet"]

  - repo: https://github.com/aquasecurity/tfsec
    rev: v1.28.0
    hooks:
      - id: tfsec
        args: ["infrastructure/terraform/"]

  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.5.0
    hooks:
      - id: detect-secrets
        args: ["--baseline", ".secrets.baseline"]
```

### 8.4 Regras de IaC

- [ ] **Zero hardcoded secrets** em templates — usar `!Ref`, `var.`, ou `ssm:` dynamic references
- [ ] **checkov/tfsec/cfn-nag** executados no CI — build falha se encontrar HIGH/CRITICAL
- [ ] **cdk-nag AwsSolutions** habilitado — suppressions requerem justificativa documentada
- [ ] **detect-secrets** no pre-commit — previne commit acidental de secrets
- [ ] **Removal policies**: `RETAIN` para dados de produção (DynamoDB, S3), `DESTROY` apenas em dev
- [ ] **Tags obrigatórias** em todos os recursos: `Project`, `Environment`, `ManagedBy`
- [ ] **pip-audit** semanal no CI para vulnerabilidades em dependências Python

### 8.5 Validação por Nível de Teste

| Nível | Validação de Segurança |
|-------|----------------------|
| **Nível 1 — Dev Local** | `checkov`, `tfsec`, `detect-secrets`, `cdk synth` + cdk-nag, `pip-audit` |
| **Nível 2 — Container Local** | Trivy scan na imagem, verificar non-root user, read-only fs |
| **Nível 3 — Staging AWS** | IAM Access Analyzer, Security Hub findings, GuardDuty alerts |

---

## 9. LLM/AI Security (OWASP LLM Top 10)

### 9.1 Prompt Injection (LLM01)

| Controle | Implementação |
|----------|---------------|
| Input sanitization | Pydantic validation em todos os inputs antes do LLM |
| System prompt isolation | System prompt via `SystemContentBlock` separado do user input |
| Bedrock Guardrails | Content filters habilitados (seção 4.4) |
| Canary tokens | Incluir token no system prompt para detectar leakage |

### 9.2 Output Handling (LLM02)

| Controle | Implementação |
|----------|---------------|
| Output como UNTRUSTED | Nunca executar output do LLM como código |
| Sanitização | PII masking na resposta antes de enviar ao usuário |
| Tool call validation | Argumentos de tool calls validados com Pydantic antes da execução |

### 9.3 Model DoS (LLM04)

| Controle | Implementação |
|----------|---------------|
| maxTokens | Configurado em toda invocação Bedrock |
| Rate limiting | WAF + API Gateway throttling + Lambda concurrency |
| Cost budgets | AWS Budgets com alertas em 80% e 100% do limite |
| Loop detection | `SlidingWindowConversationManager` com `window_size` limitado |

### 9.4 Supply Chain (LLM05)

| Controle | Implementação |
|----------|---------------|
| MCP servers auditados | Código-fonte revisado antes de registrar no Gateway |
| MCP permissions scoped | Cada GatewayTarget com permissões mínimas |
| Model versions pinned | Usar inference profile específico, nunca `latest` |
| Dependências auditadas | `pip-audit` semanal, Dependabot habilitado |

### 9.5 Insecure Tools (LLM07)

| Controle | Implementação |
|----------|---------------|
| Least privilege por tool | Cada tool com IAM role scoped ao recurso que acessa |
| Destructive tools | Requerem confirmação humana (human-in-the-loop) |
| Read-only default | Tools de consulta não devem ter permissão de escrita |
| Audit trail | Toda invocação de tool logada com nome, duração, sucesso/falha |

### 9.6 Excessive Agency (LLM08)

| Controle | Implementação |
|----------|---------------|
| Tool allowlist | Apenas tools registradas no `domain.yaml` e Gateway são acessíveis |
| Human-in-the-loop | Ações destrutivas (delete, transfer) requerem confirmação |
| Action logging | Todas as ações logadas com correlation ID |
| Kill switch | Capacidade de desabilitar agente via feature flag (SSM Parameter) |

---

## 10. Checklist de Compliance

### 10.1 Pré-Deploy (Gate de Segurança)

**IAM:**
- [ ] Nenhuma policy com `Resource: '*'`
- [ ] Nenhuma policy com `Action: '*'` ou `Action: 'service:*'`
- [ ] Todas as policies scoped com ARNs específicos
- [ ] Condition keys aplicadas (`aws:ResourceTag`, `aws:SourceArn`)
- [ ] Roles usados em vez de access keys
- [ ] Nenhuma inline policy (usar managed policies)

**Secrets:**
- [ ] Zero secrets em código-fonte (`detect-secrets` limpo)
- [ ] Todos os secrets no Secrets Manager ou SSM SecureString
- [ ] Rotação automática configurada (90 dias)
- [ ] `.env` no `.gitignore`
- [ ] Fail-fast se secret indisponível (sem fallback)

**Network:**
- [ ] AgentCore Runtime em subnet privada
- [ ] VPC Endpoints para serviços AWS
- [ ] Security Groups sem `0.0.0.0/0` em ingress
- [ ] WAF no API Gateway com rate limiting
- [ ] TLS 1.2+ em todas as comunicações

**Data:**
- [ ] Encryption at rest em DynamoDB, S3, Secrets Manager
- [ ] PII masking em todos os logs
- [ ] Bedrock Guardrails com filtro de PII habilitado
- [ ] DynamoDB TTL configurado (dedup table)
- [ ] Macie habilitado em buckets S3

**Container:**
- [ ] Non-root user no Dockerfile
- [ ] ECR scan on push habilitado
- [ ] Image tag immutability habilitada
- [ ] Trivy scan sem findings CRITICAL/HIGH
- [ ] Read-only root filesystem

**IaC:**
- [ ] checkov/tfsec/cfn-nag sem findings HIGH/CRITICAL
- [ ] cdk-nag AwsSolutions habilitado
- [ ] detect-secrets no pre-commit
- [ ] Tags obrigatórias em todos os recursos
- [ ] Removal policies explícitas

**LLM/AI:**
- [ ] Bedrock Guardrails configurados
- [ ] maxTokens definido em toda invocação
- [ ] Tool calls validados com Pydantic
- [ ] MCP servers auditados
- [ ] Model version pinned (não `latest`)

**Observability:**
- [ ] CloudTrail habilitado (all regions)
- [ ] GuardDuty habilitado
- [ ] Security Hub com CIS Benchmark
- [ ] Alertas de segurança configurados (webhook rejections, auth failures)
- [ ] Log groups com encryption KMS e retenção definida

### 10.2 Monitoramento Contínuo

| Serviço | Propósito | Frequência |
|---------|-----------|------------|
| GuardDuty | Detecção de ameaças | Contínuo |
| Security Hub | Postura de segurança | Contínuo |
| IAM Access Analyzer | Policies excessivas | Contínuo |
| Macie | PII em S3 | Diário |
| pip-audit | Vulnerabilidades em deps | Semanal |
| Trivy | Vulnerabilidades em container | A cada build |
| Config Rules | Compliance de recursos | Contínuo |

---

## Rastreabilidade: Critical Issues → Security Requirements

| Issue | Severidade | Seção | Status |
|-------|-----------|-------|--------|
| C1 — Race condition em estado global | 🔴 Critical | design.md §4.3 (SessionContext) | Endereçado |
| C2 — MCP Client resource leak | 🔴 Critical | design.md §4.5 (GatewayTokenManager) | Endereçado |
| C3 — Fallback silencioso para token inválido | 🔴 Critical | §2 Secrets Management | Endereçado |
| C4 — IAM Policy com `Resource: '*'` | 🔴 Critical | §1 IAM Least Privilege | Endereçado |
| C5 — Zero validação de input (CPF) | 🔴 Critical | design.md §4.8 (Validation) | Endereçado |
| C6 — PII logado em texto claro | 🔴 Critical | §4 Data Protection, §7 Observability | Endereçado |
| C7 — Webhook signature sempre `True` | 🔴 Critical | §5 Webhook Security | Endereçado |
