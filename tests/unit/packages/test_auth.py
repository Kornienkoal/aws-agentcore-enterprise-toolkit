"""Unit tests for agentcore-common auth module."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from agentcore_common.auth import get_m2m_token, get_ssm_parameter


class TestGetSSMParameter:
    """Test SSM parameter retrieval."""

    @patch("agentcore_common.auth.boto3.client")
    def test_get_parameter_success(self, mock_boto_client):
        """Should return parameter value on success."""
        mock_ssm = MagicMock()
        mock_ssm.get_parameter.return_value = {"Parameter": {"Value": "test-value"}}
        mock_boto_client.return_value = mock_ssm

        result = get_ssm_parameter("/test/param")

        assert result == "test-value"
        mock_ssm.get_parameter.assert_called_once_with(Name="/test/param", WithDecryption=True)

    @patch("agentcore_common.auth.boto3.client")
    def test_get_parameter_not_found(self, mock_boto_client):
        """Should raise ValueError when parameter not found."""
        mock_ssm = MagicMock()
        mock_ssm.exceptions.ParameterNotFound = Exception
        mock_ssm.get_parameter.side_effect = Exception("Not found")
        mock_boto_client.return_value = mock_ssm

        with pytest.raises(ValueError, match="SSM parameter not found"):
            get_ssm_parameter("/nonexistent/param")


class TestGetM2MToken:
    """Test M2M token retrieval."""

    @patch("agentcore_common.auth.requests.post")
    @patch("agentcore_common.auth.get_ssm_parameter")
    def test_get_token_success(self, mock_get_ssm, mock_post):
        """Should return access token on successful OAuth flow."""

        def fake_get_ssm(name, **_kwargs):
            mapping = {
                "/app/customersupport/agentcore/machine_client_id": "test-client-id",
                "/app/customersupport/agentcore/client_secret": "test-secret",
                "/app/customersupport/agentcore/cognito_token_url": "https://cognito.example.com/oauth2/token",
                "/app/customersupport/agentcore/cognito_auth_scope": "api/read api/write",
            }
            if name in mapping:
                return mapping[name]
            raise ValueError("SSM parameter not found")

        mock_get_ssm.side_effect = fake_get_ssm

        # Mock OAuth token response
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "test-token-12345"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = get_m2m_token()

        assert result == "test-token-12345"
        mock_post.assert_called_once()

    @patch("agentcore_common.auth.requests.post")
    @patch("agentcore_common.auth.get_ssm_parameter")
    def test_get_token_request_failure(self, mock_get_ssm, mock_post):
        """Should raise RuntimeError on request failure."""

        def fake_get_ssm(name, with_decryption=True):  # noqa: ARG001
            mapping = {
                "/app/customersupport/agentcore/machine_client_id": "client-id",
                "/app/customersupport/agentcore/client_secret": "secret",
                "/app/customersupport/agentcore/cognito_token_url": "https://token.url",
                "/app/customersupport/agentcore/cognito_auth_scope": "scope",
            }
            if name in mapping:
                return mapping[name]
            raise ValueError("SSM parameter not found")

        mock_get_ssm.side_effect = fake_get_ssm

        mock_post.side_effect = requests.RequestException("Network error")

        with pytest.raises(RuntimeError, match="Failed to get M2M token"):
            get_m2m_token()

    @patch("agentcore_common.auth.requests.post")
    @patch("agentcore_common.auth.get_ssm_parameter")
    def test_get_token_fallback_domain_default_scope(self, mock_get_ssm, mock_post):
        """Should derive token URL and scope when only domain is configured."""

        def fake_get_ssm(name, with_decryption=True):  # noqa: ARG001
            mapping = {
                "/agentcore/dev/identity/machine_client_id": "derived-client",
                "/agentcore/dev/identity/client_secret": "derived-secret",
                "/agentcore/dev/identity/domain": "agentcore-dev",
            }
            if name in mapping:
                return mapping[name]
            raise ValueError("SSM parameter not found")

        mock_get_ssm.side_effect = fake_get_ssm

        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "derived-token"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        token = get_m2m_token(ssm_prefix="/agentcore/dev/identity")

        assert token == "derived-token"

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://agentcore-dev.auth.us-east-1.amazoncognito.com/oauth2/token"
        # Ensure default scope is supplied in token request payload
        assert "scope=agentcore%2Finvoke" in kwargs["data"]
