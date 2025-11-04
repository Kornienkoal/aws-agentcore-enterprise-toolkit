"""AgentCore Runtime client for invoking deployed agents."""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import Any

import boto3
import streamlit as st
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Cache the runtime ARN in session state to avoid repeated control plane lookups
_RUNTIME_ARN_CACHE_KEY = "agentcore_runtime_arn_cache"
_GLOBAL_RUNTIME_ARN_CACHE: dict[str, str] = {}


def _canonical_runtime_name(name: str) -> str:
    """Normalise runtime identifiers for comparison.

    Strips non-alphanumeric characters and lowercases the result so that
    names such as ``customer-support``, ``customer_support`` and
    ``CustomerSupport`` collapse to the same canonical representation.
    """

    return "".join(ch for ch in name.lower() if ch.isalnum())


def _get_runtime_cache() -> dict[str, str]:
    """Return the runtime ARN cache, preferring Streamlit session state.

    When executed outside of a Streamlit script (e.g., during unit tests),
    ``st.session_state`` is not available. In that scenario we fall back to a
    module-level dictionary so that the client remains usable.
    """

    try:
        return st.session_state.setdefault(_RUNTIME_ARN_CACHE_KEY, {})
    except RuntimeError:
        return _GLOBAL_RUNTIME_ARN_CACHE


class AgentCoreRuntimeClient:
    """Client for invoking AgentCore Runtime."""

    def __init__(
        self,
        runtime_name: str = "customersupport",
        runtime_arn: str | None = None,
        region: str = "us-east-1",
    ):
        """Initialize the runtime client.

        Args:
            runtime_name: Name of the AgentCore runtime (used to look up ARN)
            runtime_arn: AgentCore Runtime ARN (if None, fetches from control plane)
            region: AWS region
        """
        self.region = region
        self.runtime_name = runtime_name
        self.runtime_client = boto3.client("bedrock-agentcore", region_name=region)

        # Get runtime ARN if not provided
        if runtime_arn is None:
            cache = _get_runtime_cache()
            cache_key = _canonical_runtime_name(self.runtime_name)

            if cache_key in cache:
                runtime_arn = cache[cache_key]
                logger.info(f"Using cached runtime ARN for '{self.runtime_name}': {runtime_arn}")
            else:
                runtime_arn = self._get_runtime_arn()
                cache[cache_key] = runtime_arn

        self.runtime_arn = runtime_arn
        logger.info(f"Initialized runtime client for: {runtime_arn}")

    def _get_runtime_arn(self) -> str:
        """Fetch runtime ARN from AgentCore control plane.

        Returns:
            Runtime ARN

        Raises:
            RuntimeError: If runtime not found or AWS credentials expired
        """
        try:
            control_client = boto3.client("bedrock-agentcore-control", region_name=self.region)
            response = control_client.list_agent_runtimes()

            target_name_canonical = _canonical_runtime_name(self.runtime_name)

            # Find runtime by name (supporting hyphen/underscore variations)
            candidates = response.get("agentRuntimes", [])

            for runtime in candidates:
                runtime_name = runtime.get("agentRuntimeName", "")
                if _canonical_runtime_name(runtime_name) == target_name_canonical:
                    # Update runtime name to the exact control-plane identifier
                    self.runtime_name = runtime_name
                    # Cache canonical name for future lookups
                    cache = _get_runtime_cache()
                    cache[_canonical_runtime_name(runtime_name)] = runtime["agentRuntimeArn"]
                    return runtime["agentRuntimeArn"]

            for runtime in response.get("agentRuntimes", []):
                if runtime.get("agentRuntimeName") == self.runtime_name:
                    return runtime["agentRuntimeArn"]

            available = [r.get("agentRuntimeName", "<unknown>") for r in candidates if r]

            # If there is exactly one runtime available, fall back to it automatically
            if len(candidates) == 1:
                fallback = candidates[0]
                fallback_name = fallback.get("agentRuntimeName", "")
                fallback_arn = fallback.get("agentRuntimeArn")

                if fallback_name and fallback_arn:
                    logger.warning(
                        "Runtime '%s' not found. Falling back to '%s'.",
                        self.runtime_name,
                        fallback_name,
                    )
                    self.runtime_name = fallback_name
                    cache = _get_runtime_cache()
                    cache[_canonical_runtime_name(fallback_name)] = fallback_arn

                    # Update Streamlit session state selection if available
                    with suppress(RuntimeError):
                        st.session_state["selected_agent"] = fallback_name.replace("_", "-")

                    return fallback_arn

            raise RuntimeError(
                f"Runtime '{self.runtime_name}' not found. Available runtimes: "
                + (", ".join(available) or "<none>")
            )
        except ClientError as e:
            raise RuntimeError(f"Failed to fetch runtime ARN: {e}") from e

    def invoke_agent(
        self,
        message: str,
        user_id: str,
        session_id: str,
    ) -> dict[str, Any]:
        """Invoke the AgentCore Runtime.

        Args:
            message: User's query
            user_id: User identifier
            session_id: Conversation session ID

        Returns:
            Agent response dictionary with 'output' field

        Raises:
            RuntimeError: If runtime invocation fails
        """
        import json

        try:
            logger.info(f"Invoking runtime for user {user_id}, session {session_id}")

            # Prepare payload as JSON bytes
            payload_dict = {
                "prompt": message,
            }
            payload_bytes = json.dumps(payload_dict).encode("utf-8")

            response = self.runtime_client.invoke_agent_runtime(
                agentRuntimeArn=self.runtime_arn,
                runtimeUserId=user_id,
                runtimeSessionId=session_id,
                contentType="application/json",
                accept="application/json",
                payload=payload_bytes,
            )

            # Extract output from response field (StreamingBody)
            response_body = response.get("response")
            if response_body:
                # Response is a StreamingBody, read it
                output = response_body.read().decode("utf-8")
                # Remove surrounding quotes if present
                if output.startswith('"') and output.endswith('"'):
                    output = output[1:-1]
            else:
                output = ""

            logger.info("Runtime invocation successful")

            return {
                "output": output,
                "session_id": session_id,
                "user_id": user_id,
            }

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_msg = e.response["Error"]["Message"]

            logger.error(f"Runtime invocation failed: {error_code} - {error_msg}")

            if error_code == "AccessDeniedException":
                raise RuntimeError(
                    "Access denied. Ensure you have permission to invoke the runtime."
                ) from e
            elif error_code == "ResourceNotFoundException":
                raise RuntimeError(
                    f"Runtime not found: {self.runtime_arn}. Verify the runtime is deployed."
                ) from e
            elif error_code == "ThrottlingException":
                raise RuntimeError("Too many requests. Please wait a moment and try again.") from e
            else:
                raise RuntimeError(f"Runtime error: {error_msg}") from e

        except Exception as e:
            logger.error(f"Unexpected error during runtime invocation: {e}")
            raise RuntimeError(f"Unexpected error: {e}") from e


def get_runtime_client(
    runtime_name: str | None = None,
    runtime_arn: str | None = None,
) -> AgentCoreRuntimeClient:
    """Factory function to create an AgentCoreRuntimeClient.

    Args:
        runtime_name: Name of the AgentCore runtime (if None, reads from session state)
        runtime_arn: Optional runtime ARN (if None, fetches from control plane)

    Returns:
        Configured AgentCoreRuntimeClient instance

    Note:
        Phase 2: Reads selected_agent from session state if runtime_name is None.
        Agent selector in main.py stores the choice in st.session_state.selected_agent.
        Full runtime switching behavior will be implemented in Phase 3 (T020).
    """
    # Read selected agent from session state if not provided
    if runtime_name is None:
        runtime_name = st.session_state.get("selected_agent", "customer-support")
        logger.info(f"Using selected agent from session state: {runtime_name}")

    return AgentCoreRuntimeClient(runtime_name=runtime_name, runtime_arn=runtime_arn)
