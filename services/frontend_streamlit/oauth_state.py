"""Utilities for signing and verifying OAuth state parameters."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from .config import load_config

STATE_PAYLOAD_VERSION = 1
STATE_MAX_AGE_SECONDS = 300  # 5 minutes


class OAuthStateError(ValueError):
    """Raised when the OAuth state payload is invalid or cannot be verified."""


def _get_signing_key() -> bytes:
    config = load_config()
    client_secret = getattr(config.cognito, "client_secret", None)
    if not client_secret:
        raise OAuthStateError("Cognito client secret is not configured for signing state.")
    return client_secret.encode("utf-8")


def _urlsafe_b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _urlsafe_b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _sign_payload(payload: dict[str, Any]) -> str:
    signing_key = _get_signing_key()
    serialized = _serialize_payload(payload).encode("utf-8")
    signature = hmac.new(signing_key, serialized, hashlib.sha256).digest()
    return _urlsafe_b64encode(signature)


def encode_oauth_state(code_verifier: str) -> str:
    """Create a signed OAuth state string that encodes the PKCE verifier."""
    if not code_verifier:
        raise OAuthStateError("PKCE code verifier is required to encode state.")

    payload: dict[str, Any] = {
        "v": STATE_PAYLOAD_VERSION,
        "iat": int(time.time()),
        "nonce": secrets.token_urlsafe(16),
        "verifier": code_verifier,
    }

    signature = _sign_payload(payload)
    payload_with_signature = {**payload, "sig": signature}
    serialized = _serialize_payload(payload_with_signature).encode("utf-8")
    return _urlsafe_b64encode(serialized)


def decode_oauth_state(state_value: str) -> dict[str, Any]:
    """Decode and verify a signed OAuth state string."""
    if not state_value:
        raise OAuthStateError("State value is missing.")

    try:
        decoded = _urlsafe_b64decode(state_value).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:  # pragma: no cover - defensive
        raise OAuthStateError("Unable to decode state payload.") from exc

    try:
        payload_with_signature: dict[str, Any] = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise OAuthStateError("State payload is not valid JSON.") from exc

    signature = payload_with_signature.pop("sig", None)
    if not signature:
        raise OAuthStateError("State payload signature is missing.")

    expected_signature = _sign_payload(payload_with_signature)
    if not hmac.compare_digest(signature, expected_signature):
        raise OAuthStateError("State payload signature mismatch.")

    if payload_with_signature.get("v") != STATE_PAYLOAD_VERSION:
        raise OAuthStateError("Unsupported state payload version.")

    issued_at = payload_with_signature.get("iat")
    if not isinstance(issued_at, int):
        raise OAuthStateError("State payload timestamp is invalid.")

    if time.time() - issued_at > STATE_MAX_AGE_SECONDS:
        raise OAuthStateError("State payload has expired.")

    verifier = payload_with_signature.get("verifier")
    if not isinstance(verifier, str) or not verifier:
        raise OAuthStateError("State payload is missing PKCE verifier.")

    return payload_with_signature
