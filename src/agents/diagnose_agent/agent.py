"""Diagnose Agent — root cause analysis via Azure AI Foundry (GPT-4o-mini).

Given workflow failure logs and the PR diff, returns a structured diagnosis:
    {
        "root_cause": str,
        "fix_suggestion": str,
        "file": str | None,
        "line": int | None,
        "confidence": "high" | "medium" | "low"
    }
"""
import json
import os
from typing import TypedDict

from openai import AzureOpenAI

from src.shared.logging import get_logger
from src.shared.credential import get_credential

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are DevPilot Diagnose, an expert CI/CD failure analyst.
You receive GitHub Actions workflow failure logs and a pull-request diff.
Your job is to identify the root cause and suggest a concrete fix.

Respond ONLY with valid JSON matching this schema (no markdown fences):
{
  "root_cause": "<one clear sentence>",
  "fix_suggestion": "<actionable fix description>",
  "file": "<relative file path or null>",
  "line": <line number as integer or null>,
  "confidence": "high" | "medium" | "low"
}"""


class Diagnosis(TypedDict):
    root_cause: str
    fix_suggestion: str
    file: str | None
    line: int | None
    confidence: str


def _get_client(model: str) -> tuple[AzureOpenAI, str]:
    endpoint = os.environ["AI_FOUNDRY_ENDPOINT"]
    # AzureOpenAI SDK works against AI Foundry AI Services endpoints
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=lambda: get_credential().get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-08-01-preview",
    )
    return client, model


def diagnose(
    logs: str,
    diff: str,
    model: str = "gpt-4o-mini",
    max_log_lines: int = 500,
    include_fix: bool = True,
) -> Diagnosis:
    """Run root-cause analysis and return a structured Diagnosis."""
    # Trim logs to budget
    log_lines = logs.splitlines()
    if len(log_lines) > max_log_lines:
        log_lines = log_lines[-max_log_lines:]
    trimmed_logs = "\n".join(log_lines)

    user_content = f"## Failure Logs\n```\n{trimmed_logs}\n```\n\n## PR Diff\n```diff\n{diff}\n```"
    if not include_fix:
        user_content += "\n\nNote: omit fix_suggestion (set to empty string)."

    client, deployment = _get_client(model)

    logger.info("Calling AI Foundry (model=%s) for diagnosis", deployment)
    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content
    try:
        result: Diagnosis = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Could not parse LLM JSON response, returning fallback")
        result = Diagnosis(
            root_cause="Unable to determine root cause automatically.",
            fix_suggestion="Please review the failure logs manually.",
            file=None,
            line=None,
            confidence="low",
        )
    logger.info("Diagnosis complete — confidence=%s", result.get("confidence"))
    return result


def format_pr_comment(diagnosis: Diagnosis, run_url: str) -> str:
    """Render the diagnosis as a GitHub-flavoured markdown PR comment."""
    confidence_emoji = {"high": "🟢", "medium": "🟡", "low": "🔴"}.get(
        diagnosis.get("confidence", "low"), "🔴"
    )
    file_info = ""
    if diagnosis.get("file"):
        loc = diagnosis["file"]
        if diagnosis.get("line"):
            loc += f":{diagnosis['line']}"
        file_info = f"\n\n> 📄 **Location**: `{loc}`"

    return f"""## 🔍 DevPilot Diagnosis {confidence_emoji}

**Root Cause**
{diagnosis['root_cause']}

**Suggested Fix**
{diagnosis.get('fix_suggestion') or '_No suggestion available._'}{file_info}

<sub>Powered by Azure AI Foundry · [View run]({run_url})</sub>"""
