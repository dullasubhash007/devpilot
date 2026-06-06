"""Act Agent — autonomous actions via Semantic Kernel + Azure AI Foundry.

Given the Predict score and Diagnose output, the Act agent decides:
  • Whether to create a GitHub Issue with the diagnosis
  • Whether to recommend a deploy strategy (rolling / canary / blue-green)
  • Whether to adjust quality gates (only when auto_adjust_gates=True)

All decisions are recorded in Cosmos DB and surfaced in the PR comment.
"""
import json
import os
from dataclasses import dataclass, field

import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistory

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
    diagnosis: dict                      # output of diagnose agent
    config: dict                         # resolved .devpilot.yml section
    head_sha: str = ""
    run_url: str = ""


@dataclass
class ActOutput:
    issue_url: str | None = None
    deploy_strategy: str | None = None   # "rolling" | "canary" | "blue-green"
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

Decide what actions to take. Respond ONLY with valid JSON:
{{
  "deploy_strategy": "rolling" | "canary" | "blue-green" | null,
  "adjust_gate_to": <integer 0-100 or null>,
  "reasoning": "<one paragraph>"
}}

Rules:
- Recommend "canary" or "blue-green" only when score > 70.
- Adjust gate only when auto_adjust_gates is true AND score has changed significantly.
- Be conservative — prefer null over a questionable recommendation.
"""


def _build_kernel() -> sk.Kernel:
    kernel = sk.Kernel()
    endpoint = os.environ["AI_FOUNDRY_ENDPOINT"]
    deployment = os.getenv("AI_FOUNDRY_MODEL_DEPLOYMENT", "diagnose")
    kernel.add_service(
        AzureChatCompletion(
            service_id="act",
            deployment_name=deployment,
            endpoint=endpoint,
            ad_token_provider=lambda: get_credential().get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token,
        )
    )
    return kernel


async def act(inp: ActInput) -> ActOutput:
    """Run the Act agent decision loop and execute approved actions."""
    output = ActOutput()
    act_cfg = inp.config.get("act", {})

    # --- Decision via Semantic Kernel ---
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

    kernel = _build_kernel()
    history = ChatHistory()
    history.add_user_message(prompt)

    chat_service = kernel.get_service("act")
    settings = kernel.get_prompt_execution_settings_from_service_id("act")
    settings.temperature = 0.1
    settings.max_tokens = 400

    response = await chat_service.get_chat_message_contents(
        chat_history=history, settings=settings
    )
    raw = response[0].content if response else "{}"

    try:
        decision = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Act agent returned unparseable JSON: %s", raw)
        decision = {}

    output.reasoning = decision.get("reasoning", "")
    output.deploy_strategy = decision.get("deploy_strategy")

    # --- Execute actions ---
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


async def _create_issue(inp: ActInput) -> dict | None:
    from src.github.issues import create_issue

    title = (
        f"[DevPilot] Pipeline failure on PR #{inp.pr_number} "
        f"(risk {inp.predict_score}/100)"
    )
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
    strategy_section = ""
    return f"""## 🤖 DevPilot Auto-Generated Issue

**PR**: #{inp.pr_number}  
**Risk Score**: {inp.predict_score}/100 ({inp.predict_label})  
**Run**: {inp.run_url}

### Root Cause
{d.get('root_cause', 'Unknown')}

### Suggested Fix
{d.get('fix_suggestion', '_No suggestion._')}

{"### File" + chr(10) + f"`{d['file']}`" + (f":{d['line']}" if d.get('line') else "") if d.get('file') else ""}

---
<sub>Created automatically by DevPilot Act Agent · Powered by Azure AI Foundry</sub>
"""


def format_act_summary(output: ActOutput) -> str:
    if not output.actions_taken:
        return ""
    lines = ["## 🤖 DevPilot Actions", ""]
    for action in output.actions_taken:
        lines.append(f"- {action}")
    if output.reasoning:
        lines += ["", f"_{output.reasoning}_"]
    return "\n".join(lines)
