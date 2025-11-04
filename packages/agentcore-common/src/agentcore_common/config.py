"""Configuration management for Amazon Bedrock AgentCore agents.

Loads and validates agent configuration from YAML files.
Supports environment-specific overrides and SSM parameter resolution.
"""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from .auth import get_ssm_parameter


class ModelConfig(BaseModel):
    """LLM model configuration."""

    provider: str = "bedrock"
    model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    temperature: float = 0.7
    max_tokens: int = 4096


class ToolsConfig(BaseModel):
    """Agent tools configuration."""

    # Allow both string names and dict configs for gateway_targets
    gateway_targets: list[Any] = Field(default_factory=list)
    local_tools: list[dict[str, Any]] = Field(default_factory=list)
    identity_aware_tools: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"extra": "allow"}


class MemoryConfig(BaseModel):
    """Memory configuration."""

    enabled: bool = True
    memory_id: str | None = None
    strategies: list[str] = Field(
        default_factory=lambda: [
            "userPreferenceMemoryStrategy",
            "semanticMemoryStrategy",
        ]
    )
    ttl_days: int = 30


class AuthorizationConfig(BaseModel):
    """Authorization configuration."""

    type: str = "cognito_jwt"
    client_id: str | None = None
    discovery_url: str | None = None
    web_client_id: str | None = None
    redirect_uri: str | None = None


class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    enabled: bool = True
    cloudwatch_logs: bool = True
    xray_tracing: bool = True
    metrics_namespace: str = "AgentCore"


class RuntimeConfig(BaseModel):
    """Runtime configuration."""

    execution_role: str | None = None
    region: str = "us-east-1"
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)


class AgentConfig(BaseModel):
    """Complete agent configuration."""

    name: str
    namespace: str = "app/default"
    description: str = ""
    system_prompt: str = ""
    model: ModelConfig = Field(default_factory=ModelConfig)
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    authorization: AuthorizationConfig = Field(default_factory=AuthorizationConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)

    # Additional fields from YAML
    environment: dict[str, Any] = Field(default_factory=dict)
    gateway: dict[str, Any] = Field(default_factory=dict)
    identity: dict[str, Any] = Field(default_factory=dict)
    observability: dict[str, Any] = Field(default_factory=dict)

    # Allow extra fields from YAML
    model_config = {"extra": "allow"}


def resolve_ssm_parameters(value: Any, region: str = "us-east-1") -> Any:
    """
    Recursively resolve ${SSM:parameter_name} placeholders.

    Example:
        >>> value = "${SSM:/agentcore/dev/gateway/gateway_id}"
        >>> resolve_ssm_parameters(value)
        'agentcoregatewaydev-tapkcg7c6u'
    """
    if isinstance(value, str):
        if value.startswith("${SSM:") and value.endswith("}"):
            param_name = value[6:-1]  # Extract parameter name
            try:
                return get_ssm_parameter(param_name)
            except Exception as e:
                # Parameter not found or AWS credentials issue
                # Return placeholder as-is for graceful degradation
                # This allows local testing without AWS credentials
                import logging

                logging.warning(f"Could not resolve SSM parameter {param_name}: {e}")
                return value
        return value
    elif isinstance(value, dict):
        return {k: resolve_ssm_parameters(v, region) for k, v in value.items()}
    elif isinstance(value, list):
        return [resolve_ssm_parameters(item, region) for item in value]
    return value


def load_agent_config(
    config_path: str | None = None,
    agent_name: str | None = None,
    environment: str | None = None,
) -> AgentConfig:
    """
    Load and validate agent configuration from YAML file.

    Args:
        config_path: Path to config file (defaults to agent-config/{agent_name}.yaml)
        agent_name: Agent name (used if config_path not provided)
        environment: Environment name for overrides (dev/staging/prod)

    Returns:
        Validated AgentConfig instance

    Raises:
        FileNotFoundError: If config file not found
        ValueError: If configuration is invalid

    Example:
        >>> config = load_agent_config(agent_name='customer-support')
        >>> print(config.model.model_id)
        'anthropic.claude-3-7-sonnet-20250219-v1:0'
    """
    # Determine config path
    if not config_path:
        if not agent_name:
            agent_name = os.getenv("AGENT_NAME", "default")

        # Look for config in standard location
        config_path = f"../../agent-config/{agent_name}.yaml"

        # If not found, try relative to current working directory
        if not Path(config_path).exists():
            config_path = f"agent-config/{agent_name}.yaml"

    # Load YAML
    with open(config_path) as f:
        raw_config = yaml.safe_load(f)

    # Extract agent section
    agent_config = raw_config.get("agent", {})

    # Merge top-level keys that aren't 'agent' into agent_config
    # This handles keys like 'environment', 'model', 'system_prompt', 'gateway', etc.
    for key, value in raw_config.items():
        if key != "agent" and key not in agent_config:
            agent_config[key] = value

    # Apply environment-specific overrides
    if environment:
        env_overrides = agent_config.get("runtime", {}).get("environments", {}).get(environment, {})
        # Merge environment overrides (simplified - could use deep merge)
        for key, value in env_overrides.items():
            if "." in key:
                # Handle nested keys (e.g., 'model.model_id')
                parts = key.split(".")
                current = agent_config
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                current[parts[-1]] = value
            else:
                agent_config[key] = value

    # Resolve SSM parameters
    agent_config = resolve_ssm_parameters(agent_config)

    # Validate and return
    return AgentConfig(**agent_config)
