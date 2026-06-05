"""Configuration loader.

Resolution order:
  1. .devpilot.yml in the repository root (passed as raw YAML string)
  2. Azure App Configuration (global feature flags / defaults)
  3. Built-in hardcoded defaults in src/config/defaults.py

Usage::

    cfg = load_config(repo_yaml_content)
    max_lines = cfg["diagnose"]["max_log_lines"]
"""
import copy
import os
from typing import Any

import yaml
from azure.appconfiguration import AzureAppConfigurationClient

from .credential import get_credential
from .logging import get_logger
from src.config.defaults import DEFAULTS

logger = get_logger(__name__)

_SENTINEL = object()


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (base is mutated)."""
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val
    return base


def _load_app_config() -> dict:
    """Pull key-values prefixed with ``devpilot:`` from Azure App Configuration."""
    endpoint = os.getenv("AZURE_APP_CONFIG_ENDPOINT")
    if not endpoint:
        return {}

    try:
        client = AzureAppConfigurationClient(
            base_url=endpoint, credential=get_credential()
        )
        settings: dict[str, Any] = {}
        for item in client.list_configuration_settings(key_filter="devpilot:*"):
            # "devpilot:diagnose:max_log_lines" → nested dict
            parts = item.key.split(":")[1:]  # strip "devpilot" prefix
            node = settings
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            raw = item.value
            # coerce booleans / integers stored as strings
            if raw.lower() in ("true", "false"):
                node[parts[-1]] = raw.lower() == "true"
            elif raw.isdigit():
                node[parts[-1]] = int(raw)
            else:
                node[parts[-1]] = raw
        logger.debug("Loaded %d settings from App Configuration", len(settings))
        return settings
    except Exception as exc:
        logger.warning("Could not load App Configuration: %s", exc)
        return {}


def load_config(repo_yaml: str | None = None) -> dict:
    """Return merged configuration dict for a repository."""
    result = copy.deepcopy(DEFAULTS)

    # Layer 2: Azure App Configuration
    _deep_merge(result, _load_app_config())

    # Layer 1: .devpilot.yml
    if repo_yaml:
        try:
            repo_cfg = yaml.safe_load(repo_yaml) or {}
            devpilot_section = repo_cfg.get("devpilot", {})
            if devpilot_section:
                _deep_merge(result, devpilot_section)
        except yaml.YAMLError as exc:
            logger.warning("Failed to parse .devpilot.yml: %s", exc)

    return result
