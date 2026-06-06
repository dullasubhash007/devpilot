"""diagnose_trigger — Queue-triggered Azure Function.

Consumes jobs from the ``diagnose-jobs`` Storage Queue, fetches workflow
logs and the PR diff, runs the Diagnose agent, posts a PR comment, and
then enqueues an act job.
"""
import json

import azure.functions as func

from src.agents.diagnose_agent.agent import diagnose, format_pr_comment
from src.github.comments import post_pr_comment
from src.github.content import get_workflow_logs, get_pr_diff
from src.shared.config import load_config
from src.shared.cosmos import upsert_run
from src.shared.logging import get_logger

logger = get_logger(__name__)

bp = func.Blueprint()


@bp.queue_trigger(arg_name="msg", queue_name="diagnose-jobs", connection="AzureWebJobsStorage")
@bp.queue_output(arg_name="act_queue", queue_name="act-jobs", connection="AzureWebJobsStorage")
async def diagnose_trigger(msg: func.QueueMessage, act_queue: func.Out[str]) -> None:
    job = json.loads(msg.get_body().decode())
    logger.info("diagnose_trigger: run %s in %s/%s", job.get("run_id"), job.get("owner"), job.get("repo"))

    installation_id = job["installation_id"]
    owner = job["owner"]
    repo = job["repo"]
    run_id = job["run_id"]
    run_url = job.get("run_url", "")
    head_sha = job.get("head_sha", "")
    pr_numbers: list[int] = job.get("pr_numbers", [])

    try:
        # ── Fetch logs & config ───────────────────────────────────────────
        repo_yaml = _fetch_devpilot_yml(installation_id, owner, repo, head_sha)
        cfg = load_config(repo_yaml)
        diagnose_cfg = cfg.get("diagnose", {})

        max_lines = diagnose_cfg.get("max_log_lines", 500)
        model = diagnose_cfg.get("model", "gpt-4o-mini")
        include_fix = diagnose_cfg.get("include_fix_suggestion", True)
        post_comment = diagnose_cfg.get("post_pr_comment", True)

        logs = get_workflow_logs(installation_id, owner, repo, run_id, max_lines)
        diff = ""
        if pr_numbers:
            diff = get_pr_diff(installation_id, owner, repo, pr_numbers[0])

        # ── Run Diagnose agent ────────────────────────────────────────────
        try:
            diagnosis = diagnose(logs=logs, diff=diff, model=model,
                                 max_log_lines=max_lines, include_fix=include_fix)
        except Exception as diag_exc:
            logger.warning("Diagnose LLM call failed: %s — using fallback", diag_exc)
            # Graceful fallback: parse logs for common error patterns
            diagnosis = _fallback_diagnosis(logs, str(diag_exc))

        # ── Post PR comment ───────────────────────────────────────────────
        if post_comment and pr_numbers:
            comment_body = format_pr_comment(diagnosis, run_url)
            for pr_number in pr_numbers:
                post_pr_comment(installation_id, owner, repo, pr_number, comment_body)
                logger.info("Posted diagnosis comment on PR #%s", pr_number)

        # ── Persist ───────────────────────────────────────────────────────
        run_key = f"{owner}-{repo}-run{run_id}"
        await upsert_run(run_key, {
            "type": "diagnose",
            "owner": owner,
            "repo": repo,
            "run_id": run_id,
            "diagnosis": diagnosis,
        })

        # ── Enqueue act job ───────────────────────────────────────────────
        act_job = {
            "owner": owner,
            "repo": repo,
            "installation_id": installation_id,
            "run_id": run_id,
            "run_url": run_url,
            "head_sha": head_sha,
            "pr_numbers": pr_numbers,
            "diagnosis": diagnosis,
            "run_key": run_key,
        }
        act_queue.set(json.dumps(act_job))
        logger.info("Enqueued act job for run %s", run_id)

    except Exception as exc:
        logger.exception("diagnose_trigger failed for run %s: %s", run_id, exc)


def _fetch_devpilot_yml(installation_id, owner, repo, ref) -> str | None:
    from src.github.content import get_file_content
    return get_file_content(installation_id, owner, repo, ".devpilot.yml", ref)


def _fallback_diagnosis(logs: str, error_detail: str) -> dict:
    """Rule-based fallback when AI model is unavailable.

    Scans log lines for common CI failure patterns and returns a
    structured diagnosis without calling an LLM.
    """
    import re
    patterns = [
        (r"error: (.{10,120})",        "Build/compile error"),
        (r"FAILED\s+(.{10,80})",       "Test failure"),
        (r"Error: (.{10,120})",        "Runtime error"),
        (r"npm ERR! (.{10,100})",      "npm error"),
        (r"ModuleNotFoundError: (.+)", "Missing Python module"),
        (r"cannot find (.{5,80})",     "Missing resource or file"),
        (r"exit code (\d+)",           "Non-zero exit code"),
        (r"TimeoutError|timed out",    "Timeout"),
        (r"Permission denied",         "Permission error"),
        (r"Out of memory|OOM",         "Out of memory"),
    ]

    root_cause = "Pipeline failed — AI diagnosis unavailable (no model deployment)"
    fix_suggestion = (
        "Review the workflow logs directly. "
        f"(AI Foundry model not available: {error_detail[:120]})"
    )

    for log_line in logs.splitlines()[-200:]:
        for pattern, label in patterns:
            m = re.search(pattern, log_line, re.IGNORECASE)
            if m:
                matched = m.group(1) if m.lastindex else label
                root_cause = f"{label}: {matched.strip()[:120]}"
                fix_suggestion = "Check the workflow logs for the full error context."
                break
        else:
            continue
        break

    return {
        "root_cause": root_cause,
        "fix_suggestion": fix_suggestion,
        "file": None,
        "line": None,
        "confidence": "low",
    }
