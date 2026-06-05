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
    cred = (ManagedIdentityCredential() if os.getenv("WEBSITE_INSTANCE_ID")
            else DefaultAzureCredential())
    return QueueServiceClient(
        account_url=f"https://{os.environ['STORAGE_ACCOUNT_NAME']}.queue.core.windows.net",
        credential=cred,
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
            _enqueue("predict-jobs", job)

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
                "pr_numbers": [pr["number"] for pr in run.get("pull_requests", [])],
            }
            _enqueue("diagnose-jobs", job)

    return Response(content="OK", status_code=200)
