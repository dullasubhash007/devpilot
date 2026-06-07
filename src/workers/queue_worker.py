"""Background queue worker — replaces Azure Functions queue triggers.

Polls predict-jobs, diagnose-jobs, and act-jobs queues and dispatches
to the respective agents. Runs as a long-lived Container App worker.
"""
import asyncio
import base64
import json
import logging
import os
import signal
import sys

from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.storage.queue import QueueServiceClient, QueueMessage

from src.shared.logging import get_logger

logger = get_logger(__name__)

QUEUES = ["predict-jobs", "diagnose-jobs", "act-jobs"]
POLL_INTERVAL = int(os.getenv("QUEUE_POLL_INTERVAL", "5"))
_running = True


def _get_credential():
    if os.getenv("IDENTITY_ENDPOINT") or os.getenv("WEBSITE_INSTANCE_ID"):
        return ManagedIdentityCredential()
    return DefaultAzureCredential()


def _queue_service() -> QueueServiceClient:
    return QueueServiceClient(
        account_url=f"https://{os.environ['STORAGE_ACCOUNT_NAME']}.queue.core.windows.net",
        credential=_get_credential(),
    )


def _decode(msg: QueueMessage) -> dict:
    try:
        return json.loads(base64.b64decode(msg.content).decode())
    except Exception:
        return json.loads(msg.content)


async def _process_predict(job: dict) -> None:
    from src.functions.predict_trigger.function import _run_predict
    await _run_predict(job)


async def _process_diagnose(job: dict) -> None:
    from src.functions.diagnose_trigger.function import _run_diagnose
    act_job = await _run_diagnose(job)
    if act_job:
        svc = _queue_service()
        q = svc.get_queue_client("act-jobs")
        q.send_message(base64.b64encode(json.dumps(act_job).encode()).decode())


async def _process_act(job: dict) -> None:
    from src.functions.act_trigger.function import _run_act
    await _run_act(job)


HANDLERS = {
    "predict-jobs":  _process_predict,
    "diagnose-jobs": _process_diagnose,
    "act-jobs":      _process_act,
}


async def poll_queue(svc: QueueServiceClient, queue_name: str) -> None:
    q = svc.get_queue_client(queue_name)
    messages = q.receive_messages(max_messages=4, visibility_timeout=60)
    for msg in messages:
        try:
            job = _decode(msg)
            logger.info("Processing %s job %s", queue_name, job.get("delivery_id", ""))
            await HANDLERS[queue_name](job)
            q.delete_message(msg)
        except Exception as exc:
            logger.exception("Failed to process %s message: %s", queue_name, exc)


async def main_loop() -> None:
    global _running
    svc = _queue_service()
    logger.info("Worker started — polling queues: %s", QUEUES)
    while _running:
        for queue_name in QUEUES:
            try:
                await poll_queue(svc, queue_name)
            except Exception as exc:
                logger.warning("Error polling %s: %s", queue_name, exc)
        await asyncio.sleep(POLL_INTERVAL)
    logger.info("Worker stopped.")


def _shutdown(sig, frame):
    global _running
    logger.info("Signal %s received — shutting down", sig)
    _running = False


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    asyncio.run(main_loop())
