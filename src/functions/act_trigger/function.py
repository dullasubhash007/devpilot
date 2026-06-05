"""act_trigger — Queue-triggered Azure Function.

Consumes jobs from the ``act-jobs`` Storage Queue. Enriches the job with
the Predict score (from Cosmos DB), calls the Act agent, and updates the
PR comment with the action summary.
"""
import json

import azure.functions as func

from src.agents.act_agent.agent import ActInput, act, format_act_summary
from src.agents.predict_agent.agent import PredictResult
from src.github.comments import post_pr_comment
from src.shared.config import load_config
from src.shared.cosmos import get_run, upsert_run
from src.shared.logging import get_logger

logger = get_logger(__name__)

bp = func.Blueprint()


@bp.queue_trigger(arg_name="msg", queue_name="act-jobs", connection="AzureWebJobsStorage")
async def act_trigger(msg: func.QueueMessage) -> None:
    job = json.loads(msg.get_body().decode())
    logger.info("act_trigger: run %s in %s/%s", job.get("run_id"), job.get("owner"), job.get("repo"))

    owner = job["owner"]
    repo = job["repo"]
    installation_id = job["installation_id"]
    run_id = job["run_id"]
    run_url = job.get("run_url", "")
    head_sha = job.get("head_sha", "")
    pr_numbers: list[int] = job.get("pr_numbers", [])
    diagnosis: dict = job.get("diagnosis", {})
    run_key: str = job.get("run_key", f"{owner}-{repo}-run{run_id}")

    try:
        # ── Fetch predict score from Cosmos DB ────────────────────────────
        predict_score = 50
        predict_label = "medium"
        if pr_numbers:
            predict_key = f"{owner}-{repo}-pr{pr_numbers[0]}-{head_sha[:7]}"
            predict_record = await get_run(predict_key)
            if predict_record:
                predict_score = predict_record.get("score", 50)
                predict_label = predict_record.get("label", "medium")

        # ── Load config ───────────────────────────────────────────────────
        repo_yaml = _fetch_devpilot_yml(installation_id, owner, repo, head_sha)
        cfg = load_config(repo_yaml)

        # ── Skip if human approval required ──────────────────────────────
        qg = cfg.get("quality_gates", {})
        if qg.get("require_human_approval_on_act", True):
            logger.info("Act agent skipped: require_human_approval_on_act=true")
            return

        # ── Run Act agent ─────────────────────────────────────────────────
        inp = ActInput(
            owner=owner,
            repo=repo,
            pr_number=pr_numbers[0] if pr_numbers else 0,
            installation_id=installation_id,
            run_id=run_id,
            run_url=run_url,
            predict_score=predict_score,
            predict_label=predict_label,
            diagnosis=diagnosis,
            config=cfg,
            head_sha=head_sha,
        )
        output = await act(inp)

        # ── Append act summary to PR comment ─────────────────────────────
        if output.actions_taken and pr_numbers:
            summary = format_act_summary(output)
            if summary:
                post_pr_comment(installation_id, owner, repo, pr_numbers[0], summary)

        # ── Persist ───────────────────────────────────────────────────────
        await upsert_run(run_key, {
            "act": {
                "issue_url": output.issue_url,
                "deploy_strategy": output.deploy_strategy,
                "gate_adjusted": output.gate_adjusted,
                "actions_taken": output.actions_taken,
                "reasoning": output.reasoning,
            }
        })

    except Exception as exc:
        logger.exception("act_trigger failed for run %s: %s", run_id, exc)


def _fetch_devpilot_yml(installation_id, owner, repo, ref) -> str | None:
    from src.github.content import get_file_content
    return get_file_content(installation_id, owner, repo, ".devpilot.yml", ref)
