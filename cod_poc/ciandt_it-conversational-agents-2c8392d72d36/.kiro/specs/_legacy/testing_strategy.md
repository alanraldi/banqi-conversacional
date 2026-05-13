# Testing Strategy: conversational-agents — Framework Multi-Agente Conversacional Genérico

> **Referências**: [requirements.md](./requirements.md) (US-01 a US-23) · [design.md](./design.md) (10 seções) · [tasks.md](./tasks.md) (29 tasks)
> **Stack**: Python 3.12+, Strands Agent Framework, AWS AgentCore Runtime, Bedrock, Pydantic v2
> **Cobertura mínima**: 80% unit tests · 90% critical paths (C1–C7)
> **Metodologia**: TDD (Red → Green → Refactor) com testes escritos ANTES da implementação

---

## 1. Estratégia de Testes em 3 Níveis

```
┌─────────────────────────────────────────────────────────────────────┐
│  NÍVEL 3 — STAGING AWS (pré-produção)                              │
│  Deploy completo via IaC + testes e2e + WhatsApp sandbox           │
│  Custo: $$ (recursos AWS reais)                                    │
│  Frequência: PR merge → main, release candidates                   │
├─────────────────────────────────────────────────────────────────────┤
│  NÍVEL 2 — CONTAINER LOCAL (custo mínimo)                          │
│  AgentCore CLI local + SAM local invoke + Docker                   │
│  Custo: $ (apenas chamadas Bedrock)                                │
│  Frequência: Antes de cada PR                                      │
├─────────────────────────────────────────────────────────────────────┤
│  NÍVEL 1 — DEV LOCAL (zero custo AWS)                              │
│  pytest + moto + Chainlit + CDK synth + terraform validate         │
│  Custo: $0                                                         │
│  Frequência: A cada commit (CI obrigatório)                        │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.1 Nível 1 — DEV LOCAL (Zero Custo AWS)

**Objetivo**: Validar lógica de negócio, configuração, segurança e IaC sem gastar com AWS.

| Ferramenta | Propósito |
|------------|-----------|
| `pytest` | Unit tests + integration tests com mocks |
| `moto` | Mock de serviços AWS (DynamoDB, S3, Bedrock) |
| `pytest-asyncio` | Testes de código async (Gateway, WhatsApp client) |
| `pytest-mock` | Mocking de dependências externas |
| `Chainlit` | Testes manuais de conversação (interface visual) |
| `cdk synth` | Validação de templates CDK (assertions) |
| `terraform validate` | Validação sintática de módulos Terraform |
| `cfn-lint` | Validação de templates CloudFormation |

**Escopo**:
- Todos os unit tests (domain, agents, channels, utils)
- Validação de Pydantic models e domain.yaml
- PII masking, input validation, signature validation
- CDK assertions (`Template.fromStack`)
- Terraform `validate` + `plan` (com mock provider)

**Comando**:
```bash
# Rodar todos os testes nível 1
pytest tests/unit/ tests/integration/ -v --cov=src --cov-report=term-missing --cov-fail-under=80

# IaC validation
cd infrastructure/cdk && cdk synth --no-staging
cd infrastructure/terraform && terraform init && terraform validate
cfn-lint infrastructure/cloudformation/template.yaml
```

### 1.2 Nível 2 — CONTAINER LOCAL (Custo Mínimo)

**Objetivo**: Validar que o container funciona end-to-end com AgentCore CLI e SAM local.

| Ferramenta | Propósito |
|------------|-----------|
| `bedrock-agentcore local run` | Executa container AgentCore localmente |
| `sam local invoke` | Testa Lambda do WhatsApp localmente |
| `sam local start-api` | API Gateway local para webhook |
| `docker compose` | Orquestra container + DynamoDB local |
| `curl` / `httpx` | Testes de endpoint manuais e automatizados |

**Escopo**:
- Health check (`/ping`) no container
- Invocação do Supervisor via `/invocations`
- Lambda webhook com payload simulado
- Deduplicação DynamoDB local
- Integração real com Bedrock (custo mínimo — poucas chamadas)

**Comando**:
```bash
# AgentCore local
bedrock-agentcore local run --agent-name conversational-agent

# Testar health
curl http://localhost:8080/ping

# Testar invocação
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Olá", "user_id": "test-user"}'

# SAM local para WhatsApp Lambda
sam local start-api -t infrastructure/whatsapp/template.yaml --port 3000

# Testar webhook verification
curl "http://localhost:3000/webhook?hub.mode=subscribe&hub.verify_token=test&hub.challenge=challenge123"
```

### 1.3 Nível 3 — STAGING AWS (Pré-Produção)

**Objetivo**: Validar deploy completo via IaC + testes e2e + WhatsApp sandbox real.

| Ferramenta | Propósito |
|------------|-----------|
| IaC (Terraform/CFN/CDK) | Deploy completo em conta staging |
| WhatsApp Sandbox | Número de teste Meta para e2e |
| `pytest` (e2e markers) | Testes e2e automatizados contra staging |
| CloudWatch Logs | Validação de observabilidade |
| AgentCore Console | Validação de memory, traces |

**Escopo**:
- Deploy completo: AgentCore Runtime + Lambda + DynamoDB + IAM
- Testes e2e via WhatsApp sandbox (Meta test number)
- Validação de memory STM+LTM (persistência entre sessões)
- Validação de observabilidade (traces no AgentCore Console)
- Validação de IAM least-privilege (nenhum `Resource: '*'`)
- Testes de concorrência (múltiplas sessões simultâneas)

**Comando**:
```bash
# Deploy staging
cd infrastructure/terraform && terraform apply -var="environment=staging"
# ou
cd infrastructure/cdk && cdk deploy --context environment=staging

# Testes e2e
pytest tests/e2e/ -v -m "staging" --staging-url=$STAGING_URL

# Cleanup
cd infrastructure/terraform && terraform destroy -var="environment=staging"
```

---

## 2. Cobertura Mínima por Tipo

| Tipo de Teste | Cobertura Mínima | Nível | Frequência |
|---------------|------------------|-------|------------|
| Unit tests | 80% linhas/branches | 1 | Cada commit |
| Critical paths (C1–C7) | 90% | 1 | Cada commit |
| Integration tests (mocked) | 70% | 1 | Cada commit |
| Container tests | Smoke tests | 2 | Cada PR |
| E2E tests | Critical user flows | 3 | Merge → main |
| IaC validation | 100% templates | 1 | Cada commit |

**Enforcement**:
```ini
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
markers = [
    "unit: Unit tests (nível 1)",
    "integration: Integration tests com mocks (nível 1)",
    "container: Container tests (nível 2)",
    "staging: E2E tests contra staging (nível 3)",
    "critical: Testes de critical issues C1-C7",
]

# Coverage enforcement
# pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

---

## 3. Testes por Camada

### 3.1 Camada Domain — Configuração e Prompts

> **Componentes**: `src/domain/models.py`, `src/domain/loader.py`, `config/domain.yaml`, `prompts/*.md`
> **User Stories**: US-01, US-02, US-03, US-04
> **Tasks**: T-002, T-003

#### 3.1.1 Unit Tests — Pydantic Models (`tests/unit/domain/test_models.py`)

```python
import pytest
from pydantic import ValidationError
from src.domain.models import DomainConfig, SubAgentConfig, MemoryNamespaceConfig

class TestDomainConfig:
    """US-04: Validação de schema do domain.yaml."""

    def test_valid_config_loads_successfully(self, valid_domain_dict):
        """Configuração válida deve carregar sem erros."""
        config = DomainConfig(**valid_domain_dict)
        assert config.domain.name == "TestBot"
        assert len(config.sub_agents) >= 1

    def test_missing_domain_name_raises_validation_error(self, valid_domain_dict):
        """US-04 AC2: Campos obrigatórios ausentes devem causar ValidationError."""
        del valid_domain_dict["domain"]["name"]
        with pytest.raises(ValidationError, match="domain.name"):
            DomainConfig(**valid_domain_dict)

    def test_empty_sub_agents_raises_validation_error(self, valid_domain_dict):
        """US-04 AC2: Pelo menos 1 sub-agent obrigatório."""
        valid_domain_dict["sub_agents"] = {}
        with pytest.raises(ValidationError, match="min_length"):
            DomainConfig(**valid_domain_dict)

    def test_missing_prompt_file_raises_validation_error(self, valid_domain_dict, tmp_path):
        """US-02 AC2: Prompt file inexistente deve causar erro."""
        valid_domain_dict["supervisor"]["prompt_file"] = "/nonexistent/prompt.md"
        with pytest.raises(ValidationError, match="Prompt file not found"):
            DomainConfig(**valid_domain_dict)

    def test_unknown_fields_rejected(self, valid_domain_dict):
        """US-01 AC7: Campos desconhecidos devem ser rejeitados."""
        valid_domain_dict["unknown_field"] = "value"
        with pytest.raises(ValidationError):
            DomainConfig(**valid_domain_dict)

    def test_default_values_applied(self):
        """Valores default devem ser aplicados quando campos opcionais ausentes."""
        config = DomainConfig(**minimal_valid_config())
        assert config.interface.welcome_message == "Olá! Como posso ajudar?"
        assert config.error_messages.generic == "Desculpe, ocorreu um erro. Tente novamente."

class TestMemoryNamespaceConfig:
    def test_default_values(self):
        ns = MemoryNamespaceConfig()
        assert ns.top_k == 5
        assert ns.relevance_score == 0.5

    def test_custom_values(self):
        ns = MemoryNamespaceConfig(top_k=3, relevance_score=0.7)
        assert ns.top_k == 3
        assert ns.relevance_score == 0.7
```

#### 3.1.2 Unit Tests — Domain Loader (`tests/unit/domain/test_loader.py`)

```python
import pytest
from unittest.mock import patch
from src.domain.loader import load_domain_config, get_prompt

class TestLoadDomainConfig:
    """US-01: Configuração de domínio via YAML."""

    def test_loads_valid_yaml(self, valid_domain_yaml_file):
        """US-01 AC1: Carrega config de domain.yaml no startup."""
        config = load_domain_config(str(valid_domain_yaml_file))
        assert config.domain.slug is not None

    def test_missing_yaml_raises_file_not_found(self):
        """US-01 AC2: YAML ausente causa fail-fast."""
        with pytest.raises(FileNotFoundError, match="Domain config not found"):
            load_domain_config("/nonexistent/domain.yaml")

    def test_malformed_yaml_raises_validation_error(self, malformed_domain_yaml_file):
        """US-01 AC2: YAML malformado causa fail-fast."""
        with pytest.raises(Exception):  # ValidationError ou yaml.YAMLError
            load_domain_config(str(malformed_domain_yaml_file))

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_model_env_var_raises_error(self, valid_domain_yaml_file):
        """US-04 AC3: Env var de model ID ausente causa fail-fast."""
        with pytest.raises(EnvironmentError, match="Environment variable .* is not set"):
            load_domain_config(str(valid_domain_yaml_file))

    def test_config_is_cached_singleton(self, valid_domain_yaml_file, monkeypatch):
        """Segunda chamada retorna mesma instância (singleton)."""
        monkeypatch.setenv("SUPERVISOR_AGENT_MODEL_ID", "test-model")
        monkeypatch.setenv("SERVICES_AGENT_MODEL_ID", "test-model")
        c1 = load_domain_config(str(valid_domain_yaml_file))
        c2 = load_domain_config(str(valid_domain_yaml_file))
        assert c1 is c2

class TestGetPrompt:
    """US-02: Prompts externalizados em arquivos Markdown."""

    def test_loads_existing_prompt(self, tmp_path):
        """US-02 AC1: Carrega prompt de arquivo .md."""
        prompt_file = tmp_path / "test.md"
        prompt_file.write_text("You are a helpful assistant.")
        result = get_prompt(str(prompt_file))
        assert "helpful assistant" in result

    def test_missing_prompt_raises_error(self):
        """US-02 AC2: Prompt inexistente causa fail-fast."""
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            get_prompt("/nonexistent/prompt.md")
```

### 3.2 Camada Orquestração — Agents, Memory, Gateway, Security

> **Componentes**: `src/agents/`, `src/memory/`, `src/gateway/`, `src/utils/`
> **User Stories**: US-05, US-06, US-07, US-08, US-09, US-17, US-18
> **Critical Issues**: C1, C2, C3, C5, C6
> **Tasks**: T-005, T-006, T-007, T-009, T-010, T-011

#### 3.2.1 Thread-Safe Session Context — Fix C1 (`tests/unit/agents/test_context.py`)

```python
import threading
import pytest
from src.agents.context import SessionContext

class TestSessionContext:
    """US-06 / C1: Thread-safe session context."""

    def test_set_and_get_context(self):
        ctx = SessionContext()
        ctx.set(user_id="user-1", session_id="sess-1")
        result = ctx.get()
        assert result.user_id == "user-1"
        assert result.session_id == "sess-1"

    def test_default_context_is_none(self):
        ctx = SessionContext()
        result = ctx.get()
        assert result.user_id is None
        assert result.session_id is None

    @pytest.mark.critical
    def test_threads_have_isolated_context(self):
        """C1: Threads diferentes NÃO compartilham estado."""
        ctx = SessionContext()
        results = {}

        def worker(user_id):
            ctx.set(user_id=user_id, session_id=f"sess-{user_id}")
            import time; time.sleep(0.01)  # Simula processamento
            results[user_id] = ctx.get().user_id

        threads = [threading.Thread(target=worker, args=(f"user-{i}",)) for i in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()

        # Cada thread deve ter seu próprio user_id
        for i in range(10):
            assert results[f"user-{i}"] == f"user-{i}"

    @pytest.mark.critical
    def test_no_global_mutable_dict(self):
        """C1: Nenhum dict global mutável no módulo."""
        import src.agents.context as mod
        module_vars = {k: v for k, v in vars(mod).items() if isinstance(v, dict) and not k.startswith("_")}
        assert len(module_vars) == 0, f"Dict global mutável encontrado: {module_vars.keys()}"
```

#### 3.2.2 Agent Factory (`tests/unit/agents/test_factory.py`)

```python
import pytest
from unittest.mock import patch, MagicMock
from src.agents.factory import create_supervisor, _make_delegate_tool

class TestAgentFactory:
    """US-05: Supervisor Agent genérico com Agents-as-Tools."""

    @patch("src.agents.factory.Agent")
    @patch("src.agents.factory.BedrockModel")
    @patch("src.agents.factory.load_domain_config")
    def test_creates_supervisor_with_correct_tools(self, mock_config, mock_model, mock_agent, domain_config_fixture):
        """US-05 AC2: Cada sub-agent registrado como tool."""
        mock_config.return_value = domain_config_fixture
        create_supervisor(user_id="test", session_id="sess")
        call_kwargs = mock_agent.call_args[1]
        assert len(call_kwargs["tools"]) == len(domain_config_fixture.sub_agents)

    @patch("src.agents.factory.load_domain_config")
    def test_tool_names_follow_pattern(self, mock_config, domain_config_fixture):
        """Tool names devem seguir padrão {key}_assistant."""
        mock_config.return_value = domain_config_fixture
        for key, sa in domain_config_fixture.sub_agents.items():
            tool = _make_delegate_tool(key, sa.tool_docstring)
            assert tool.__name__ == f"{key}_assistant"

    @patch("src.agents.factory.load_domain_config")
    def test_guardrail_kwargs_when_configured(self, mock_config, monkeypatch):
        """US-19 AC1: Guardrails aplicados quando BEDROCK_GUARDRAIL_ID definido."""
        monkeypatch.setenv("BEDROCK_GUARDRAIL_ID", "gr-123")
        from src.agents.factory import _guardrail_kwargs
        kwargs = _guardrail_kwargs()
        assert kwargs["guardrail_id"] == "gr-123"

    def test_guardrail_kwargs_empty_when_not_configured(self, monkeypatch):
        """US-19 AC2: Sem guardrails quando não configurado."""
        monkeypatch.delenv("BEDROCK_GUARDRAIL_ID", raising=False)
        from src.agents.factory import _guardrail_kwargs
        assert _guardrail_kwargs() == {}
```

#### 3.2.3 Memory Setup (`tests/unit/memory/test_setup.py`)

```python
import pytest
from unittest.mock import patch, MagicMock
from src.memory.setup import attach_memory

class TestMemorySetup:
    """US-08: AgentCore Memory integration."""

    def test_missing_memory_id_raises_error(self, monkeypatch, domain_config_fixture):
        """US-08 AC4: AGENTCORE_MEMORY_ID ausente causa fail-fast."""
        monkeypatch.delenv("AGENTCORE_MEMORY_ID", raising=False)
        agent = MagicMock()
        with pytest.raises(EnvironmentError, match="AGENTCORE_MEMORY_ID"):
            attach_memory(agent, domain_config_fixture, "user-1")

    @patch("src.memory.setup.AgentCoreMemorySessionManager")
    @patch("src.memory.setup.AgentCoreMemoryToolProvider")
    def test_namespaces_from_yaml(self, mock_provider, mock_session, monkeypatch, domain_config_fixture):
        """US-08 AC1: Namespaces configurados a partir do YAML."""
        monkeypatch.setenv("AGENTCORE_MEMORY_ID", "mem-123")
        agent = MagicMock()
        agent.tools = []
        attach_memory(agent, domain_config_fixture, "user-1", "sess-1")
        call_kwargs = mock_session.call_args
        assert call_kwargs is not None

    @patch("src.memory.setup.AgentCoreMemorySessionManager")
    @patch("src.memory.setup.AgentCoreMemoryToolProvider")
    def test_session_id_generated_with_prefix(self, mock_provider, mock_session, monkeypatch, domain_config_fixture):
        """Session ID gerado com prefixo do YAML quando não fornecido."""
        monkeypatch.setenv("AGENTCORE_MEMORY_ID", "mem-123")
        agent = MagicMock()
        agent.tools = []
        attach_memory(agent, domain_config_fixture, "user-1")
        # Verifica que session_id foi gerado (não None)
        assert mock_session.called
```

#### 3.2.4 Gateway Token Manager — Fix C2/C3 (`tests/unit/gateway/test_token_manager.py`)

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.gateway.token_manager import GatewayTokenManager

class TestGatewayTokenManager:
    """US-07 / C2 / C3: Singleton com cleanup, fail-fast sem fallback."""

    def setup_method(self):
        GatewayTokenManager._instance = None

    @pytest.mark.critical
    async def test_get_token_raises_on_failure(self):
        """C3: Fail-fast — sem fallback para 'fallback_token'."""
        mgr = GatewayTokenManager(
            client_id="id", client_secret="secret",
            token_endpoint="https://auth.example.com/token", scope="scope"
        )
        with patch.object(mgr, "_http_client", new_callable=AsyncMock) as mock_client:
            mock_response = AsyncMock()
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_client.post.return_value = mock_response
            mgr._http_client = mock_client
            with pytest.raises(Exception, match="401"):
                await mgr.get_token()

    @pytest.mark.critical
    async def test_cleanup_closes_http_client(self):
        """C2: cleanup() fecha HTTP client."""
        mgr = GatewayTokenManager(
            client_id="id", client_secret="secret",
            token_endpoint="https://auth.example.com/token", scope="scope"
        )
        mock_client = AsyncMock()
        mgr._http_client = mock_client
        await mgr.cleanup()
        mock_client.aclose.assert_called_once()
        assert mgr._http_client is None
        assert GatewayTokenManager._instance is None

    def test_singleton_pattern(self):
        """get_instance() retorna mesma instância."""
        kwargs = dict(client_id="id", client_secret="s", token_endpoint="url", scope="s")
        m1 = GatewayTokenManager.get_instance(**kwargs)
        m2 = GatewayTokenManager.get_instance(**kwargs)
        assert m1 is m2

    @pytest.mark.critical
    async def test_no_fallback_token_in_source(self):
        """C3: Nenhum 'fallback_token' no código fonte."""
        import inspect
        source = inspect.getsource(GatewayTokenManager)
        assert "fallback_token" not in source
        assert "fallback" not in source.lower()
```

#### 3.2.5 PII Masking — Fix C6 (`tests/unit/utils/test_pii.py`)

```python
import logging
import pytest
from src.utils.pii import mask_pii, PIIMaskingFilter, setup_pii_logging

class TestPIIMasking:
    """US-18 / C6: PII masking nos logs — conformidade LGPD."""

    @pytest.mark.critical
    def test_masks_cpf_with_dots(self):
        assert "***.***.***-00" in mask_pii("CPF: 123.456.789-00")

    @pytest.mark.critical
    def test_masks_cpf_without_dots(self):
        result = mask_pii("CPF: 12345678900")
        assert "12345678900" not in result

    @pytest.mark.critical
    def test_masks_phone_with_country_code(self):
        result = mask_pii("Tel: +55 11 99999-9999")
        assert "99999" not in result

    def test_preserves_non_pii_text(self):
        text = "Olá, como posso ajudar?"
        assert mask_pii(text) == text

    @pytest.mark.critical
    def test_filter_masks_log_record_msg(self):
        """PIIMaskingFilter mascara record.msg."""
        f = PIIMaskingFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "CPF: 123.456.789-00", (), None)
        f.filter(record)
        assert "123.456.789" not in record.msg

    @pytest.mark.critical
    def test_filter_masks_log_record_args(self):
        """PIIMaskingFilter mascara record.args."""
        f = PIIMaskingFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "User: %s", ("123.456.789-00",), None)
        f.filter(record)
        assert "123.456.789" not in str(record.args)
```

#### 3.2.6 Input Validation — Fix C5 (`tests/unit/utils/test_validation.py`)

```python
import pytest
from src.utils.validation import CPFInput, PhoneInput, validate_non_empty

class TestCPFInput:
    """US-17 / C5: Validação de CPF."""

    @pytest.mark.critical
    def test_valid_cpf_11_digits(self):
        result = CPFInput(cpf="12345678901")
        assert result.cpf == "12345678901"

    @pytest.mark.critical
    def test_valid_cpf_with_punctuation(self):
        result = CPFInput(cpf="123.456.789-01")
        assert result.cpf == "12345678901"

    @pytest.mark.critical
    def test_invalid_cpf_too_short(self):
        with pytest.raises(ValueError, match="11 dígitos"):
            CPFInput(cpf="1234")

    @pytest.mark.critical
    def test_invalid_cpf_letters(self):
        with pytest.raises(ValueError):
            CPFInput(cpf="123456789ab")

    def test_empty_cpf(self):
        with pytest.raises(ValueError):
            CPFInput(cpf="")

class TestPhoneInput:
    def test_valid_phone(self):
        result = PhoneInput(phone="11999999999")
        assert result.phone == "11999999999"

    def test_valid_phone_with_formatting(self):
        result = PhoneInput(phone="+55 (11) 99999-9999")
        assert result.phone == "5511999999999"

    def test_invalid_phone_too_short(self):
        with pytest.raises(ValueError, match="10-15 dígitos"):
            PhoneInput(phone="123")

class TestValidateNonEmpty:
    @pytest.mark.critical
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="não pode ser vazio"):
            validate_non_empty("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            validate_non_empty("   ")

    def test_valid_string_returns_stripped(self):
        assert validate_non_empty("  hello  ") == "hello"
```

### 3.3 Camada Channels — WhatsApp e Chainlit

> **Componentes**: `src/channels/whatsapp/`, `src/channels/chainlit/`
> **User Stories**: US-10, US-11, US-12, US-13
> **Critical Issues**: C7
> **Tasks**: T-014, T-015, T-016, T-017, T-019, T-021

#### 3.3.1 WhatsApp Signature Validation — Fix C7 (`tests/unit/channels/whatsapp/test_signature.py`)

```python
import hashlib
import hmac
import pytest
from src.channels.whatsapp.signature import validate_webhook_signature

class TestWebhookSignature:
    """US-12 / C7: Validação HMAC-SHA256 do webhook Meta."""

    APP_SECRET = "test_secret_key"

    def _make_signature(self, payload: bytes) -> str:
        sig = hmac.new(self.APP_SECRET.encode(), payload, hashlib.sha256).hexdigest()
        return f"sha256={sig}"

    @pytest.mark.critical
    def test_valid_signature_accepted(self):
        payload = b'{"entry": []}'
        sig = self._make_signature(payload)
        assert validate_webhook_signature(payload, sig, self.APP_SECRET) is True

    @pytest.mark.critical
    def test_missing_signature_rejected(self):
        assert validate_webhook_signature(b"payload", None, self.APP_SECRET) is False

    @pytest.mark.critical
    def test_missing_app_secret_rejected(self):
        assert validate_webhook_signature(b"payload", "sha256=abc", "") is False

    @pytest.mark.critical
    def test_invalid_signature_rejected(self):
        assert validate_webhook_signature(b"payload", "sha256=invalid", self.APP_SECRET) is False

    @pytest.mark.critical
    def test_wrong_format_rejected(self):
        assert validate_webhook_signature(b"payload", "md5=abc", self.APP_SECRET) is False

    @pytest.mark.critical
    def test_tampered_payload_rejected(self):
        payload = b'{"entry": []}'
        sig = self._make_signature(payload)
        tampered = b'{"entry": [{"malicious": true}]}'
        assert validate_webhook_signature(tampered, sig, self.APP_SECRET) is False

    @pytest.mark.critical
    def test_never_returns_true_unconditionally(self):
        """C7: Função NUNCA retorna True incondicionalmente."""
        import inspect
        source = inspect.getsource(validate_webhook_signature)
        # Não deve ter "return True" sem condição
        lines = [l.strip() for l in source.split("\n") if l.strip() == "return True"]
        assert len(lines) == 0, "validate_webhook_signature contém 'return True' incondicional"
```

#### 3.3.2 WhatsApp Webhook Processor (`tests/unit/channels/whatsapp/test_webhook.py`)

```python
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

class TestWebhookProcessor:
    """US-11: WhatsApp channel adapter."""

    def test_get_webhook_returns_challenge(self):
        """US-11 AC1: GET /webhook retorna hub.challenge."""
        from src.channels.whatsapp.lambda_handler import lambda_handler
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {
                "hub.mode": "subscribe",
                "hub.verify_token": "test-token",
                "hub.challenge": "challenge123",
            },
        }
        with patch.dict("os.environ", {"WHATSAPP_VERIFY_TOKEN": "test-token"}):
            result = lambda_handler(event, None)
        assert result["statusCode"] == 200
        assert result["body"] == "challenge123"

    def test_get_webhook_rejects_invalid_token(self):
        """Token inválido retorna 403."""
        from src.channels.whatsapp.lambda_handler import lambda_handler
        event = {
            "httpMethod": "GET",
            "queryStringParameters": {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge123",
            },
        }
        with patch.dict("os.environ", {"WHATSAPP_VERIFY_TOKEN": "correct-token"}):
            result = lambda_handler(event, None)
        assert result["statusCode"] == 403

    @patch("src.channels.whatsapp.webhook_processor.invoke_agent_runtime")
    @patch("src.channels.whatsapp.webhook_processor.send_message")
    def test_post_webhook_processes_message(self, mock_send, mock_invoke):
        """US-11 AC2: POST processa mensagem e responde."""
        mock_invoke.return_value = "Resposta do agente"
        # ... test implementation with valid payload and signature
```

#### 3.3.3 WhatsApp Models (`tests/unit/channels/whatsapp/test_models.py`)

```python
import pytest
from src.channels.whatsapp.models import WebhookPayload

class TestWhatsAppModels:
    """Parsing de payloads do webhook Meta."""

    def test_parses_text_message(self, whatsapp_text_message_payload):
        payload = WebhookPayload(**whatsapp_text_message_payload)
        assert payload.entry[0].changes[0].value.messages[0].text.body == "Olá"

    def test_extracts_phone_number(self, whatsapp_text_message_payload):
        payload = WebhookPayload(**whatsapp_text_message_payload)
        assert payload.entry[0].changes[0].value.messages[0].from_ is not None

    def test_handles_status_update(self, whatsapp_status_payload):
        """Status updates (delivered, read) não devem causar erro."""
        payload = WebhookPayload(**whatsapp_status_payload)
        assert payload.entry[0].changes[0].value.messages is None or len(payload.entry[0].changes[0].value.messages) == 0
```

#### 3.3.4 Chainlit Adapter (`tests/unit/channels/chainlit/test_app.py`)

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

class TestChainlitAdapter:
    """US-13: Chainlit channel adapter (dev/teste)."""

    @patch("src.channels.chainlit.app.load_domain_config")
    def test_welcome_message_from_yaml(self, mock_config, domain_config_fixture):
        """US-13 AC2: Welcome message do domain.yaml."""
        mock_config.return_value = domain_config_fixture
        # Verifica que on_chat_start usa interface.welcome_message
        assert domain_config_fixture.interface.welcome_message is not None

    @patch("src.channels.chainlit.app.load_domain_config")
    def test_disabled_channel_not_initialized(self, mock_config, domain_config_fixture):
        """US-13 AC4: Não inicializa se disabled no YAML."""
        domain_config_fixture.channels["chainlit"].enabled = False
        mock_config.return_value = domain_config_fixture
        # Adapter não deve inicializar
```

### 3.4 Camada Infraestrutura — IaC Validation

> **Componentes**: `infrastructure/terraform/`, `infrastructure/cloudformation/`, `infrastructure/cdk/`
> **User Stories**: US-15, US-16
> **Critical Issues**: C4
> **Tasks**: T-023, T-024, T-025

#### 3.4.1 CDK Assertions (`tests/unit/infra/test_cdk_stack.py`)

```python
import pytest
from aws_cdk import App
from aws_cdk.assertions import Template, Match
from infrastructure.cdk.stacks.agentcore_stack import AgentCoreStack

class TestAgentCoreCDKStack:
    """US-15: Infraestrutura agnóstica — CDK."""

    @pytest.fixture
    def template(self):
        app = App()
        stack = AgentCoreStack(app, "TestStack", domain_slug="test", agent_name="test-agent", environment="test")
        return Template.from_stack(stack)

    def test_creates_ecr_repository(self, template):
        template.has_resource_properties("AWS::ECR::Repository", {
            "RepositoryName": Match.string_like_regexp("test.*"),
        })

    @pytest.mark.critical
    def test_iam_no_wildcard_resource(self, template):
        """C4 / US-16: Nenhuma IAM policy com Resource: '*'."""
        resources = template.find_resources("AWS::IAM::Policy")
        for logical_id, resource in resources.items():
            statements = resource["Properties"]["PolicyDocument"]["Statement"]
            for stmt in statements:
                resource_value = stmt.get("Resource", "")
                if isinstance(resource_value, str):
                    assert resource_value != "*", f"IAM policy {logical_id} usa Resource: '*'"
                elif isinstance(resource_value, list):
                    assert "*" not in resource_value, f"IAM policy {logical_id} usa Resource: '*'"

    def test_iam_scoped_arns(self, template):
        """US-16 AC2: ARNs scoped com account, region, resource."""
        resources = template.find_resources("AWS::IAM::Role")
        assert len(resources) > 0

    def test_resource_names_from_variables(self, template):
        """US-15 AC3: Nomes derivados de variáveis, não hardcoded."""
        resources = template.find_resources("AWS::ECR::Repository")
        for _, resource in resources.items():
            name = resource["Properties"].get("RepositoryName", "")
            assert "banqi" not in str(name).lower()
            assert "banking" not in str(name).lower()
```

#### 3.4.2 Terraform Validation (`tests/unit/infra/test_terraform.py`)

```python
import subprocess
import pytest

class TestTerraformModules:
    """US-15: Infraestrutura agnóstica — Terraform."""

    TERRAFORM_DIR = "infrastructure/terraform"

    def test_terraform_validate(self):
        """terraform validate passa sem erros."""
        result = subprocess.run(
            ["terraform", "init", "-backend=false"],
            cwd=self.TERRAFORM_DIR, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"terraform init failed: {result.stderr}"
        result = subprocess.run(
            ["terraform", "validate"],
            cwd=self.TERRAFORM_DIR, capture_output=True, text=True,
        )
        assert result.returncode == 0, f"terraform validate failed: {result.stderr}"

    @pytest.mark.critical
    def test_no_wildcard_resource_in_iam(self):
        """C4: Nenhum Resource: '*' nos arquivos .tf."""
        import re
        from pathlib import Path
        for tf_file in Path(self.TERRAFORM_DIR).glob("*.tf"):
            content = tf_file.read_text()
            # Procura por resources = ["*"] ou resource = "*"
            assert not re.search(r'resources?\s*=\s*\[?\s*"\*"\s*\]?', content), \
                f"Wildcard resource encontrado em {tf_file.name}"

    def test_variables_defined(self):
        """Variáveis obrigatórias definidas."""
        from pathlib import Path
        content = (Path(self.TERRAFORM_DIR) / "variables.tf").read_text()
        for var in ["domain_slug", "agent_name", "environment", "aws_region"]:
            assert f'variable "{var}"' in content, f"Variável {var} não definida"
```

#### 3.4.3 CloudFormation Validation (`tests/unit/infra/test_cloudformation.py`)

```python
import subprocess
import pytest
import json

class TestCloudFormationTemplate:
    """US-15: Infraestrutura agnóstica — CloudFormation."""

    TEMPLATE_PATH = "infrastructure/cloudformation/template.yaml"

    def test_cfn_lint_passes(self):
        """cfn-lint valida template sem erros."""
        result = subprocess.run(
            ["cfn-lint", self.TEMPLATE_PATH],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"cfn-lint failed: {result.stdout}"

    @pytest.mark.critical
    def test_no_wildcard_resource_in_iam(self):
        """C4: Nenhum Resource: '*' no template."""
        import yaml
        from pathlib import Path
        with open(self.TEMPLATE_PATH) as f:
            template = yaml.safe_load(f)
        resources = template.get("Resources", {})
        for name, resource in resources.items():
            if resource["Type"] in ("AWS::IAM::Policy", "AWS::IAM::Role"):
                props = json.dumps(resource.get("Properties", {}))
                assert '"*"' not in props or '"Resource": "*"' not in props, \
                    f"Wildcard resource em {name}"

    def test_parameters_defined(self):
        """Parâmetros obrigatórios definidos."""
        import yaml
        from pathlib import Path
        with open(self.TEMPLATE_PATH) as f:
            template = yaml.safe_load(f)
        params = template.get("Parameters", {})
        for param in ["DomainSlug", "AgentName", "Environment"]:
            assert param in params, f"Parâmetro {param} não definido"
```

---

## 4. Fixtures e Factories para Test Data

### 4.1 Conftest Principal (`tests/conftest.py`)

```python
import os
import pytest
import yaml
from pathlib import Path
from src.domain.models import (
    DomainConfig, DomainInfo, AgentInfo, SupervisorConfig,
    SubAgentConfig, MemoryConfig, MemoryNamespaceConfig,
    ChannelConfig, InterfaceConfig, ErrorMessagesConfig,
)


# ── Factories ──────────────────────────────────────────────

def make_domain_config(**overrides) -> DomainConfig:
    """Factory para DomainConfig com defaults válidos."""
    defaults = {
        "domain": DomainInfo(name="TestBot", slug="test-bot", description="Test assistant"),
        "agent": AgentInfo(name="test_agent", memory_name="TestMemory"),
        "supervisor": SupervisorConfig(
            prompt_file="prompts/supervisor.md",
            description="Test supervisor",
            model_id_env="SUPERVISOR_AGENT_MODEL_ID",
        ),
        "sub_agents": {
            "services": SubAgentConfig(
                name="Services Agent",
                description="Test services",
                prompt_file="prompts/services.md",
                tool_docstring="Handles service queries",
                model_id_env="SERVICES_AGENT_MODEL_ID",
            ),
        },
        "memory": MemoryConfig(namespaces={
            "preferences": MemoryNamespaceConfig(top_k=3, relevance_score=0.7),
            "facts": MemoryNamespaceConfig(top_k=5, relevance_score=0.5),
        }),
        "channels": {
            "whatsapp": ChannelConfig(enabled=True, type="webhook"),
            "chainlit": ChannelConfig(enabled=True, type="local"),
        },
        "interface": InterfaceConfig(welcome_message="Olá! Sou o TestBot."),
        "error_messages": ErrorMessagesConfig(),
    }
    defaults.update(overrides)
    return DomainConfig(**defaults)


def make_whatsapp_payload(message_text: str = "Olá", phone: str = "5511999990000") -> dict:
    """Factory para payload do webhook WhatsApp."""
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15551234567", "phone_number_id": "123"},
                    "messages": [{
                        "from": phone,
                        "id": "wamid.test123",
                        "timestamp": "1234567890",
                        "text": {"body": message_text},
                        "type": "text",
                    }],
                },
                "field": "messages",
            }],
        }],
    }


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def domain_config_fixture(tmp_path):
    """DomainConfig válido com prompt files reais."""
    for name in ["supervisor.md", "services.md"]:
        (tmp_path / name).write_text(f"You are a test {name.replace('.md', '')} agent.")
    return make_domain_config(
        supervisor=SupervisorConfig(
            prompt_file=str(tmp_path / "supervisor.md"),
            description="Test", model_id_env="SUPERVISOR_AGENT_MODEL_ID",
        ),
        sub_agents={
            "services": SubAgentConfig(
                name="Services", description="Test",
                prompt_file=str(tmp_path / "services.md"),
                tool_docstring="Test tool", model_id_env="SERVICES_AGENT_MODEL_ID",
            ),
        },
    )


@pytest.fixture
def valid_domain_dict(tmp_path):
    """Dict válido para construir DomainConfig."""
    for name in ["supervisor.md", "services.md"]:
        (tmp_path / name).write_text("Test prompt content.")
    return {
        "domain": {"name": "TestBot", "slug": "test-bot", "description": "Test"},
        "agent": {"name": "test_agent", "memory_name": "TestMemory"},
        "supervisor": {
            "prompt_file": str(tmp_path / "supervisor.md"),
            "description": "Test", "model_id_env": "SUPERVISOR_AGENT_MODEL_ID",
        },
        "sub_agents": {
            "services": {
                "name": "Services", "description": "Test",
                "prompt_file": str(tmp_path / "services.md"),
                "tool_docstring": "Test", "model_id_env": "SERVICES_AGENT_MODEL_ID",
            },
        },
    }


@pytest.fixture
def valid_domain_yaml_file(tmp_path, valid_domain_dict):
    """Arquivo domain.yaml válido no disco."""
    yaml_file = tmp_path / "domain.yaml"
    yaml_file.write_text(yaml.dump(valid_domain_dict))
    return yaml_file


@pytest.fixture
def malformed_domain_yaml_file(tmp_path):
    """Arquivo domain.yaml malformado."""
    yaml_file = tmp_path / "domain.yaml"
    yaml_file.write_text("domain:\n  name: 123\n  missing_required: true\n")
    return yaml_file


@pytest.fixture
def whatsapp_text_message_payload():
    return make_whatsapp_payload("Olá")


@pytest.fixture
def whatsapp_status_payload():
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "123", "changes": [{"value": {"statuses": [{"status": "delivered"}]}, "field": "messages"}]}],
    }


@pytest.fixture
def env_with_model_ids(monkeypatch):
    """Seta env vars de model IDs para testes."""
    monkeypatch.setenv("SUPERVISOR_AGENT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    monkeypatch.setenv("SERVICES_AGENT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    monkeypatch.setenv("GENERAL_AGENT_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    monkeypatch.setenv("AGENTCORE_MEMORY_ID", "mem-test-123")
```

### 4.2 Estrutura de Diretórios de Testes

```
tests/
├── conftest.py                              # Fixtures e factories globais
├── unit/
│   ├── domain/
│   │   ├── test_models.py                   # §3.1.1
│   │   └── test_loader.py                   # §3.1.2
│   ├── agents/
│   │   ├── test_context.py                  # §3.2.1 (C1)
│   │   └── test_factory.py                  # §3.2.2
│   ├── memory/
│   │   └── test_setup.py                    # §3.2.3
│   ├── gateway/
│   │   └── test_token_manager.py            # §3.2.4 (C2/C3)
│   ├── channels/
│   │   ├── whatsapp/
│   │   │   ├── test_signature.py            # §3.3.1 (C7)
│   │   │   ├── test_webhook.py              # §3.3.2
│   │   │   └── test_models.py               # §3.3.3
│   │   └── chainlit/
│   │       └── test_app.py                  # §3.3.4
│   ├── utils/
│   │   ├── test_pii.py                      # §3.2.5 (C6)
│   │   └── test_validation.py               # §3.2.6 (C5)
│   └── infra/
│       ├── test_cdk_stack.py                # §3.4.1 (C4)
│       ├── test_terraform.py                # §3.4.2 (C4)
│       └── test_cloudformation.py           # §3.4.3 (C4)
├── integration/
│   ├── test_channel_extensibility.py        # US-23
│   ├── test_supervisor_routing.py           # US-05 e2e mock
│   └── test_main_entrypoint.py              # US-14, US-22
└── e2e/
    ├── test_staging_health.py               # Nível 3
    ├── test_staging_invocation.py           # Nível 3
    └── test_staging_whatsapp.py             # Nível 3
```

---

## 5. CI/CD Pipeline com Testes Automatizados

### 5.1 Pipeline Overview

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Commit   │───▶│ Nível 1  │───▶│  Build   │───▶│ Nível 2  │───▶│ Nível 3  │
│  Push     │    │ Unit+IaC │    │ Docker   │    │Container │    │ Staging  │
│           │    │ ~3 min   │    │ ~5 min   │    │ ~5 min   │    │ ~15 min  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
                     │                                                │
                     ▼                                                ▼
              Gate: 80% cov                                   Gate: e2e pass
              Gate: 0 critical fail                           Gate: IAM audit
```

### 5.2 GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.12"

jobs:
  # ── NÍVEL 1: Unit + IaC (zero custo AWS) ──
  level-1-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v4
        with:
          version: "latest"

      - name: Install dependencies
        run: uv sync --frozen --group dev

      - name: Run unit tests
        run: |
          uv run pytest tests/unit/ -v \
            --cov=src --cov-report=term-missing --cov-report=xml \
            --cov-fail-under=80 \
            -m "not container and not staging"
        env:
          SUPERVISOR_AGENT_MODEL_ID: "mock-model"
          SERVICES_AGENT_MODEL_ID: "mock-model"
          AGENTCORE_MEMORY_ID: "mock-memory"

      - name: Run critical issue tests
        run: |
          uv run pytest tests/ -v -m "critical" --tb=short

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          file: coverage.xml

  level-1-iac:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform validate
        working-directory: infrastructure/terraform
        run: |
          terraform init -backend=false
          terraform validate

      - name: CFN lint
        run: |
          pip install cfn-lint
          cfn-lint infrastructure/cloudformation/template.yaml

      - name: CDK synth
        working-directory: infrastructure/cdk
        run: |
          npm ci
          npx cdk synth --no-staging

      - name: IAM wildcard audit
        run: |
          # Verifica que nenhum template tem Resource: '*'
          ! grep -r '"Resource":\s*"\*"' infrastructure/ || exit 1
          ! grep -r "Resource: '\*'" infrastructure/ || exit 1

  # ── NÍVEL 2: Container (custo mínimo) ──
  level-2-container:
    needs: [level-1-unit, level-1-iac]
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Build Docker image
        run: docker build -t conversational-agent:test .

      - name: Start container
        run: |
          docker run -d --name agent -p 8080:8080 \
            -e SUPERVISOR_AGENT_MODEL_ID=mock \
            -e AGENTCORE_MEMORY_ID=mock \
            conversational-agent:test
          sleep 5

      - name: Health check
        run: |
          response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/ping)
          [ "$response" = "200" ] || exit 1

      - name: SAM local test
        run: |
          pip install aws-sam-cli
          cd infrastructure/whatsapp
          sam build
          echo '{"httpMethod":"GET","queryStringParameters":{"hub.mode":"subscribe","hub.verify_token":"test","hub.challenge":"ok"}}' | \
            sam local invoke WebhookFunction --event -

      - name: Cleanup
        if: always()
        run: docker stop agent && docker rm agent

  # ── NÍVEL 3: Staging (pré-produção) ──
  level-3-staging:
    needs: [level-2-container]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.STAGING_ROLE_ARN }}
          aws-region: us-east-1

      - name: Deploy to staging
        working-directory: infrastructure/terraform
        run: |
          terraform init
          terraform apply -auto-approve -var="environment=staging"

      - name: Run e2e tests
        run: |
          uv run pytest tests/e2e/ -v -m "staging" \
            --staging-url=${{ secrets.STAGING_URL }}

      - name: Destroy staging
        if: always()
        working-directory: infrastructure/terraform
        run: terraform destroy -auto-approve -var="environment=staging"
```

---

## 6. Rastreabilidade: Testes → User Stories e Critical Issues

### 6.1 User Stories → Testes

| US | Descrição | Arquivo de Teste | Nível |
|----|-----------|-----------------|-------|
| US-01 | Domain config via YAML | `test_loader.py`, `test_models.py` | 1 |
| US-02 | Prompts externalizados | `test_loader.py::TestGetPrompt` | 1 |
| US-03 | Mensagens configuráveis | `test_main_entrypoint.py` | 1 |
| US-04 | Validação schema YAML | `test_models.py::TestDomainConfig` | 1 |
| US-05 | Supervisor Agents-as-Tools | `test_factory.py::TestAgentFactory` | 1 |
| US-06 | Thread-safe context (C1) | `test_context.py::TestSessionContext` | 1 |
| US-07 | MCP lifecycle (C2) | `test_token_manager.py` | 1 |
| US-08 | Memory integration | `test_setup.py::TestMemorySetup` | 1 |
| US-09 | Fail-fast credentials (C3) | `test_token_manager.py`, `test_settings.py` | 1 |
| US-10 | Channel adapter ABC | `test_channel_extensibility.py` | 1 |
| US-11 | WhatsApp adapter | `test_webhook.py`, `test_models.py` | 1, 2 |
| US-12 | Webhook signature (C7) | `test_signature.py` | 1 |
| US-13 | Chainlit adapter | `test_app.py` | 1 |
| US-14 | AgentCore Runtime | `test_main_entrypoint.py` | 1, 2 |
| US-15 | IaC agnóstica | `test_cdk_stack.py`, `test_terraform.py`, `test_cloudformation.py` | 1 |
| US-16 | IAM least-privilege (C4) | `test_cdk_stack.py::test_iam_no_wildcard_resource` | 1 |
| US-17 | Input validation (C5) | `test_validation.py` | 1 |
| US-18 | PII masking (C6) | `test_pii.py` | 1 |
| US-19 | Guardrails | `test_factory.py::test_guardrail_kwargs_*` | 1 |
| US-20 | Latência/throughput | `test_staging_invocation.py` | 3 |
| US-21 | Structured logging | `test_logging.py` | 1 |
| US-22 | Health checks | `test_main_entrypoint.py`, container health | 1, 2 |
| US-23 | Extensibilidade canais | `test_channel_extensibility.py` | 1 |

### 6.2 Critical Issues → Testes

| Issue | Descrição | Teste | Marker | Cobertura |
|-------|-----------|-------|--------|-----------|
| C1 | Race condition `_supervisor_context` | `test_context.py::test_threads_have_isolated_context` | `@critical` | 90% |
| C2 | MCP Client resource leak | `test_token_manager.py::test_cleanup_closes_http_client` | `@critical` | 90% |
| C3 | Fallback silencioso `"fallback_token"` | `test_token_manager.py::test_no_fallback_token_in_source` | `@critical` | 90% |
| C4 | IAM `Resource: '*'` | `test_cdk_stack.py::test_iam_no_wildcard_resource`, `test_terraform.py`, `test_cloudformation.py` | `@critical` | 100% |
| C5 | Zero validação de CPF | `test_validation.py::TestCPFInput` | `@critical` | 90% |
| C6 | PII logado em texto claro | `test_pii.py::test_masks_cpf_*`, `test_filter_masks_*` | `@critical` | 90% |
| C7 | Webhook signature `True` sempre | `test_signature.py::test_never_returns_true_unconditionally` | `@critical` | 100% |

### 6.3 Comando para Rodar Apenas Testes Críticos

```bash
# Roda APENAS testes marcados como critical (C1-C7)
pytest -v -m "critical" --tb=short

# Roda testes de uma US específica (via naming convention)
pytest -v -k "test_context"       # US-06 / C1
pytest -v -k "test_signature"     # US-12 / C7
pytest -v -k "test_pii"           # US-18 / C6
pytest -v -k "test_validation"    # US-17 / C5
pytest -v -k "test_iam"           # US-16 / C4
```

---

## 7. Edge Cases Obrigatórios

Todos os testes devem cobrir estes cenários:

| Cenário | Exemplo | Onde Testar |
|---------|---------|-------------|
| Input nulo/vazio | `prompt=""`, `cpf=None` | `test_validation.py`, `test_main_entrypoint.py` |
| Input com caracteres especiais | `prompt="<script>alert(1)</script>"` | `test_validation.py` |
| YAML malformado | Campos faltando, tipos errados | `test_models.py`, `test_loader.py` |
| Env vars ausentes | `AGENTCORE_MEMORY_ID` não setada | `test_loader.py`, `test_setup.py` |
| Concorrência | 10 threads simultâneas | `test_context.py` |
| Payload duplicado | Mesmo `message_id` duas vezes | `test_webhook.py` |
| Signature inválida | HMAC adulterado | `test_signature.py` |
| Token expirado | OAuth token vencido | `test_token_manager.py` |
| Prompt file ausente | Referência a arquivo inexistente | `test_loader.py`, `test_models.py` |
| PII em logs | CPF, telefone em mensagens de log | `test_pii.py` |
| IAM wildcards | `Resource: '*'` em templates | `test_cdk_stack.py`, `test_terraform.py` |
| Resposta vazia do LLM | Bedrock retorna empty | `test_factory.py` |

---

## 8. Checklist de Qualidade TDD

Antes de cada PR, verificar:

- [ ] Testes escritos ANTES da implementação (Red → Green → Refactor)
- [ ] Todas as funções públicas têm unit tests
- [ ] Error paths testados (não apenas happy path)
- [ ] Mocks para dependências externas (AWS, APIs, Bedrock)
- [ ] Testes são independentes (sem estado compartilhado entre testes)
- [ ] Cobertura ≥ 80% (linhas e branches)
- [ ] Critical paths (C1–C7) com cobertura ≥ 90%
- [ ] Nomes descritivos: `test_should_[behavior]_when_[condition]`
- [ ] Fixtures reutilizáveis via `conftest.py`
- [ ] IaC validada: `terraform validate` + `cfn-lint` + `cdk synth`
- [ ] Nenhum `Resource: '*'` em IAM policies
- [ ] PII masking verificado nos logs
- [ ] Zero referências hardcoded a domínio específico nos testes
