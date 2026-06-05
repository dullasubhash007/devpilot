"""GitHub App authentication — generates short-lived installation access tokens."""
import time
from functools import lru_cache

import jwt
import httpx

from src.shared.keyvault import get_secret
from src.shared.logging import get_logger

logger = get_logger(__name__)

GITHUB_API = "https://api.github.com"


def _make_jwt(app_id: str, private_key_pem: str) -> str:
    """Mint a GitHub App JWT (valid for 60 seconds)."""
    now = int(time.time())
    payload = {"iat": now - 10, "exp": now + 60, "iss": app_id}
    return jwt.encode(payload, private_key_pem, algorithm="RS256")


def get_installation_token(installation_id: int) -> str:
    """Exchange GitHub App JWT for an installation access token."""
    app_id = get_secret("github-app-id")
    private_key = get_secret("github-app-private-key")

    app_jwt = _make_jwt(app_id, private_key)
    headers = {
        "Authorization": f"Bearer {app_jwt}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"{GITHUB_API}/app/installations/{installation_id}/access_tokens"
    resp = httpx.post(url, headers=headers, timeout=10)
    resp.raise_for_status()
    token = resp.json()["token"]
    logger.debug("Obtained installation token for installation %s", installation_id)
    return token


def github_headers(installation_id: int) -> dict:
    token = get_installation_token(installation_id)
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
