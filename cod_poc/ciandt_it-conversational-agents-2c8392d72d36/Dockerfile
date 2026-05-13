FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOMAIN_DIR=domains/banqi-banking

# Install deps into system Python (no venv)
COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY domains/ domains/
RUN uv pip install . && \
    uv pip install aws-opentelemetry-distro>=0.10.1

# Copy remaining files
COPY . .

# Non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/ping')"]

CMD ["opentelemetry-instrument", "python", "-m", "src.main"]
