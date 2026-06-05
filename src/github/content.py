"""Fetch workflow run logs and pull request diff from GitHub."""
import base64
import io
import zipfile

import httpx

from .auth import github_headers, GITHUB_API
from src.shared.logging import get_logger

logger = get_logger(__name__)


def get_workflow_logs(
    installation_id: int,
    owner: str,
    repo: str,
    run_id: int,
    max_lines: int = 500,
) -> str:
    """Download and extract the last *max_lines* lines of workflow logs."""
    headers = github_headers(installation_id)
    url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
    resp = httpx.get(url, headers=headers, follow_redirects=True, timeout=30)
    resp.raise_for_status()

    lines: list[str] = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith(".txt"):
                text = zf.read(name).decode("utf-8", errors="replace")
                lines.extend(text.splitlines())

    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    return "\n".join(lines)


def get_pr_diff(
    installation_id: int, owner: str, repo: str, pr_number: int
) -> str:
    headers = {**github_headers(installation_id), "Accept": "application/vnd.github.diff"}
    url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    resp = httpx.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def get_file_content(
    installation_id: int, owner: str, repo: str, path: str, ref: str
) -> str | None:
    headers = github_headers(installation_id)
    url = f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
    resp = httpx.get(url, headers=headers, params={"ref": ref}, timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    data = resp.json()
    if data.get("encoding") == "base64":
        return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return data.get("content", "")
