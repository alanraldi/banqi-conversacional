"""Secret retrieval — dev: env var / prod: Secrets Manager.

Cached per secret name. Fail-fast without fallback values.
Path convention: ${domain_slug}/<service>/<secret-name>
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

import boto3

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_secret(name: str) -> str:
    """Get secret value — env var first, then Secrets Manager.

    Args:
        name: Env var name (dev) or Secrets Manager secret ID (prod).

    Returns:
        Secret value.

    Raises:
        RuntimeError: If secret cannot be retrieved.
    """
    # Dev: env var takes precedence
    val = os.getenv(name)
    if val:
        return val

    # Prod: Secrets Manager
    try:
        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=name)
        return response["SecretString"]
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve secret '{name}': {e}") from e
