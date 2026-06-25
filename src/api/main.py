"""FastAPI webhook receiver — replaces Azure Functions HTTP trigger + APIM.

Receives GitHub App webhooks, validates HMAC-SHA256 signature, and enqueues
jobs onto Azure Storage Queues for the worker process.
"""
import json
import logging
import os

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.queue import QueueServiceClient
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse

from src.github.webhook import verify_signature
from src.shared.logging import get_logger

logger = get_logger(__name__)
app = FastAPI(title="DevPilot Webhook", version="1.0.0")


def _queue_client() -> QueueServiceClient:
    # Use ManagedIdentityCredential explicitly — avoids DefaultAzureCredential
    # falling through to Azure CLI token which lacks Storage Queue scope.
    return QueueServiceClient(
        account_url=f"https://{os.environ['STORAGE_ACCOUNT_NAME']}.queue.core.windows.net",
        credential=ManagedIdentityCredential(),
    )


def _enqueue(queue_name: str, payload: dict) -> None:
    client = _queue_client()
    q = client.get_queue_client(queue_name)
    # Base64-encode so Azure Storage Queue accepts it
    import base64
    msg = base64.b64encode(json.dumps(payload).encode()).decode()
    q.send_message(msg)
    logger.info("Enqueued message to %s", queue_name)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/devpilot/webhook")
async def webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    event = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", "")

    # ── Signature validation ──────────────────────────────────────────────
    if not verify_signature(body, sig):
        logger.warning("Invalid webhook signature — rejected delivery %s", delivery_id)
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # ── Route to queues ───────────────────────────────────────────────────
    if event in ("push", "pull_request"):
        pr = payload.get("pull_request", {})
        if pr or event == "push":
            # Compute approximate branch age from PR creation date vs base push
            branch_age_days = 0
            if pr.get("created_at") and pr.get("base", {}).get("repo", {}).get("pushed_at"):
                try:
                    from datetime import datetime, timezone
                    created = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                    base_pushed = datetime.fromisoformat(
                        pr["base"]["repo"]["pushed_at"].replace("Z", "+00:00")
                    )
                    branch_age_days = max(0, (created - base_pushed).days)
                except Exception:
                    pass

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
                "branch_age_days": branch_age_days,
                "pr_additions": pr.get("additions", 0),
                "pr_deletions": pr.get("deletions", 0),
                "pr_changed_files": pr.get("changed_files", 0),
            }
            _enqueue("predict-jobs", job)

    elif event == "workflow_run":
        run = payload.get("workflow_run", {})
        owner = payload.get("repository", {}).get("owner", {}).get("login")
        repo = payload.get("repository", {}).get("name")
        installation_id = payload.get("installation", {}).get("id")

        if payload.get("action") == "completed" and run.get("conclusion"):
            _enqueue(
                "predict-jobs",
                {
                    "event": event,
                    "kind": "outcome",
                    "delivery_id": delivery_id,
                    "installation_id": installation_id,
                    "owner": owner,
                    "repo": repo,
                    "head_sha": run.get("head_sha"),
                    "run_id": run.get("id"),
                    "conclusion": run.get("conclusion"),
                },
            )

        if run.get("conclusion") == "failure":
            _enqueue(
                "diagnose-jobs",
                {
                    "event": event,
                    "delivery_id": delivery_id,
                    "installation_id": installation_id,
                    "owner": owner,
                    "repo": repo,
                    "run_id": run.get("id"),
                    "run_url": run.get("html_url"),
                    "head_sha": run.get("head_sha"),
                    "pr_numbers": [pr["number"] for pr in run.get("pull_requests", [])],
                },
            )

    return Response(content="OK", status_code=200)
