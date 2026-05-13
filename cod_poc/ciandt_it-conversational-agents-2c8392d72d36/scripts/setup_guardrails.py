"""Provision Bedrock Guardrails with PII filters for LGPD compliance.

Usage: python scripts/setup_guardrails.py [--config config/domain.yaml]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_settings
from src.domain.loader import load_domain_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# PII types for LGPD — anonymize in both input and output
_PII_ENTITIES = [
    {"type": "CPF", "action": "ANONYMIZE"},
    {"type": "PHONE", "action": "ANONYMIZE"},
    {"type": "NAME", "action": "ANONYMIZE"},
    {"type": "EMAIL", "action": "ANONYMIZE"},
    {"type": "ADDRESS", "action": "ANONYMIZE"},
    {"type": "CREDIT_DEBIT_CARD_NUMBER", "action": "ANONYMIZE"},
]

_CONTENT_FILTERS = [
    {"type": "SEXUAL", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "VIOLENCE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "HATE", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "INSULTS", "inputStrength": "HIGH", "outputStrength": "HIGH"},
    {"type": "MISCONDUCT", "inputStrength": "HIGH", "outputStrength": "HIGH"},
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision Bedrock Guardrails")
    parser.add_argument("--config", default="config/domain.yaml")
    args = parser.parse_args()

    cfg = load_domain_config(args.config)
    settings = get_settings()

    client = boto3.client("bedrock", region_name=settings.AWS_REGION)

    name = f"{cfg.domain.slug}-guardrail"
    logger.info("Creating guardrail: %s", name)

    try:
        response = client.create_guardrail(
            name=name,
            description=f"PII protection + content filtering for {cfg.domain.name}",
            sensitiveInformationPolicyConfig={
                "piiEntitiesConfig": _PII_ENTITIES,
            },
            contentPolicyConfig={
                "filtersConfig": _CONTENT_FILTERS,
            },
            blockedInputMessaging="Your message was blocked for security reasons.",
            blockedOutputsMessaging="The response was blocked for security reasons.",
        )

        guardrail_id = response["guardrailId"]
        logger.info("Guardrail created: %s", guardrail_id)
        logger.info("")
        logger.info("Add to .env:")
        logger.info("  BEDROCK_GUARDRAIL_ID=%s", guardrail_id)

    except client.exceptions.ConflictException:
        logger.info("Guardrail '%s' already exists", name)
    except Exception as e:
        logger.error("Failed to create guardrail: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
