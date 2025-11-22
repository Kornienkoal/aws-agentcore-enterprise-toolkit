"""Unit tests for authentication module."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from services.frontend_streamlit.auth import (
    build_authorization_url,
    build_logout_url,
    decode_id_token,
    exchange_code_for_tokens,
    generate_pkce_pair,
    refresh_access_token,
)


@pytest.fixture
def mock_config():
    """Mock application configuration."""
    with patch("services.frontend_streamlit.auth.load_config") as mock:
        config = MagicMock()
        config.cognito.client_id = "test-client-id"
        config.cognito.client_secret = "test-client-secret"
        config.cognito.authorize_url = (
            "https://test.auth.us-east-1.amazoncognito.com/oauth2/authorize"
        )
        config.cognito.token_url = "https://test.auth.us-east-1.amazoncognito.com/oauth2/token"
        config.cognito.logout_url = "https://test.auth.us-east-1.amazoncognito.com/logout"
        mock.return_value = config
        yield mock


class TestPKCE:
    """Tests for PKCE generation."""

    def test_generate_pkce_pair(self):
        """Test PKCE code verifier and challenge generation."""
        verifier, challenge = generate_pkce_pair()

        # Verifier should be base64 URL-safe without padding
        assert len(verifier) > 40
        assert "=" not in verifier

        # Challenge should be base64 URL-safe without padding
        assert len(challenge) > 40
        assert "=" not in challenge

        # Should generate different values each time
        verifier2, challenge2 = generate_pkce_pair()
        assert verifier != verifier2
        assert challenge != challenge2


class TestAuthorizationURL:
    """Tests for authorization URL building.

    Note: mock_config fixture mocks SSM config loading during module import.
    """

    def test_build_authorization_url(self, mock_config):  # noqa: ARG002
        """Test building OAuth2 authorization URL with PKCE."""
        url = build_authorization_url(
            state="test-state",
            code_challenge="test-challenge",
            redirect_uri="http://localhost:8501",
        )

        assert "https://test.auth.us-east-1.amazoncognito.com/oauth2/authorize?" in url
        assert "response_type=code" in url
        assert "client_id=test-client-id" in url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A8501" in url
        assert "state=test-state" in url
        assert "code_challenge=test-challenge" in url
        assert "code_challenge_method=S256" in url
        assert "scope=openid+email+profile" in url

    def test_build_logout_url(self, mock_config):  # noqa: ARG002
        """Test building logout URL."""
        url = build_logout_url(redirect_uri="http://localhost:8501")

        assert "https://test.auth.us-east-1.amazoncognito.com/logout?" in url
        assert "client_id=test-client-id" in url
        assert "logout_uri=http%3A%2F%2Flocalhost%3A8501" in url


class TestTokenExchange:
    """Tests for OAuth2 token exchange."""

    @patch("services.frontend_streamlit.auth.requests.post")
    def test_exchange_code_success(self, mock_post, mock_config):  # noqa: ARG002
        """Test successful token exchange."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "access123",
            "id_token": "id123",
            "refresh_token": "refresh123",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tokens = exchange_code_for_tokens(
            authorization_code="code123",
            code_verifier="verifier123",
            redirect_uri="http://localhost:8501",
        )

        assert tokens.access_token == "access123"
        assert tokens.id_token == "id123"
        assert tokens.refresh_token == "refresh123"
        assert tokens.expires_in == 3600

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["headers"]["Content-Type"] == "application/x-www-form-urlencoded"
        assert "Basic" in call_kwargs["headers"]["Authorization"]
        assert call_kwargs["data"]["grant_type"] == "authorization_code"
        assert call_kwargs["data"]["code"] == "code123"
        assert call_kwargs["data"]["code_verifier"] == "verifier123"

    @patch("services.frontend_streamlit.auth.requests.post")
    def test_exchange_code_http_error(self, mock_post, mock_config):  # noqa: ARG002
        """Test token exchange with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_response.json.return_value = {"error_description": "Invalid code"}
        mock_response.text = '{"error_description": "Invalid code"}'
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Authentication failed"):
            exchange_code_for_tokens(
                authorization_code="bad-code",
                code_verifier="verifier",
                redirect_uri="http://localhost:8501",
            )

    @patch("services.frontend_streamlit.auth.requests.post")
    def test_exchange_code_network_error(self, mock_post, mock_config):  # noqa: ARG002
        """Test token exchange with network error."""
        mock_post.side_effect = requests.RequestException("Network error")

        with pytest.raises(ValueError, match="Network error"):
            exchange_code_for_tokens(
                authorization_code="code",
                code_verifier="verifier",
                redirect_uri="http://localhost:8501",
            )


class TestTokenRefresh:
    """Tests for token refresh."""

    @patch("services.frontend_streamlit.auth.requests.post")
    def test_refresh_success(self, mock_post, mock_config):  # noqa: ARG002
        """Test successful token refresh."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new-access",
            "id_token": "new-id",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        tokens = refresh_access_token(refresh_token="refresh123")

        assert tokens.access_token == "new-access"
        assert tokens.id_token == "new-id"
        assert tokens.refresh_token == "refresh123"  # Should use original if not returned

    @patch("services.frontend_streamlit.auth.requests.post")
    def test_refresh_failure(self, mock_post, mock_config):  # noqa: ARG002
        """Test token refresh failure."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Session expired"):
            refresh_access_token(refresh_token="invalid-refresh")


class TestTokenDecoding:
    """Tests for ID token decoding."""

    @patch("services.frontend_streamlit.auth.jwt.decode")
    def test_decode_id_token(self, mock_decode):
        """Test decoding ID token claims."""
        mock_decode.return_value = {
            "sub": "user-123",
            "email": "test@example.com",
            "cognito:username": "testuser",
        }

        claims = decode_id_token("fake-jwt-token")

        assert claims["sub"] == "user-123"
        assert claims["email"] == "test@example.com"
        assert claims["cognito:username"] == "testuser"

        # Should decode without verification (API Gateway verifies)
        mock_decode.assert_called_once()
        assert mock_decode.call_args[1]["options"]["verify_signature"] is False
