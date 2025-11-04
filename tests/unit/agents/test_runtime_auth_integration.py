"""Unit tests covering runtime auth/gateway integration for both agents.

These tests verify that runtimes use shared helpers:
- agentcore_common.gateway.get_gateway_url
- agentcore_common.auth.resolve_authorization_header

And that MCP tool loading is attempted only when an Authorization value
is available (either caller-provided or M2M fallback).
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _add_agent_to_path(agent_name: str):
    agent_path = Path(__file__).parent.parent.parent.parent / "agents" / agent_name
    sys.path.insert(0, str(agent_path))
    return agent_path


class FakeAgent:
    def __init__(self, model=None, tools=None, system_prompt=None):  # noqa: D401, ARG002
        self.tools = tools or []

    def __call__(self, user_input):  # noqa: D401, ARG002
        # Minimal response structure expected by runtime
        # Runtime accesses response.message["content"][0]["text"],
        # so we return an object with a `.message` attribute.
        return SimpleNamespace(message={"content": [{"text": "ok"}]})


def _run_coro_in_thread(coro):
    """Run an async coroutine in a dedicated thread to avoid nested event-loop conflicts."""
    import asyncio
    import threading

    result = {}
    error = {}

    def _target():
        try:
            result["value"] = asyncio.run(coro)
        except BaseException as exc:  # noqa: BLE001
            error["exc"] = exc

    t = threading.Thread(target=_target)
    t.start()
    t.join()

    if "exc" in error:
        raise error["exc"]
    return result.get("value")


@pytest.mark.parametrize("agent_name", ["customer-support", "warranty-docs"])
def test_invoke_attempts_mcp_when_auth_available(agent_name):
    """When resolve_authorization_header returns a token, runtime attempts MCP list_tools."""
    agent_path = _add_agent_to_path(agent_name)

    with (
        patch("agentcore_tools.runtime.load_agent_config") as mock_load_config,
        patch("agentcore_tools.runtime.setup_observability", return_value=MagicMock()),
        patch(
            "agentcore_tools.runtime.get_gateway_url", return_value="https://gw.example.com"
        ) as mock_gw,
        patch(
            "agentcore_tools.runtime.resolve_authorization_header", return_value="Bearer caller"
        ) as mock_resolve,
        patch("agentcore_tools.runtime.BedrockModel"),
        patch("agentcore_tools.runtime.Agent", FakeAgent),
        patch("agentcore_tools.runtime.create_mcp_client") as mock_mcp,
    ):
        # Minimal config
        cfg = MagicMock()
        cfg.name = agent_name
        cfg.model.model_id = "test-model"
        cfg.model.temperature = 0.1
        cfg.model.max_tokens = 100
        cfg.system_prompt = "prompt"
        cfg.runtime.region = "us-east-1"
        cfg.gateway = {"gateway_id": "gw-123"}
        cfg.identity = {"client_id": "c", "client_secret": "s", "domain": "d"}
        cfg.observability = {"log_level": "INFO", "xray_tracing": False}
        mock_load_config.return_value = cfg

        # MCPClient context manager mock
        mcp_inst = MagicMock()
        mcp_inst.__enter__.return_value = mcp_inst
        mcp_inst.__exit__.return_value = False
        mcp_inst.list_tools_sync.return_value = []
        mock_mcp.return_value = mcp_inst

        # Import runtime after patches are in place
        try:
            import importlib

            # Ensure we import the correct agent runtime each time
            if "runtime" in sys.modules:
                del sys.modules["runtime"]
            # Also clear any cached local tools packages from previous agent import
            for mod in list(sys.modules.keys()):
                if mod == "tools" or mod.startswith("tools."):
                    del sys.modules[mod]
            runtime = importlib.import_module("runtime")
        finally:
            # Clean path to avoid leakage across tests
            if str(agent_path) in sys.path:
                sys.path.remove(str(agent_path))

        # Call invoke with minimal payload and dummy context
        context = SimpleNamespace(request_headers={"Authorization": "Bearer external"})
        res = _run_coro_in_thread(runtime.invoke({"prompt": "hi"}, context=context))

        assert res == "ok"
        mock_gw.assert_called_once_with("gw-123", region="us-east-1")
        mock_resolve.assert_called()
        mock_mcp.assert_called_once()  # Attempted to load MCP tools


@pytest.mark.parametrize("agent_name", ["customer-support", "warranty-docs"])
def test_invoke_skips_mcp_when_no_auth(agent_name):
    """When no Authorization (caller or M2M), runtime should not instantiate MCPClient."""
    agent_path = _add_agent_to_path(agent_name)

    with (
        patch("agentcore_tools.runtime.load_agent_config") as mock_load_config,
        patch("agentcore_tools.runtime.setup_observability", return_value=MagicMock()),
        patch("agentcore_tools.runtime.get_gateway_url", return_value="https://gw.example.com"),
        patch("agentcore_tools.runtime.resolve_authorization_header", return_value=None),
        patch("agentcore_tools.runtime.BedrockModel"),
        patch("agentcore_tools.runtime.Agent", FakeAgent),
        patch("agentcore_tools.runtime.create_mcp_client") as mock_mcp,
    ):
        # Minimal config
        cfg = MagicMock()
        cfg.name = agent_name
        cfg.model.model_id = "test-model"
        cfg.model.temperature = 0.1
        cfg.model.max_tokens = 100
        cfg.system_prompt = "prompt"
        cfg.runtime.region = "us-east-1"
        cfg.gateway = {"gateway_id": "gw-123"}
        cfg.identity = {}
        cfg.observability = {"log_level": "INFO", "xray_tracing": False}
        mock_load_config.return_value = cfg

        # Import runtime
        try:
            import importlib

            # Ensure we import the correct agent runtime each time
            if "runtime" in sys.modules:
                del sys.modules["runtime"]
            # Also clear any cached local tools packages from previous agent import
            for mod in list(sys.modules.keys()):
                if mod == "tools" or mod.startswith("tools."):
                    del sys.modules[mod]
            runtime = importlib.import_module("runtime")
        finally:
            if str(agent_path) in sys.path:
                sys.path.remove(str(agent_path))

        # Invoke without Authorization
        context = SimpleNamespace(request_headers={})
        res = _run_coro_in_thread(runtime.invoke({"prompt": "hi"}, context=context))

        assert res == "ok"
        mock_mcp.assert_not_called()
