"""Authentication utilities for Cognito Hosted UI OAuth2 + PKCE."""

from __future__ import annotations

import base64
import contextlib
import hashlib
import logging
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import jwt
import requests

from .config import load_config

logger = logging.getLogger(__name__)


@dataclass
class OAuthTokens:
    """Container for OAuth token set fetched from Cognito."""

    access_token: str
    id_token: str
    refresh_token: str | None
    expires_in: int


def generate_pkce_pair() -> tuple[str, str]:
    """Generate PKCE code verifier and challenge.

    Returns:
        Tuple of (code_verifier, code_challenge)
    """
    # Generate random 128-byte code verifier
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(96)).decode("utf-8")
    # Remove padding
    code_verifier = code_verifier.rstrip("=")

    # Create SHA256 hash
    code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    # Base64 URL-safe encode
    code_challenge = base64.urlsafe_b64encode(code_challenge).decode("utf-8")
    code_challenge = code_challenge.rstrip("=")

    return code_verifier, code_challenge


def build_authorization_url(state: str, code_challenge: str, redirect_uri: str) -> str:
    """Build OAuth2 authorization URL with PKCE.

    Args:
        state: Random state parameter for CSRF protection
        code_challenge: PKCE code challenge (S256 hash of verifier)
        redirect_uri: Callback URL (e.g., http://localhost:8501)

    Returns:
        Complete authorization URL to redirect user to
    """
    config = load_config()

    params = {
        "response_type": "code",
        "client_id": config.cognito.client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "scope": "openid email profile",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    return f"{config.cognito.authorize_url}?{urlencode(params)}"


def exchange_code_for_tokens(
    authorization_code: str,
    code_verifier: str,
    redirect_uri: str,
) -> OAuthTokens:
    """Exchange authorization code for OAuth2 tokens.

    Args:
        authorization_code: Code from OAuth callback
        code_verifier: PKCE code verifier (original random string)
        redirect_uri: Same redirect URI used in authorization request

    Returns:
        OAuthTokens containing access, ID, and refresh tokens

    Raises:
        ValueError: If token exchange fails
    """
    config = load_config()

    # Prepare Basic Auth header
    credentials = f"{config.cognito.client_id}:{config.cognito.client_secret}"
    b64_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier,
    }

    try:
        response = requests.post(
            config.cognito.token_url,
            headers=headers,
            data=data,
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()

        return OAuthTokens(
            access_token=token_data["access_token"],
            id_token=token_data["id_token"],
            refresh_token=token_data.get("refresh_token"),
            expires_in=token_data["expires_in"],
        )
    except requests.HTTPError as e:
        logger.error(f"Token exchange failed: {e}")
        error_detail = {}
        if hasattr(e, "response") and e.response is not None and e.response.text:
            with contextlib.suppress(Exception):
                error_detail = e.response.json()
        raise ValueError(
            f"Authentication failed: {error_detail.get('error_description', 'Unknown error')}"
        ) from e
    except requests.RequestException as e:
        logger.error(f"Network error during token exchange: {e}")
        raise ValueError("Network error during authentication. Please try again.") from e


def refresh_access_token(refresh_token: str) -> OAuthTokens:
    """Refresh access token using refresh token.

    Args:
        refresh_token: Refresh token from previous authentication

    Returns:
        New OAuthTokens with refreshed access token

    Raises:
        ValueError: If refresh fails
    """
    config = load_config()

    # Prepare Basic Auth header
    credentials = f"{config.cognito.client_id}:{config.cognito.client_secret}"
    b64_credentials = base64.b64encode(credentials.encode()).decode()

    headers = {
        "Authorization": f"Basic {b64_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    try:
        response = requests.post(
            config.cognito.token_url,
            headers=headers,
            data=data,
            timeout=10,
        )
        response.raise_for_status()
        token_data = response.json()

        return OAuthTokens(
            access_token=token_data["access_token"],
            id_token=token_data["id_token"],
            refresh_token=token_data.get("refresh_token", refresh_token),  # May not return new one
            expires_in=token_data["expires_in"],
        )
    except requests.HTTPError as e:
        logger.error(f"Token refresh failed: {e}")
        raise ValueError("Session expired. Please log in again.") from e
    except requests.RequestException as e:
        logger.error(f"Network error during token refresh: {e}")
        raise ValueError("Network error. Please try again.") from e


def decode_id_token(id_token: str) -> dict[str, Any]:
    """Decode JWT ID token to extract user claims.

    Note: This does NOT verify the signature - API Gateway handles that.
    This is only for extracting user information client-side.

    Args:
        id_token: JWT ID token from Cognito

    Returns:
        Dictionary of token claims (sub, email, username, etc.)
    """
    try:
        # Decode without verification (verification happens at API Gateway)
        claims = jwt.decode(id_token, options={"verify_signature": False})
        return claims
    except jwt.DecodeError as e:
        logger.error(f"Failed to decode ID token: {e}")
        raise ValueError("Invalid ID token") from e


def build_logout_url(redirect_uri: str) -> str:
    """Build Cognito logout URL.

    Args:
        redirect_uri: Where to redirect after logout

    Returns:
        Complete logout URL
    """
    config = load_config()

    params = {
        "client_id": config.cognito.client_id,
        "logout_uri": redirect_uri,
    }

    return f"{config.cognito.logout_url}?{urlencode(params)}"
