"""Local runtime client for development - connects to local HTTP server instead of AWS."""

from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class LocalRuntimeClient:
    """Client for invoking local agent runtime server."""

    def __init__(
        self,
        runtime_name: str = "warranty-docs",
        base_url: str = "http://localhost:8000",
    ):
        """Initialize the local runtime client.

        Args:
            runtime_name: Name of the agent (for logging)
            base_url: Base URL of the local runtime server
        """
        self.runtime_name = runtime_name
        self.base_url = base_url
        self.invoke_url = f"{base_url}/invoke"
        logger.info(f"Initialized local runtime client: {self.invoke_url}")

    def invoke_agent(
        self,
        message: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Invoke the local agent runtime.

        Args:
            message: User's query
            user_id: User identifier (not used in local mode)
            session_id: Conversation session ID

        Returns:
            Agent response dictionary with 'output' field

        Raises:
            RuntimeError: If runtime invocation fails
        """
        try:
            logger.info(f"Invoking local runtime: {message[:50]}...")

            # Prepare payload
            payload = {
                "prompt": message,
            }

            # Call local server
            response = requests.post(
                self.invoke_url,
                json=payload,
                timeout=120,  # 2 minute timeout for Bedrock calls
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Local runtime returned status {response.status_code}: {response.text}"
                )

            result = response.json()

            if result.get("status") == "error":
                raise RuntimeError(f"Runtime error: {result.get('error')}")

            logger.info("Local runtime invocation successful")

            return {
                "output": result.get("output", ""),
                "session_id": session_id,
                "user_id": user_id,
            }

        except requests.exceptions.ConnectionError as err:
            raise RuntimeError(
                "Cannot connect to local runtime server. "
                "Make sure it's running: ./scripts/local/run-local-runtime-server.sh"
            ) from err
        except requests.exceptions.Timeout as err:
            raise RuntimeError(
                "Local runtime request timed out. The agent may be processing a long query."
            ) from err
        except Exception as e:
            logger.error(f"Unexpected error during local runtime invocation: {e}")
            raise RuntimeError(f"Unexpected error: {e}") from e


def get_local_runtime_client(
    runtime_name: str = "warranty-docs",
    base_url: str = "http://localhost:8000",
) -> LocalRuntimeClient:
    """Factory function to create a LocalRuntimeClient.

    Args:
        runtime_name: Name of the agent
        base_url: Base URL of the local runtime server

    Returns:
        Configured LocalRuntimeClient instance
    """
    return LocalRuntimeClient(runtime_name=runtime_name, base_url=base_url)
