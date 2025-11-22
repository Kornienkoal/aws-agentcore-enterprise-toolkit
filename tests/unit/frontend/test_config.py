"""Unit tests for configuration loader."""

from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError

from services.frontend_streamlit.config import (
    AppConfig,
    CognitoConfig,
    get_ssm_parameter,
    load_config,
)


@pytest.fixture
def mock_ssm_client():
    """Mock boto3 SSM client."""
    with patch("services.frontend_streamlit.config.boto3.client") as mock_client:
        yield mock_client.return_value


class TestGetSSMParameter:
    """Tests for SSM parameter retrieval."""

    def test_get_parameter_success(self, mock_ssm_client):
        """Test successful parameter retrieval."""
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "test-value"}}

        result = get_ssm_parameter("/test/param")
        assert result == "test-value"
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name="/test/param", WithDecryption=False
        )

    def test_get_parameter_with_decryption(self, mock_ssm_client):
        """Test parameter retrieval with decryption."""
        mock_ssm_client.get_parameter.return_value = {"Parameter": {"Value": "secret-value"}}

        result = get_ssm_parameter("/test/secret", with_decryption=True)
        assert result == "secret-value"
        mock_ssm_client.get_parameter.assert_called_once_with(
            Name="/test/secret", WithDecryption=True
        )

    def test_get_parameter_not_found(self, mock_ssm_client):
        """Test parameter not found error."""
        mock_ssm_client.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "ParameterNotFound"}}, "GetParameter"
        )

        with pytest.raises(RuntimeError, match="not found"):
            get_ssm_parameter("/test/missing")

    def test_get_parameter_other_error(self, mock_ssm_client):
        """Test other AWS errors."""
        mock_ssm_client.get_parameter.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied"}}, "GetParameter"
        )

        with pytest.raises(RuntimeError, match="Failed to retrieve"):
            get_ssm_parameter("/test/param")


class TestLoadConfig:
    """Tests for configuration loading."""

    @patch.dict("os.environ", {"AGENTCORE_ENV": "dev", "AWS_REGION": "us-east-1"})
    @patch("services.frontend_streamlit.config.get_ssm_parameter")
    def test_load_config_success(self, mock_get_param):
        """Test successful configuration loading."""
        # Clear cache
        load_config.cache_clear()

        # Mock SSM parameter responses
        param_values = {
            "/agentcore/dev/identity/pool_id": "us-east-1_ABC123",
            "/agentcore/dev/identity/frontend_client_id": "client123",
            "/agentcore/dev/identity/frontend_client_secret": "secret123",
            "/agentcore/dev/identity/domain": "myapp",
            "/agentcore/dev/gateway/invoke_url": "https://api.example.com",
            "/agentcore/dev/frontend-gateway/api_endpoint": "https://gateway.example.com",
        }

        # Mock function accepts but ignores with_decryption parameter
        def mock_fn(name: str, **_kwargs) -> str:
            return param_values[name]

        mock_get_param.side_effect = mock_fn

        config = load_config()

        assert isinstance(config, AppConfig)
        assert config.environment == "dev"
        assert config.cognito.pool_id == "us-east-1_ABC123"
        assert config.cognito.client_id == "client123"
        assert config.cognito.client_secret == "secret123"
        assert config.cognito.domain == "myapp"
        assert config.cognito.region == "us-east-1"
        assert config.gateway.invoke_url == "https://api.example.com"

    @patch("services.frontend_streamlit.config.get_ssm_parameter")
    def test_load_config_missing_parameter(self, mock_get_param):
        """Test configuration loading with missing parameter."""
        load_config.cache_clear()
        mock_get_param.side_effect = RuntimeError("Parameter not found")

        with pytest.raises(RuntimeError, match="Failed to load configuration"):
            load_config()

    def test_cognito_config_urls(self):
        """Test Cognito URL properties."""
        config = CognitoConfig(
            pool_id="us-east-1_ABC123",
            client_id="client123",
            client_secret="secret123",
            domain="myapp",
            region="us-east-1",
        )

        assert (
            config.authorize_url
            == "https://myapp.auth.us-east-1.amazoncognito.com/oauth2/authorize"
        )
        assert config.token_url == "https://myapp.auth.us-east-1.amazoncognito.com/oauth2/token"
        assert config.logout_url == "https://myapp.auth.us-east-1.amazoncognito.com/logout"
