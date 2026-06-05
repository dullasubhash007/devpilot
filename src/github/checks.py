"""GitHub Checks API — create / update check runs."""
import httpx

from .auth import github_headers, GITHUB_API
from src.shared.logging import get_logger

logger = get_logger(__name__)


def create_check_run(
    installation_id: int,
    owner: str,
    repo: str,
    name: str,
    head_sha: str,
    status: str = "in_progress",
    conclusion: str | None = None,
    title: str = "",
    summary: str = "",
    annotations: list[dict] | None = None,
) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/check-runs"
    body: dict = {
        "name": name,
        "head_sha": head_sha,
        "status": status,
        "output": {
            "title": title,
            "summary": summary,
            "annotations": annotations or [],
        },
    }
    if conclusion:
        body["conclusion"] = conclusion
        body["status"] = "completed"

    resp = httpx.post(url, json=body, headers=github_headers(installation_id), timeout=15)
    resp.raise_for_status()
    return resp.json()


def update_check_run(
    installation_id: int,
    owner: str,
    repo: str,
    check_run_id: int,
    conclusion: str,
    title: str,
    summary: str,
    annotations: list[dict] | None = None,
) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/check-runs/{check_run_id}"
    body = {
        "status": "completed",
        "conclusion": conclusion,
        "output": {
            "title": title,
            "summary": summary,
            "annotations": annotations or [],
        },
    }
    resp = httpx.patch(url, json=body, headers=github_headers(installation_id), timeout=15)
    resp.raise_for_status()
    return resp.json()
