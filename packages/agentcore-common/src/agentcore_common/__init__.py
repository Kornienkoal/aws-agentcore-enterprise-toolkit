"""AgentCore Common - Shared utilities for Amazon Bedrock AgentCore agents.

This package provides common functionality for:
- Authentication (Cognito M2M, OAuth2)
- Configuration (SSM Parameter Store)
- Observability (CloudWatch, X-Ray)
"""

__version__ = "0.1.0"

from .auth import (
    _get_m2m_bearer_token,
    get_gateway_m2m_bearer_header,
    get_m2m_token,
    get_ssm_parameter,
    resolve_authorization_header,
)
from .config import AgentConfig, load_agent_config
from .gateway import get_gateway_url
from .observability import setup_observability

__all__ = [
    "_get_m2m_bearer_token",
    "resolve_authorization_header",
    "get_m2m_token",
    "get_ssm_parameter",
    "get_gateway_m2m_bearer_header",
    "get_gateway_url",
    "load_agent_config",
    "AgentConfig",
    "setup_observability",
]
