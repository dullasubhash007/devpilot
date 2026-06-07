"""predict_trigger — Queue-triggered Azure Function.

Consumes jobs from the ``predict-jobs`` Storage Queue, extracts features
from the PR diff, calls the Predict agent, and posts a GitHub Check.
"""
import json
import logging

import azure.functions as func

from src.agents.predict_agent.agent import extract_features, predict, format_check_summary
from src.github.checks import create_check_run, update_check_run
from src.github.content import get_pr_diff
from src.shared.config import load_config
from src.shared.cosmos import upsert_run
from src.shared.logging import get_logger

logger = get_logger(__name__)

bp = func.Blueprint()


@bp.queue_trigger(arg_name="msg", queue_name="predict-jobs", connection="AzureWebJobsStorage")
async def predict_trigger(msg: func.QueueMessage) -> None:
    job = json.loads(msg.get_body().decode())
    await _run_predict(job)


async def _run_predict(job: dict) -> None:
    """Core predict logic — callable from both Azure Functions and queue_worker."""
    logger.info("predict_trigger: PR #%s in %s/%s", job.get("pr_number"), job.get("owner"), job.get("repo"))

    installation_id = job["installation_id"]
    owner = job["owner"]
    repo = job["repo"]
    pr_number = job.get("pr_number")
    head_sha = job["head_sha"]

    if not pr_number or not head_sha:
        logger.warning("predict_trigger: missing pr_number or head_sha, skipping")
        return

    # ── Create pending check run ──────────────────────────────────────────
    check = create_check_run(
        installation_id=installation_id,
        owner=owner,
        repo=repo,
        name="DevPilot · Predict",
        head_sha=head_sha,
        status="in_progress",
        title="Calculating failure risk…",
        summary="DevPilot is analysing the pull request.",
    )
    check_run_id = check["id"]

    try:
        # ── Fetch diff & config ───────────────────────────────────────────
        diff = ""
        try:
            diff = get_pr_diff(installation_id, owner, repo, pr_number)
        except Exception as diff_exc:
            logger.warning("Could not fetch PR diff: %s — scoring with empty diff", diff_exc)

        repo_yaml = _fetch_devpilot_yml(installation_id, owner, repo, head_sha)
        cfg = load_config(repo_yaml)
        predict_cfg = cfg.get("predict", {})

        # ── Feature extraction ────────────────────────────────────────────
        # Prefer PR metadata from webhook payload (more accurate than diff parsing)
        pr_additions = job.get("pr_additions", 0)
        pr_deletions = job.get("pr_deletions", 0)
        pr_changed_files = job.get("pr_changed_files", 0)
        branch_age_days = job.get("branch_age_days", 0)

        features = extract_features(diff=diff)

        # Override with accurate PR metadata when available
        if pr_additions or pr_deletions:
            features.diff_size = pr_additions + pr_deletions
        if pr_changed_files:
            features.files_changed = pr_changed_files
        if branch_age_days:
            features.branch_age = branch_age_days

        logger.info(
            "Predict features: diff_size=%d files=%d branch_age=%d",
            features.diff_size, features.files_changed, features.branch_age
        )

        result = predict(features, enabled_features=predict_cfg.get("features"))

        failure_threshold = predict_cfg.get("failure_threshold", 70)
        block_threshold = predict_cfg.get("block_threshold", 90)

        if result.score >= block_threshold:
            conclusion = "failure"
        elif result.score >= failure_threshold:
            conclusion = "neutral"
        else:
            conclusion = "success"

        summary = format_check_summary(result, failure_threshold, block_threshold)
        title = f"Risk Score: {result.score}/100 — {result.label.upper()}"

        update_check_run(
            installation_id=installation_id,
            owner=owner,
            repo=repo,
            check_run_id=check_run_id,
            conclusion=conclusion,
            title=title,
            summary=summary,
        )

        # ── Persist to Cosmos DB ──────────────────────────────────────────
        await upsert_run(
            f"{owner}-{repo}-pr{pr_number}-{head_sha[:7]}",
            {
                "type": "predict",
                "owner": owner,
                "repo": repo,
                "pr_number": pr_number,
                "head_sha": head_sha,
                "score": result.score,
                "label": result.label,
                "features": result.features,
            },
        )

    except Exception as exc:
        logger.exception("predict_trigger failed: %s", exc)
        update_check_run(
            installation_id=installation_id,
            owner=owner,
            repo=repo,
            check_run_id=check_run_id,
            conclusion="neutral",
            title="Predict — Unavailable",
            summary=f"DevPilot Predict could not complete: `{exc}`",
        )


def _fetch_devpilot_yml(installation_id, owner, repo, ref) -> str | None:
    from src.github.content import get_file_content
    return get_file_content(installation_id, owner, repo, ".devpilot.yml", ref)
