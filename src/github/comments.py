"""GitHub PR comments — create and update markdown comments on pull requests."""
import httpx

from .auth import github_headers, GITHUB_API
from src.shared.logging import get_logger

logger = get_logger(__name__)

DEVPILOT_MARKER = "<!-- devpilot-comment -->"


def post_pr_comment(
    installation_id: int, owner: str, repo: str, pr_number: int, body: str
) -> dict:
    """Post or update a DevPilot comment on a PR (idempotent via marker)."""
    headers = github_headers(installation_id)

    # Look for an existing DevPilot comment to update
    existing_id = _find_existing_comment(headers, owner, repo, pr_number)

    body_with_marker = f"{DEVPILOT_MARKER}\n{body}"

    if existing_id:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/comments/{existing_id}"
        resp = httpx.patch(url, json={"body": body_with_marker}, headers=headers, timeout=15)
    else:
        url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        resp = httpx.post(url, json={"body": body_with_marker}, headers=headers, timeout=15)

    resp.raise_for_status()
    return resp.json()


def _find_existing_comment(
    headers: dict, owner: str, repo: str, pr_number: int
) -> int | None:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
    resp = httpx.get(url, headers=headers, params={"per_page": 100}, timeout=15)
    resp.raise_for_status()
    for comment in resp.json():
        if DEVPILOT_MARKER in comment.get("body", ""):
            return comment["id"]
    return None
