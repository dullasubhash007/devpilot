"""GitHub Issues — create issues with diagnosis and fix suggestion."""
import httpx

from .auth import github_headers, GITHUB_API
from src.shared.logging import get_logger

logger = get_logger(__name__)


def create_issue(
    installation_id: int,
    owner: str,
    repo: str,
    title: str,
    body: str,
    labels: list[str] | None = None,
) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    payload = {"title": title, "body": body, "labels": labels or ["devpilot", "bug"]}
    resp = httpx.post(
        url, json=payload, headers=github_headers(installation_id), timeout=15
    )
    resp.raise_for_status()
    issue = resp.json()
    logger.info("Created issue #%s: %s", issue["number"], title)
    return issue
