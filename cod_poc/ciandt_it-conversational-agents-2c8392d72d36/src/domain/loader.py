"""Domain configuration loader — singleton, fail-fast, thread-safe."""

from __future__ import annotations

import os
import threading
from pathlib import Path

import yaml

from src.domain.schema import DomainConfig

_config: DomainConfig | None = None
_domain_dir: Path | None = None
_lock = threading.Lock()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_domain_dir() -> Path:
    """Resolve the active domain directory.

    Resolution order:
    1. DOMAIN_DIR env var (absolute or relative to PROJECT_ROOT)
    2. Default: domains/banqi-banking
    """
    global _domain_dir
    if _domain_dir is not None:
        return _domain_dir

    raw = os.environ.get("DOMAIN_DIR", "domains/banqi-banking")
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    _domain_dir = path
    return _domain_dir


def load_domain_config(config_path: str | None = None) -> DomainConfig:
    """Load and validate domain.yaml. Fail-fast on invalid config or missing env vars.

    Args:
        config_path: Explicit path to domain.yaml (for tests). If None, uses domain dir.

    Uses double-check locking for thread-safe singleton.
    Returns cached instance on subsequent calls.
    """
    global _config
    if _config is not None:
        return _config

    with _lock:
        if _config is not None:
            return _config

        if config_path:
            path = Path(config_path) if Path(config_path).is_absolute() else PROJECT_ROOT / config_path
        else:
            path = get_domain_dir() / "domain.yaml"

        if not path.exists():
            raise FileNotFoundError(f"Domain config not found: {path}")

        with open(path) as f:
            raw = yaml.safe_load(f)

        config = DomainConfig(**raw)
        _validate_model_env_vars(config)
        _config = config
        return _config


def _validate_model_env_vars(config: DomainConfig) -> None:
    """Fail-fast if required model ID env vars are missing."""
    missing: list[str] = []

    if not os.getenv(config.supervisor.model_id_env):
        missing.append(f"{config.supervisor.model_id_env} (Supervisor)")

    for _key, agent_cfg in config.sub_agents.items():
        if not os.getenv(agent_cfg.model_id_env):
            missing.append(f"{agent_cfg.model_id_env} ({agent_cfg.name})")

    if missing:
        raise OSError(f"Missing required environment variables: {', '.join(missing)}")


def get_prompt(prompt_file: str) -> str:
    """Load prompt from .md file relative to domain dir. Fail-fast if not found."""
    path = get_domain_dir() / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def reset_config() -> None:
    """Reset cached config and domain dir — for testing only."""
    global _config, _domain_dir
    _config = None
    _domain_dir = None
