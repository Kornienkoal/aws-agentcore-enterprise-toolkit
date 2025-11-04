"""Unit tests for agentcore_common.auth helper behaviors added in refactor."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from agentcore_common.auth import resolve_authorization_header


class TestResolveAuthorizationHeader:
    """Tests for resolve_authorization_header preference order and fallbacks."""

    def test_prefers_caller_authorization_header(self):
        """Should return caller-provided Authorization header when present."""
        context = SimpleNamespace(request_headers={"Authorization": "Bearer caller-token"})

        with patch("agentcore_common.auth._get_m2m_bearer_token") as mock_m2m:
            result = resolve_authorization_header(context, {"client_id": "x"})

        assert result == "Bearer caller-token"
        mock_m2m.assert_not_called()

    def test_falls_back_to_m2m_when_no_caller_token(self):
        """Should call M2M helper and return its value if caller token missing."""
        context = SimpleNamespace(request_headers={})

        with patch(
            "agentcore_common.auth._get_m2m_bearer_token", return_value="Bearer m2m"
        ) as mock_m2m:
            result = resolve_authorization_header(
                context, {"client_id": "id", "client_secret": "sec", "domain": "example"}
            )

        assert result == "Bearer m2m"
        mock_m2m.assert_called_once()

    def test_returns_none_when_no_caller_and_m2m_unavailable(self):
        """Should return None if no caller header and M2M not configured/returns None."""
        context = SimpleNamespace(request_headers=None)

        with patch("agentcore_common.auth._get_m2m_bearer_token", return_value=None) as mock_m2m:
            result = resolve_authorization_header(context, None)

        assert result is None
        mock_m2m.assert_called_once()
