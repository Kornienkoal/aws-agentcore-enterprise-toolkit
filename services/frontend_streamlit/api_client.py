"""HTTP client helpers for interacting with AgentCore Gateway."""

from __future__ import annotations

import logging
from typing import Any

import requests

from .config import load_config

logger = logging.getLogger(__name__)


class AgentGatewayClient:
    """Client for invoking the AgentCore agent via API Gateway."""

    def __init__(self, id_token: str | None = None):
        """Initialize the client.

        Args:
            id_token: Cognito ID token for authorization (optional, can be set per request)
        """
        self.config = load_config()
        self.id_token = id_token
        self.base_url = self.config.gateway.invoke_url

    def invoke_agent(
        self,
        message: str,
        user_id: str,
        session_id: str,
        id_token: str | None = None,
    ) -> dict[str, Any]:
        """Invoke the customer support agent.

        Args:
            message: User's query
            user_id: Cognito user identifier (sub claim)
            session_id: Conversation session ID
            id_token: Cognito ID token (overrides instance token if provided)

        Returns:
            Agent response as dictionary

        Raises:
            requests.HTTPError: If API call fails
            ValueError: If no ID token provided
        """
        token = id_token or self.id_token
        if not token:
            raise ValueError("ID token required for agent invocation")

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "message": message,
        }

        logger.info(f"Invoking agent for user {user_id}, session {session_id}")

        try:
            response = requests.post(
                f"{self.base_url}/invoke",
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            logger.error(f"Agent invocation failed: {e}")
            if e.response.status_code == 401:
                raise ValueError("Token expired or invalid. Please log in again.") from e
            if e.response.status_code == 429:
                raise ValueError("Too many requests. Please wait a moment and try again.") from e
            if e.response.status_code >= 500:
                raise ValueError(
                    "Agent service is temporarily unavailable. Please try again later."
                ) from e
            raise
        except requests.Timeout:
            logger.error("Agent invocation timed out")
            raise ValueError(
                "Request timed out. The agent is taking longer than expected."
            ) from None
        except requests.RequestException as e:
            logger.error(f"Network error during agent invocation: {e}")
            raise ValueError("Network error. Please check your connection and try again.") from e


def get_gateway_client(id_token: str | None = None) -> AgentGatewayClient:
    """Factory function to create an AgentGatewayClient.

    Args:
        id_token: Optional Cognito ID token for authorization

    Returns:
        Configured AgentGatewayClient instance
    """
    return AgentGatewayClient(id_token=id_token)
