"""Observability utilities for Amazon Bedrock AgentCore agents.

Provides helpers for:
- CloudWatch Logs integration
- X-Ray tracing
- Custom metrics
"""

import logging
import os

import boto3
from aws_xray_sdk.core import patch_all, xray_recorder


def setup_observability(
    agent_name: str,
    log_level: str = "INFO",
    enable_xray: bool = True,
    metrics_namespace: str | None = None,  # noqa: ARG001
) -> logging.Logger:
    """
    Configure observability for an agent.

    Sets up:
    - CloudWatch Logs with structured logging
    - AWS X-Ray tracing (optional)
    - Custom metrics namespace (optional)

    Args:
        agent_name: Agent name for log identification
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        enable_xray: Enable AWS X-Ray tracing
        metrics_namespace: CloudWatch metrics namespace

    Returns:
        Configured logger instance

    Example:
        >>> logger = setup_observability('customer-support', enable_xray=True)
        >>> logger.info("Agent started", extra={'user_id': '12345'})
    """
    # Configure logging
    logger = logging.getLogger(agent_name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Add CloudWatch handler if running in AWS
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # Enable X-Ray tracing
    if enable_xray:
        otel_enabled = str(os.getenv("AGENT_OBSERVABILITY_ENABLED", "")).lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

        if otel_enabled:
            logger.info("Skipping manual X-Ray setup because AGENT_OBSERVABILITY_ENABLED is true")
        else:
            daemon_address = os.environ.get("AWS_XRAY_DAEMON_ADDRESS") or "127.0.0.1:2000"

            try:
                patch_all()  # Patch boto3, requests, etc.

                # Configure X-Ray recorder
                # In local development, X-Ray daemon may not be running - that's ok
                xray_recorder.configure(
                    service=agent_name,
                    daemon_address=daemon_address,
                    sampling=True,
                    context_missing="IGNORE_ERROR",  # Suppress missing segment noise
                )
                logger.info("X-Ray tracing enabled")
            except Exception as e:
                logger.warning(f"Failed to enable X-Ray: {e}")

    return logger


def log_agent_invocation(
    logger: logging.Logger, user_id: str, session_id: str, prompt: str, **kwargs
) -> None:
    """
    Log agent invocation with structured data.

    Args:
        logger: Logger instance
        user_id: User identifier
        session_id: Session identifier
        prompt: User prompt
        **kwargs: Additional context
    """
    logger.info(
        "Agent invocation",
        extra={
            "user_id": user_id,
            "session_id": session_id,
            "prompt_length": len(prompt),
            **kwargs,
        },
    )


def put_metric(
    metric_name: str,
    value: float,
    namespace: str = "AgentCore",
    dimensions: dict[str, str] | None = None,
    unit: str = "None",
) -> None:
    """
    Publish custom metric to CloudWatch.

    Args:
        metric_name: Metric name
        value: Metric value
        namespace: CloudWatch namespace
        dimensions: Metric dimensions (e.g., {'AgentName': 'customer-support'})
        unit: Metric unit (Count, Seconds, Milliseconds, etc.)

    Example:
        >>> put_metric(
        ...     'ToolInvocations',
        ...     1,
        ...     dimensions={'AgentName': 'customer-support', 'ToolName': 'web_search'}
        ... )
    """
    cloudwatch = boto3.client("cloudwatch")

    metric_data = {"MetricName": metric_name, "Value": value, "Unit": unit}

    if dimensions:
        metric_data["Dimensions"] = [{"Name": k, "Value": v} for k, v in dimensions.items()]

    try:
        cloudwatch.put_metric_data(Namespace=namespace, MetricData=[metric_data])
    except Exception as e:
        # Don't fail on metrics errors
        logging.warning(f"Failed to publish metric: {e}")
