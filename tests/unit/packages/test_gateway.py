"""Unit tests for agentcore_common.gateway helpers added in refactor."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agentcore_common.gateway import get_gateway_url


def test_get_gateway_url_calls_control_and_returns_url():
    """Should call bedrock-agentcore-control and return gatewayUrl as string."""
    with patch("agentcore_common.gateway.boto3.client") as mock_client:
        mock_ctrl = MagicMock()
        mock_ctrl.get_gateway.return_value = {"gatewayUrl": "https://gw.example.com"}
        mock_client.return_value = mock_ctrl

        url = get_gateway_url("gw-123", region="us-east-1")

        assert url == "https://gw.example.com"
        mock_client.assert_called_once_with("bedrock-agentcore-control", region_name="us-east-1")
        mock_ctrl.get_gateway.assert_called_once_with(gatewayIdentifier="gw-123")
