"""Authentication utilities for Amazon Bedrock AgentCore.

Provides helpers for:
- Cognito Machine-to-Machine (M2M) authentication
- OAuth2 Client Credentials flow
- SSM Parameter Store access

Also includes convenience helpers used by agent runtimes to obtain a
"Bearer <token>" value for calling Gateway MCP when an end-user token
is not present.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import urlencode

import boto3
import requests


def get_ssm_parameter(name: str, with_decryption: bool = True) -> str:
    """
    Get parameter from AWS Systems Manager Parameter Store.

    Args:
        name: Parameter name (e.g., '/app/myagent/agentcore/pool_id')
        with_decryption: Decrypt SecureString parameters

    Returns:
        Parameter value

    Raises:
        ValueError: If parameter not found

    Example:
        >>> pool_id = get_ssm_parameter('/app/myagent/agentcore/pool_id')
    """
    ssm = boto3.client("ssm")

    try:
        response = ssm.get_parameter(Name=name, WithDecryption=with_decryption)
        return str(response["Parameter"]["Value"])
    except ssm.exceptions.ParameterNotFound as e:
        raise ValueError(f"SSM parameter not found: {name}") from e


def get_m2m_token(
    client_id: str | None = None,
    client_secret: str | None = None,
    ssm_prefix: str = "/app/customersupport/agentcore",
    scope: str | None = None,
    token_url: str | None = None,
    domain: str | None = None,
    region: str | None = None,
    default_scope: str | None = "agentcore/invoke",
) -> str:
    """
    Get Machine-to-Machine access token using OAuth2 Client Credentials flow.

    This function implements the M2M authentication pattern used by AgentCore
    Runtime to authorize API calls to AgentCore services (Gateway, Memory, etc.).

    Args:
        client_id: Cognito app client ID (if None, reads from SSM)
        client_secret: Client secret (if None, reads from SSM)
        ssm_prefix: SSM parameter path prefix

    Returns:
        Access token (JWT) with correct scope for AgentCore services

    Raises:
        RuntimeError: If token exchange fails

    Example:
        >>> # Automatic (reads from SSM)
        >>> token = get_m2m_token()
        >>>
        >>> # Manual
        >>> token = get_m2m_token(client_id='abc123', client_secret='secret')

    References:
        - OAuth 2.0 Client Credentials: https://tools.ietf.org/html/rfc6749#section-4.4
        - AgentCore Authorization: See architecture-decisions.md
    """
    session_region = region or boto3.session.Session().region_name or "us-east-1"

    def _get_optional_param(parameter: str, decrypt: bool = True) -> str | None:
        full_name = (
            parameter if parameter.startswith("/") else f"{ssm_prefix.rstrip('/')}/{parameter}"
        )

        try:
            return get_ssm_parameter(full_name, with_decryption=decrypt)
        except ValueError:
            return None

    # Read credentials from SSM if not provided
    if not client_id:
        client_id = _get_optional_param("machine_client_id") or _get_optional_param("client_id")
    if not client_secret:
        client_secret = _get_optional_param("client_secret")

    # Resolve OAuth settings (token URL, scope, domain)
    if not token_url:
        token_url = _get_optional_param("cognito_token_url")
    if scope is None:
        scope = _get_optional_param("cognito_auth_scope")
    if not domain:
        domain = _get_optional_param("domain") or _get_optional_param("cognito_domain")

    if not token_url and domain:
        normalized_domain = domain.rstrip("/")
        if not normalized_domain.startswith("http://") and not normalized_domain.startswith(
            "https://"
        ):
            normalized_domain = (
                f"https://{normalized_domain}.auth.{session_region}.amazoncognito.com"
            )
        token_url = f"{normalized_domain}/oauth2/token"

    if scope is None:
        scope = default_scope or ""

    if not client_id or not client_secret:
        raise RuntimeError(
            "Missing Cognito client credentials for Machine-to-Machine token exchange"
        )

    if not token_url:
        raise RuntimeError(
            "Unable to determine Cognito token URL. Provide token_url or ensure SSM configuration includes either cognito_token_url or domain."
        )

    if not scope:
        raise RuntimeError("Unable to determine OAuth scope for Machine-to-Machine token exchange")

    # OAuth2 Client Credentials grant
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "scope": scope,
    }

    try:
        response = requests.post(token_url, headers=headers, data=urlencode(data), timeout=10)
        response.raise_for_status()

        token_response = response.json()
        return str(token_response["access_token"])

    except requests.RequestException as e:
        raise RuntimeError(f"Failed to get M2M token: {e}") from e


def put_ssm_parameter(
    name: str, value: str, parameter_type: str = "String", with_encryption: bool = False
) -> None:
    """
    Store parameter in AWS Systems Manager Parameter Store.

    Args:
        name: Parameter name
        value: Parameter value
        parameter_type: 'String' or 'SecureString'
        with_encryption: Encrypt using AWS KMS

    Example:
        >>> put_ssm_parameter('/app/myagent/config/url', 'https://api.example.com')
    """
    ssm = boto3.client("ssm")

    put_params = {
        "Name": name,
        "Value": value,
        "Type": "SecureString" if with_encryption else parameter_type,
        "Overwrite": True,
    }

    ssm.put_parameter(**put_params)


def get_gateway_m2m_bearer_header(
    identity_cfg: Mapping[str, Any] | None,
    *,
    default_scope: str = "",
    logger: logging.Logger | None = None,
) -> str | None:
    """Return a "Bearer <token>" header value for Gateway access using M2M.

    This wrapper centralizes the common logic present in agent runtimes:
    it attempts to exchange client credentials for an OAuth2 access token
    using Cognito and returns a value suitable for the HTTP Authorization
    header. If required identity fields are missing or the exchange fails,
    it returns ``None``.

    The function intentionally swallows errors and logs at ``warning`` level so
    that agents can continue operating with local tools when M2M is not
    configured.

    Args:
        identity_cfg: Mapping that may contain keys such as ``client_id``,
            ``client_secret``, ``cognito_domain``/``domain``, optional ``scope``
            or ``cognito_token_url``.
        default_scope: Scope to use when ``scope`` is not provided.
        logger: Optional logger for informational/warning messages.

    Returns:
        A string in the form ``"Bearer <token>"`` on success; otherwise ``None``.
    """

    if not identity_cfg:
        return None

    log = logger or logging.getLogger(__name__)

    try:
        token = get_m2m_token(
            client_id=identity_cfg.get("client_id"),
            client_secret=identity_cfg.get("client_secret"),
            token_url=identity_cfg.get("cognito_token_url") or identity_cfg.get("token_url"),
            domain=identity_cfg.get("cognito_domain") or identity_cfg.get("domain"),
            scope=identity_cfg.get("scope", default_scope),
        )
        if token:
            log.info("Acquired Gateway M2M access token via client_credentials")
            return f"Bearer {token}"
    except Exception as exc:  # pragma: no cover - defensive path
        log.warning("M2M token acquisition failed: %s", exc)

    return None


def _get_m2m_bearer_token(identity_cfg: Mapping[str, Any], logger: logging.Logger) -> str | None:
    """Obtain a machine-to-machine OAuth2 access token via Cognito client credentials.

    This mirrors the helper used in agent runtimes and is provided here so
    agents can import a shared implementation with minimal changes.

    Expects identity_cfg to include Cognito domain, client_id and client_secret.
    Optionally, 'scope' may be provided; otherwise a reasonable default is used.

    Returns:
        str | None: "Bearer <token>" if a token could be acquired; otherwise None.
    """
    try:
        domain = identity_cfg.get("cognito_domain") or identity_cfg.get("domain")
        client_id = identity_cfg.get("client_id")
        client_secret = identity_cfg.get("client_secret")
        scope = identity_cfg.get("scope", "")

        if not (domain and client_id and client_secret):
            return None

        # Determine region for building a full Cognito domain when only a prefix is provided
        region = (
            identity_cfg.get("region")
            or identity_cfg.get("aws_region")
            or identity_cfg.get("cognito_region")
            or os.environ.get("AWS_REGION")
            or boto3.session.Session().region_name
            or "us-east-1"
        )

        normalized = str(domain).strip()
        if normalized.startswith(("http://", "https://")):
            token_base = normalized.rstrip("/")
        elif normalized.count(".") == 0:
            token_base = f"https://{normalized}.auth.{region}.amazoncognito.com"
        else:
            token_base = f"https://{normalized}".rstrip("/")

        token_url = token_base + "/oauth2/token"

        # Client credentials grant
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        if scope:  # Only include scope if explicitly provided
            data["scope"] = scope

        resp = requests.post(token_url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        token = resp.json().get("access_token")
        if token:
            logger.info("Acquired Gateway M2M access token via client_credentials")
            return f"Bearer {token}"
    except Exception as exc:  # pragma: no cover - defensive path
        logger.warning(f"M2M token acquisition failed: {exc}")
    return None


def resolve_authorization_header(
    context, identity_cfg: Mapping[str, Any] | None, logger: logging.Logger | None = None
) -> str | None:
    """Resolve Authorization header for Gateway access.

    Preference order:
    1) Caller-provided Authorization header from the runtime context
    2) M2M token derived from the provided ``identity_cfg`` via client credentials

    Args:
        context: Runtime context object that may have ``request_headers`` attribute
        identity_cfg: Mapping with identity settings (client_id, client_secret, domain, ...)
        logger: Optional logger to emit info/warn messages

    Returns:
        Authorization header value (e.g., ``"Bearer <token>"``) or ``None`` if unavailable.
    """

    log = logger or logging.getLogger(__name__)
    try:
        raw_headers = getattr(context, "request_headers", None) or {}
    except Exception:
        raw_headers = {}

    headers: dict[str, Any] = raw_headers if isinstance(raw_headers, dict) else {}
    auth_header = cast(str | None, headers.get("Authorization"))
    if auth_header:
        log.info("Using caller Authorization header for Gateway access")
        return auth_header

    # Fall back to M2M if configured
    bearer = _get_m2m_bearer_token(identity_cfg or {}, log)
    if bearer:
        log.info("Using M2M token for Gateway access (no caller token present)")
        return bearer

    return None
