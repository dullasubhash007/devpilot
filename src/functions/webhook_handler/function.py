"""webhook_handler — HTTP-triggered Azure Function.

Receives all GitHub App webhooks via APIM, validates the HMAC signature,
and enqueues work onto Storage Queues for the three agent triggers.
"""
import json
import logging

import azure.functions as func

from src.github.webhook import verify_signature
from src.shared.logging import get_logger

logger = get_logger(__name__)

bp = func.Blueprint()


@bp.route(route="webhook", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
@bp.queue_output(arg_name="predict_queue", queue_name="predict-jobs", connection="AzureWebJobsStorage")
@bp.queue_output(arg_name="diagnose_queue", queue_name="diagnose-jobs", connection="AzureWebJobsStorage")
def webhook_handler(
    req: func.HttpRequest,
    predict_queue: func.Out[str],
    diagnose_queue: func.Out[str],
) -> func.HttpResponse:
    logger.info("Received webhook event=%s", req.headers.get("X-GitHub-Event"))

    # ── Signature validation ───────────────────────────────────────────────
    sig = req.headers.get("X-Hub-Signature-256", "")
    body = req.get_body()
    if not verify_signature(body, sig):
        logger.warning("Invalid webhook signature — rejected")
        return func.HttpResponse("Forbidden", status_code=403)

    event = req.headers.get("X-GitHub-Event", "")
    delivery_id = req.headers.get("X-GitHub-Delivery", "")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return func.HttpResponse("Bad Request", status_code=400)

    # ── Route to queues ────────────────────────────────────────────────────
    if event in ("push", "pull_request"):
        pr = payload.get("pull_request", {})
        if pr or event == "push":
            job = {
                "event": event,
                "delivery_id": delivery_id,
                "installation_id": payload.get("installation", {}).get("id"),
                "owner": payload.get("repository", {}).get("owner", {}).get("login"),
                "repo": payload.get("repository", {}).get("name"),
                "pr_number": pr.get("number"),
                "head_sha": pr.get("head", {}).get("sha") or payload.get("after"),
                "base_sha": pr.get("base", {}).get("sha") or payload.get("before"),
                "sender": payload.get("sender", {}).get("login"),
                "ref": payload.get("ref"),
            }
            predict_queue.set(json.dumps(job))
            logger.info("Enqueued predict job for PR #%s", job.get("pr_number"))

    elif event == "workflow_run":
        run = payload.get("workflow_run", {})
        if run.get("conclusion") == "failure":
            job = {
                "event": event,
                "delivery_id": delivery_id,
                "installation_id": payload.get("installation", {}).get("id"),
                "owner": payload.get("repository", {}).get("owner", {}).get("login"),
                "repo": payload.get("repository", {}).get("name"),
                "run_id": run.get("id"),
                "run_url": run.get("html_url"),
                "head_sha": run.get("head_sha"),
                "pr_numbers": [
                    pr["number"]
                    for pr in run.get("pull_requests", [])
                ],
            }
            diagnose_queue.set(json.dumps(job))
            logger.info("Enqueued diagnose job for run %s", job.get("run_id"))

    return func.HttpResponse("OK", status_code=200)
