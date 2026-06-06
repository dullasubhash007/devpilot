"""Unit tests for GitHub webhook HMAC signature validator."""
import hashlib
import hmac
import pytest
from unittest.mock import patch

from src.github.webhook import verify_signature


SECRET = "test-webhook-secret-abc123"
PAYLOAD = b'{"action":"opened","pull_request":{"number":42}}'


def _make_sig(payload: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


@patch("src.github.webhook.get_secret", return_value=SECRET)
def test_valid_signature(mock_secret):
    sig = _make_sig(PAYLOAD, SECRET)
    assert verify_signature(PAYLOAD, sig) is True


@patch("src.github.webhook.get_secret", return_value=SECRET)
def test_wrong_secret(mock_secret):
    sig = _make_sig(PAYLOAD, "wrong-secret")
    assert verify_signature(PAYLOAD, sig) is False


@patch("src.github.webhook.get_secret", return_value=SECRET)
def test_tampered_payload(mock_secret):
    sig = _make_sig(PAYLOAD, SECRET)
    tampered = PAYLOAD + b"extra"
    assert verify_signature(tampered, sig) is False


@patch("src.github.webhook.get_secret", return_value=SECRET)
def test_missing_signature_header(mock_secret):
    assert verify_signature(PAYLOAD, "") is False


@patch("src.github.webhook.get_secret", return_value=SECRET)
def test_malformed_signature_header(mock_secret):
    assert verify_signature(PAYLOAD, "sha1=abc") is False


@patch("src.github.webhook.get_secret", return_value=SECRET)
def test_none_signature_header(mock_secret):
    assert verify_signature(PAYLOAD, None) is False
