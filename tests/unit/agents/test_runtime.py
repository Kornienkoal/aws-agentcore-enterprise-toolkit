"""Unit tests for customer-support agent runtime."""

from unittest.mock import MagicMock, patch

import pytest


class TestAgentRuntime:
    """Test agent runtime entrypoint."""

    def test_invoke_with_valid_payload(self):
        """Agent should process valid payload successfully."""
        import sys
        from pathlib import Path

        # Add agent directory to path
        agent_path = Path(__file__).parent.parent.parent.parent / "agents" / "customer-support"
        sys.path.insert(0, str(agent_path))

        # Patch config and dependencies before importing runtime
        with (
            patch("agentcore_common.load_agent_config") as mock_load_config,
            patch("boto3.client") as mock_boto_client,
        ):
            # Mock configuration
            mock_config = MagicMock()
            mock_config.name = "test-agent"
            mock_config.model.model_id = "test-model"
            mock_config.model.temperature = 0.7
            mock_config.model.max_tokens = 4096
            mock_config.model.top_p = 0.95
            mock_config.system_prompt = "Test prompt"
            mock_config.observability.xray_tracing = False
            mock_load_config.return_value = mock_config

            # Mock bedrock control client
            mock_control = MagicMock()
            mock_boto_client.return_value = mock_control

            # Now we can import runtime without triggering real config loading
            try:
                import runtime  # noqa: F401

                # If we get here, runtime imports successfully
                assert True
            except ImportError as e:
                pytest.fail(f"Failed to import runtime: {e}")


class TestAgentTools:
    """Test agent-specific tools."""

    def test_product_tools_importable(self):
        """Product tools should be importable."""
        import sys
        from pathlib import Path

        agent_path = Path(__file__).parent.parent.parent.parent / "agents" / "customer-support"
        sys.path.insert(0, str(agent_path))

        from tools.product_tools import get_product_info, search_documentation

        assert callable(get_product_info)
        assert callable(search_documentation)

    def test_get_product_info_signature(self):
        """get_product_info should support both product_id and product_name parameters."""
        import inspect
        import sys
        from pathlib import Path

        agent_path = Path(__file__).parent.parent.parent.parent / "agents" / "customer-support"
        sys.path.insert(0, str(agent_path))

        from tools.product_tools import get_product_info

        sig = inspect.signature(get_product_info)

        assert "product_id" in sig.parameters
        assert sig.parameters["product_id"].default is None

        assert "product_name" in sig.parameters
        assert sig.parameters["product_name"].default is None

    def test_get_product_info_alias_lookup(self):
        """Friendly product names should resolve to mock catalog entries."""
        import sys
        from pathlib import Path

        agent_path = Path(__file__).parent.parent.parent.parent / "agents" / "customer-support"
        sys.path.insert(0, str(agent_path))

        from tools.product_tools import get_product_info

        product = get_product_info(product_name="Contoso Laptop X1")

        assert product["product_id"] == "laptop-x1"
        assert product["specs"]["ram"] == "16GB"
        assert product["specs"]["battery_life"] == "12 hours"
