"""GitHub webhook HMAC-SHA256 signature validator."""
import hashlib
import hmac

from src.shared.keyvault import get_secret
from src.shared.logging import get_logger

logger = get_logger(__name__)


def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
    """Return True when the webhook payload matches the stored secret."""
    if not signature_header or not signature_header.startswith("sha256="):
        logger.warning("Missing or malformed webhook signature header")
        return False

    secret = get_secret("github-webhook-secret").encode()
    expected = "sha256=" + hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)
