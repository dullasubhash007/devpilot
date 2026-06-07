"""Act Agent - autonomous actions via Azure AI Foundry.

Given the Predict score and Diagnose output, the Act agent decides:
  - Whether to create a GitHub Issue with the diagnosis
  - Whether to recommend a deploy strategy (rolling / canary / blue-green)
  - Whether to adjust quality gates (only when auto_adjust_gates=True)
"""
import json
import os
from dataclasses import dataclass, field

from openai import AzureOpenAI

from src.shared.credential import get_credential
from src.shared.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ActInput:
    owner: str
    repo: str
    pr_number: int
    installation_id: int
    run_id: int
    predict_score: int
    predict_label: str
    diagnosis: dict
    config: dict
    head_sha: str = ""
    run_url: str = ""


@dataclass
class ActOutput:
    issue_url: str | None = None
    deploy_strategy: str | None = None
    gate_adjusted: bool = False
    actions_taken: list[str] = field(default_factory=list)
    reasoning: str = ""


DECISION_PROMPT = """You are DevPilot Act, an autonomous CI/CD remediation agent.

Context:
- Repository: {owner}/{repo}  PR #{pr_number}
- Predict risk score: {score}/100 ({label})
- Root cause: {root_cause}
- Suggested fix: {fix_suggestion}
- Config: auto_create_issue={auto_create_issue}, suggest_deploy_strategy={suggest_deploy_strategy}, auto_adjust_gates={auto_adjust_gates}

Decide what actions to take. Respond ONLY with valid JSON (no markdown):
{{
  "deploy_strategy": "rolling" | "canary" | "blue-green" | null,
  "adjust_gate_to": null,
  "reasoning": "<one paragraph explaining your decision>"
}}

Rules:
- Recommend "canary" or "blue-green" only when score > 70.
- Recommend "rolling" when score is 40-70.
- Return null for deploy_strategy when score < 40.
- Be conservative - prefer null over a questionable recommendation.
"""


def _get_client() -> tuple:
    endpoint = os.environ["AI_FOUNDRY_ENDPOINT"]
    deployment = os.getenv("AI_FOUNDRY_MODEL_DEPLOYMENT", "gpt-4.1-mini")
    client = AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=lambda: get_credential().get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
        api_version="2024-08-01-preview",
    )
    return client, deployment


async def act(inp: ActInput) -> ActOutput:
    """Run the Act agent decision loop and execute approved actions."""
    output = ActOutput()
    act_cfg = inp.config.get("act", {})

    prompt = DECISION_PROMPT.format(
        owner=inp.owner,
        repo=inp.repo,
        pr_number=inp.pr_number,
        score=inp.predict_score,
        label=inp.predict_label,
        root_cause=inp.diagnosis.get("root_cause", ""),
        fix_suggestion=inp.diagnosis.get("fix_suggestion", ""),
        auto_create_issue=act_cfg.get("auto_create_issue", True),
        suggest_deploy_strategy=act_cfg.get("suggest_deploy_strategy", True),
        auto_adjust_gates=act_cfg.get("auto_adjust_gates", False),
    )

    try:
        client, deployment = _get_client()
        response = client.chat.completions.create(
            model=deployment,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        decision = json.loads(raw)
        logger.info("Act decision: %s", decision)
    except Exception as exc:
        logger.warning("Act LLM call failed: %s -- using rule-based fallback", exc)
        decision = _rule_based_decision(inp.predict_score)

    output.reasoning = decision.get("reasoning", "")
    output.deploy_strategy = decision.get("deploy_strategy")

    if act_cfg.get("auto_create_issue", True):
        issue = await _create_issue(inp)
        if issue:
            output.issue_url = issue.get("html_url")
            output.actions_taken.append(f"Created issue: {output.issue_url}")

    if act_cfg.get("suggest_deploy_strategy", True) and output.deploy_strategy:
        output.actions_taken.append(f"Recommended deploy strategy: {output.deploy_strategy}")

    if act_cfg.get("auto_adjust_gates", False) and decision.get("adjust_gate_to"):
        new_gate = int(decision["adjust_gate_to"])
        output.gate_adjusted = True
        output.actions_taken.append(f"Quality gate adjusted to {new_gate}")

    logger.info("Act agent completed: %s", output.actions_taken)
    return output


def _rule_based_decision(score: int) -> dict:
    """Fallback when LLM is unavailable."""
    if score >= 80:
        strategy, reason = "canary", f"Risk score {score} is high - canary deployment recommended."
    elif score >= 50:
        strategy, reason = "rolling", f"Risk score {score} is medium - rolling deployment recommended."
    else:
        strategy, reason = None, f"Risk score {score} is low - standard deployment is fine."
    return {"deploy_strategy": strategy, "adjust_gate_to": None, "reasoning": reason}


async def _create_issue(inp: ActInput) -> dict | None:
    from src.github.issues import create_issue
    title = f"[DevPilot] Pipeline failure on PR #{inp.pr_number} (risk {inp.predict_score}/100)"
    body = _issue_body(inp)
    try:
        return create_issue(
            installation_id=inp.installation_id,
            owner=inp.owner,
            repo=inp.repo,
            title=title,
            body=body,
        )
    except Exception as exc:
        logger.error("Failed to create issue: %s", exc)
        return None


def _issue_body(inp: ActInput) -> str:
    d = inp.diagnosis
    file_section = ""
    if d.get("file"):
        loc = d["file"]
        if d.get("line"):
            loc += f":{d['line']}"
        file_section = f"\n\n**Location**: `{loc}`"
    return f"""## DevPilot Auto-Generated Issue

**PR**: #{inp.pr_number}
**Risk Score**: {inp.predict_score}/100 ({inp.predict_label})
**Run**: {inp.run_url}

### Root Cause
{d.get('root_cause', 'Unknown')}{file_section}

### Suggested Fix
{d.get('fix_suggestion', '_No suggestion._')}

---
<sub>Created automatically by DevPilot Act Agent - Powered by Azure AI Foundry</sub>
"""


def format_act_summary(output: ActOutput) -> str:
    if not output.actions_taken:
        return ""
    lines = ["## DevPilot Actions", ""]
    for action in output.actions_taken:
        lines.append(f"- {action}")
    if output.reasoning:
        lines += ["", f"_{output.reasoning}_"]
    return "\n".join(lines)
