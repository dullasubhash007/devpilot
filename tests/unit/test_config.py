"""Unit tests for configuration loader (src/shared/config.py)."""
import pytest
from unittest.mock import patch, MagicMock

from src.config.defaults import DEFAULTS
from src.shared.config import load_config, _deep_merge


# ── _deep_merge ────────────────────────────────────────────────────────────────

def test_deep_merge_simple():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    override = {"b": {"c": 99}}
    result = _deep_merge(base, override)
    assert result["a"] == 1
    assert result["b"]["c"] == 99
    assert result["b"]["d"] == 3  # untouched


def test_deep_merge_new_key():
    base = {"a": 1}
    result = _deep_merge(base, {"b": 2})
    assert result["b"] == 2


def test_deep_merge_replaces_non_dict():
    base = {"a": {"nested": 1}}
    result = _deep_merge(base, {"a": "overridden"})
    assert result["a"] == "overridden"


# ── load_config ────────────────────────────────────────────────────────────────

@patch("src.shared.config._load_app_config", return_value={})
def test_load_config_defaults(mock_app_cfg):
    cfg = load_config()
    assert cfg["diagnose"]["model"] == DEFAULTS["diagnose"]["model"]
    assert cfg["predict"]["failure_threshold"] == DEFAULTS["predict"]["failure_threshold"]
    assert cfg["act"]["auto_create_issue"] is True


@patch("src.shared.config._load_app_config", return_value={})
def test_load_config_repo_yaml_override(mock_app_cfg):
    yaml = """
devpilot:
  diagnose:
    model: gpt-4o
    max_log_lines: 200
  predict:
    block_threshold: 80
"""
    cfg = load_config(yaml)
    assert cfg["diagnose"]["model"] == "gpt-4o"
    assert cfg["diagnose"]["max_log_lines"] == 200
    assert cfg["predict"]["block_threshold"] == 80
    # defaults still intact for untouched keys
    assert cfg["predict"]["failure_threshold"] == DEFAULTS["predict"]["failure_threshold"]


@patch("src.shared.config._load_app_config", return_value={})
def test_load_config_invalid_yaml_falls_back_to_defaults(mock_app_cfg):
    cfg = load_config("not: valid: yaml: {{{{")
    assert cfg["diagnose"]["model"] == DEFAULTS["diagnose"]["model"]


@patch("src.shared.config._load_app_config", return_value={})
def test_load_config_empty_devpilot_section(mock_app_cfg):
    cfg = load_config("devpilot: {}")
    assert cfg["diagnose"]["model"] == DEFAULTS["diagnose"]["model"]


@patch("src.shared.config._load_app_config", return_value={"diagnose": {"max_log_lines": 999}})
def test_load_config_app_config_overrides_defaults(mock_app_cfg):
    cfg = load_config()
    assert cfg["diagnose"]["max_log_lines"] == 999


@patch("src.shared.config._load_app_config", return_value={"diagnose": {"max_log_lines": 999}})
def test_load_config_repo_yaml_overrides_app_config(mock_app_cfg):
    cfg = load_config("devpilot:\n  diagnose:\n    max_log_lines: 100")
    assert cfg["diagnose"]["max_log_lines"] == 100
