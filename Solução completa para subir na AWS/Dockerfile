FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOMAIN_SLUG=banqi-consignado

# Instalar dependências primeiro (cache de layer Docker)
COPY pyproject.toml uv.lock* ./
RUN uv pip install . && \
    uv pip install aws-opentelemetry-distro>=0.10.1

# Copiar código da aplicação
COPY src/ src/
COPY domains/ domains/

# Usuário não-root (requisito AgentCore)
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/ping')"]

# OpenTelemetry auto-instrumentation + entrypoint AgentCore
CMD ["opentelemetry-instrument", "python", "-m", "src.main"]
