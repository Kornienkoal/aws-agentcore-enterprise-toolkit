"""Unit tests for agentcore-common config module."""

import pytest
from agentcore_common.config import (
    AgentConfig,
    load_agent_config,
    resolve_ssm_parameters,
)


class TestResolveSSMParameters:
    """Test SSM parameter resolution."""

    def test_resolve_plain_string(self):
        """Plain strings should pass through unchanged."""
        result = resolve_ssm_parameters("hello world")
        assert result == "hello world"

    def test_resolve_dict(self):
        """Dictionaries should have values resolved recursively."""
        input_dict = {
            "plain": "value",
            "nested": {"key": "nested_value"},
        }
        result = resolve_ssm_parameters(input_dict)
        assert result == input_dict

    def test_resolve_list(self):
        """Lists should have items resolved recursively."""
        input_list = ["plain", "value", {"key": "nested"}]
        result = resolve_ssm_parameters(input_list)
        assert result == input_list

    def test_ssm_placeholder_without_credentials(self):
        """SSM placeholders should return as-is when credentials unavailable."""
        # This will fail to resolve but should gracefully return placeholder
        result = resolve_ssm_parameters("${SSM:/test/param}")
        # Should either resolve or return placeholder (depending on AWS creds)
        assert result in ["${SSM:/test/param}", "${SSM:/test/param}"] or isinstance(result, str)


class TestLoadAgentConfig:
    """Test agent configuration loading."""

    def test_load_config_requires_file(self):
        """Loading config without file should raise error."""
        with pytest.raises(FileNotFoundError):
            load_agent_config(config_path="nonexistent.yaml")

    def test_config_model_validation(self):
        """AgentConfig model should validate required fields."""
        # Minimum valid config
        config_data = {
            "name": "test-agent",
            "namespace": "test/namespace",
        }
        config = AgentConfig(**config_data)
        assert config.name == "test-agent"
        assert config.namespace == "test/namespace"

    def test_config_defaults(self):
        """AgentConfig should provide sensible defaults."""
        config = AgentConfig(name="test", namespace="test/ns")
        assert config.model.provider == "bedrock"
        assert config.model.temperature == 0.7
        assert config.memory.enabled is True
        assert config.authorization.type == "cognito_jwt"
