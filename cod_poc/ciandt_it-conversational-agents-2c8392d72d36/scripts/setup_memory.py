"""Provision AgentCore Memory with namespaces from domain.yaml.

Usage: python scripts/setup_memory.py [--config config/domain.yaml]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import boto3

# Ensure project root in path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_settings
from src.domain.loader import load_domain_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision AgentCore Memory")
    parser.add_argument("--config", default="config/domain.yaml")
    args = parser.parse_args()

    cfg = load_domain_config(args.config)
    settings = get_settings()

    client = boto3.client("bedrock-agentcore", region_name=settings.AWS_REGION)

    memory_name = cfg.agent.memory_name
    logger.info("Creating memory: %s", memory_name)

    try:
        response = client.create_memory(
            name=memory_name,
            description=f"Memory for {cfg.domain.name} multi-agent system",
            memoryStrategies=[
                {
                    "semanticMemoryStrategy": {
                        "model": "anthropic.claude-sonnet-4-6-v1:0",
                        "name": "semantic",
                        "description": "Semantic memory extraction",
                    }
                },
                {
                    "summaryMemoryStrategy": {
                        "model": "anthropic.claude-sonnet-4-6-v1:0",
                        "name": "summary",
                        "description": "Conversation summaries",
                    }
                },
                {
                    "userPreferenceMemoryStrategy": {
                        "model": "anthropic.claude-sonnet-4-6-v1:0",
                        "name": "preferences",
                        "description": "User preferences extraction",
                    }
                },
            ],
        )

        memory_id = response["memoryId"]
        logger.info("Memory created: %s", memory_id)
        logger.info("Namespaces from domain.yaml: %s", list(cfg.memory.namespaces.keys()))
        logger.info("")
        logger.info("Add to .env:")
        logger.info("  AGENTCORE_MEMORY_ID=%s", memory_id)

    except client.exceptions.ConflictException:
        logger.info("Memory '%s' already exists", memory_name)
    except Exception as e:
        logger.error("Failed to create memory: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
