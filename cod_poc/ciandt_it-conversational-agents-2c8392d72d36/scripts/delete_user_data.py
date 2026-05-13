"""Delete user data from AgentCore Memory — LGPD right to erasure.

Usage: python scripts/delete_user_data.py --user-id <phone_or_id> [--memory-id <id>]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import boto3

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete user data (LGPD)")
    parser.add_argument("--user-id", required=True, help="User ID (phone number or identifier)")
    parser.add_argument("--memory-id", help="AgentCore Memory ID (overrides env var)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be deleted")
    args = parser.parse_args()

    settings = get_settings()
    memory_id = args.memory_id or settings.AGENTCORE_MEMORY_ID
    if not memory_id:
        logger.error("AGENTCORE_MEMORY_ID not set and --memory-id not provided")
        sys.exit(1)

    client = boto3.client("bedrock-agentcore", region_name=settings.AWS_REGION)
    namespaces = [
        f"/preferences/{args.user_id}/",
        f"/facts/{args.user_id}/",
        f"/summaries/{args.user_id}/",
    ]

    for ns in namespaces:
        if args.dry_run:
            logger.info("[DRY RUN] Would delete namespace: %s", ns)
            continue
        try:
            client.delete_memory_records(
                memoryId=memory_id,
                namespace=ns,
            )
            logger.info("Deleted namespace: %s", ns)
        except Exception as e:
            logger.warning("Failed to delete %s: %s", ns, e)

    if not args.dry_run:
        logger.info("User data deleted for: %s", args.user_id)
    else:
        logger.info("[DRY RUN] No data was deleted")


if __name__ == "__main__":
    main()
