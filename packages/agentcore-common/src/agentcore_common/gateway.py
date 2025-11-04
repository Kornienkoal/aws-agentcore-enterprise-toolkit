"""Gateway utilities for Amazon Bedrock AgentCore.

Lightweight helpers that do not introduce optional tool dependencies.

This module intentionally avoids importing optional MCP or Strands classes so
it can be reused from any runtime. It provides:

- Control plane helpers (e.g., ``get_gateway_url``)
- Tool filtering helpers that respect per‑agent ``allowed_tools`` lists
    regardless of whether configuration objects are dict-like or attribute-based.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import boto3


def get_gateway_url(gateway_id: str, *, region: str | None = None) -> str:
    """Return the Gateway URL for a given gateway identifier.

    Args:
        gateway_id: AgentCore Gateway identifier (from SSM / config)
        region: AWS region; if not provided, falls back to current session region

    Returns:
        Gateway URL string
    """

    resolved_region = region or boto3.session.Session().region_name or "us-east-1"
    control = boto3.client("bedrock-agentcore-control", region_name=resolved_region)
    resp = control.get_gateway(gatewayIdentifier=gateway_id)
    return str(resp["gatewayUrl"])


def _extract_allowed_tools(gateway_cfg: Any) -> list[str] | None:
    """Extract ``allowed_tools`` from a gateway config object or mapping.

    Supports both object-style (attributes) and dict-style configuration
    containers to be resilient to changes in config parsing libraries.
    """

    # Attribute-style (e.g., pydantic/attr objects)
    try:
        allowed = getattr(gateway_cfg, "allowed_tools", None)
    except Exception:  # pragma: no cover - defensive
        allowed = None

    # Mapping-style (plain dicts)
    if allowed is None and isinstance(gateway_cfg, dict):
        allowed = gateway_cfg.get("allowed_tools")

    # Normalize to list[str]
    if allowed is None:
        return None
    if isinstance(allowed, (list, tuple)):
        return [str(x) for x in allowed]
    # Anything else – best effort string split
    return [str(allowed)]


def filter_tools_by_allowed(
    tools: Iterable[Any],
    gateway_cfg: Any,
    logger: logging.Logger | None = None,
) -> list[Any]:
    """Filter a collection of tool objects by ``allowed_tools``.

    A tool object's name is resolved via ``getattr(tool, "name", None)`` or
    ``tool.get("name")`` if it is a mapping. If ``allowed_tools`` is not
    configured, the original list is returned unchanged.

    Args:
        tools: Iterable of tool objects (e.g., Strands Tool instances)
        gateway_cfg: The ``gateway`` section from agent config
        logger: Optional logger for summary output

    Returns:
        A concrete list containing only allowed tools (or all if not configured)
    """

    allowed = _extract_allowed_tools(gateway_cfg)
    tools_list = list(tools)

    if not allowed:
        if logger:
            logger.info(f"Loaded {len(tools_list)} Gateway tools")
        return tools_list

    allowed_set = set(allowed)

    def tool_name(obj: Any) -> str | None:
        # Common Strands Tool attribute
        name = getattr(obj, "name", None)
        if name is not None:
            return str(name)
        # Some wrappers use tool_name
        name = getattr(obj, "tool_name", None)
        if name is not None:
            return str(name)
        if isinstance(obj, dict):
            val = obj.get("name")
            return str(val) if val is not None else None
        return None

    def is_allowed(obj: Any) -> bool:
        n = tool_name(obj)
        if not n:
            return False
        if n in allowed_set:
            return True
        # Support MCP tool compound names like "web-search___web-search"
        base = n.split("___")[-1]
        return base in allowed_set

    filtered = [t for t in tools_list if is_allowed(t)]

    if logger:
        logger.info(
            f"Loaded {len(filtered)} Gateway tools (filtered from {len(tools_list)} available)"
        )
    return filtered
