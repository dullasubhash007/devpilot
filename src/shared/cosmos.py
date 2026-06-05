"""Cosmos DB client — pipeline_runs container."""
import os
from datetime import datetime, timezone
from typing import Any

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey

from .credential import get_credential
from .logging import get_logger

logger = get_logger(__name__)

_client: CosmosClient | None = None


def _get_client() -> CosmosClient:
    global _client
    if _client is None:
        _client = CosmosClient(
            url=os.environ["COSMOS_ENDPOINT"],
            credential=get_credential(),
        )
    return _client


async def upsert_run(run_id: str, data: dict[str, Any]) -> None:
    client = _get_client()
    db = client.get_database_client(os.getenv("COSMOS_DATABASE", "devpilot"))
    container = db.get_container_client(
        os.getenv("COSMOS_CONTAINER", "pipeline_runs")
    )
    item = {
        "id": run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    await container.upsert_item(item)
    logger.debug("Upserted run %s to Cosmos DB", run_id)


async def get_run(run_id: str) -> dict[str, Any] | None:
    client = _get_client()
    db = client.get_database_client(os.getenv("COSMOS_DATABASE", "devpilot"))
    container = db.get_container_client(
        os.getenv("COSMOS_CONTAINER", "pipeline_runs")
    )
    try:
        return await container.read_item(item=run_id, partition_key=run_id)
    except Exception:
        return None
