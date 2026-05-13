"""Setup script — gera .bedrock_agentcore.yaml a partir do domain.yaml.

Uso: python scripts/setup.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

# Adiciona raiz do projeto ao path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from src.domain.loader import PROJECT_ROOT, load_domain_config


def generate_agentcore_yaml() -> None:
    """Lê domain.yaml e gera .bedrock_agentcore.yaml na raiz do projeto."""
    cfg = load_domain_config()

    agent_name = cfg.agent.name
    memory_name = cfg.agent.memory_name

    agentcore_config: dict = {
        "default_agent": agent_name,
        "agents": {
            agent_name: {
                "name": agent_name,
                "entrypoint": "src/main.py",
                "platform": "linux/arm64",
                "container_runtime": "docker",
                "aws": {
                    "region": "${AWS_REGION}",
                    "network_configuration": {
                        "network_mode": "PUBLIC",
                    },
                    "protocol_configuration": {
                        "server_protocol": "HTTP",
                    },
                    "observability": {
                        "enabled": True,
                    },
                },
                "memory": {
                    "mode": "STM_AND_LTM",
                    "memory_name": memory_name,
                },
            },
        },
    }

    output_path = PROJECT_ROOT / ".bedrock_agentcore.yaml"
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(agentcore_config, f, default_flow_style=False, sort_keys=False)

    print(f"Generated: {output_path}")
    print(f"  agent: {agent_name}")
    print(f"  memory: {memory_name}")


if __name__ == "__main__":
    generate_agentcore_yaml()
