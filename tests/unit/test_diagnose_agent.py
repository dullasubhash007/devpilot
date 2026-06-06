"""Unit tests for Diagnose agent formatting (src/agents/diagnose_agent/agent.py)."""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.agents.diagnose_agent.agent import format_pr_comment, Diagnosis


# ── format_pr_comment ─────────────────────────────────────────────────────────

def test_format_pr_comment_high_confidence():
    d: Diagnosis = {
        "root_cause": "Missing environment variable DATABASE_URL in production.",
        "fix_suggestion": "Add DATABASE_URL to the deployment secrets.",
        "file": "src/db.py",
        "line": 42,
        "confidence": "high",
    }
    comment = format_pr_comment(d, "https://github.com/org/repo/actions/runs/123")
    assert "🟢" in comment
    assert "DATABASE_URL" in comment
    assert "src/db.py:42" in comment
    assert "https://github.com/org/repo/actions/runs/123" in comment


def test_format_pr_comment_low_confidence():
    d: Diagnosis = {
        "root_cause": "Unknown error.",
        "fix_suggestion": "",
        "file": None,
        "line": None,
        "confidence": "low",
    }
    comment = format_pr_comment(d, "https://run.url")
    assert "🔴" in comment
    assert "No suggestion available" in comment
    # no file location block
    assert "📄" not in comment


def test_format_pr_comment_no_line_number():
    d: Diagnosis = {
        "root_cause": "Test failure.",
        "fix_suggestion": "Fix the test.",
        "file": "tests/test_foo.py",
        "line": None,
        "confidence": "medium",
    }
    comment = format_pr_comment(d, "https://run.url")
    assert "tests/test_foo.py" in comment
    # should not have colon if no line
    assert "tests/test_foo.py:" not in comment


def test_format_pr_comment_contains_ai_foundry_branding():
    d: Diagnosis = {
        "root_cause": "x", "fix_suggestion": "y",
        "file": None, "line": None, "confidence": "medium",
    }
    comment = format_pr_comment(d, "https://run.url")
    assert "Azure AI Foundry" in comment


# ── diagnose (mocked LLM) ─────────────────────────────────────────────────────

def test_diagnose_returns_structured_output():
    mock_response_json = json.dumps({
        "root_cause": "ImportError: cannot import name 'foo' from 'bar'",
        "fix_suggestion": "Update the import in main.py line 5.",
        "file": "main.py",
        "line": 5,
        "confidence": "high",
    })

    mock_choice = MagicMock()
    mock_choice.message.content = mock_response_json

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("src.agents.diagnose_agent.agent._get_client", return_value=(mock_client, "gpt-4o-mini")):
        from src.agents.diagnose_agent.agent import diagnose
        result = diagnose(logs="ERROR: ImportError", diff="- from bar import foo", model="gpt-4o-mini")

    assert result["root_cause"] == "ImportError: cannot import name 'foo' from 'bar'"
    assert result["file"] == "main.py"
    assert result["line"] == 5
    assert result["confidence"] == "high"


def test_diagnose_fallback_on_invalid_json():
    mock_choice = MagicMock()
    mock_choice.message.content = "not valid json {{{"

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with patch("src.agents.diagnose_agent.agent._get_client", return_value=(mock_client, "gpt-4o-mini")):
        from src.agents.diagnose_agent.agent import diagnose
        result = diagnose(logs="some logs", diff="some diff")

    assert "root_cause" in result
    assert result["confidence"] == "low"
