"""Unit tests for Gateway MCP tools (global-tools)."""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.parent


class TestToolSchemas:
    """Test Gateway tool schemas exist and are valid."""

    def test_service_locator_schema(self):
        """Service locator tool schema should exist and be valid."""
        schema_path = REPO_ROOT / "agents" / "global-tools" / "service_locator" / "tool-schema.json"
        assert schema_path.exists()

        with open(schema_path) as f:
            schema = json.load(f)

        # Verify MCP schema structure
        assert schema["name"] == "service-locator"
        assert "description" in schema
        assert "inputSchema" in schema
        assert schema["inputSchema"]["type"] == "object"
        assert "city" in schema["inputSchema"]["properties"]

    def test_check_warranty_schema(self):
        """Check warranty tool schema should exist and be valid."""
        schema_path = REPO_ROOT / "agents" / "global-tools" / "check_warranty" / "tool-schema.json"
        assert schema_path.exists()

        with open(schema_path) as f:
            schema = json.load(f)

        # Verify MCP schema structure
        assert schema["name"] == "check-warranty-status"
        assert "description" in schema
        assert "inputSchema" in schema

    def test_web_search_schema(self):
        """Web search tool schema should exist and be valid."""
        schema_path = REPO_ROOT / "agents" / "global-tools" / "web_search" / "tool-schema.json"
        assert schema_path.exists()

        with open(schema_path) as f:
            schema = json.load(f)

        # Verify MCP schema structure
        assert schema["name"] == "web-search"
        assert "description" in schema
        assert "inputSchema" in schema

    def test_all_schemas_use_hyphens(self):
        """All tool schemas should use hyphenated names (not underscores)."""
        tool_schemas = [
            REPO_ROOT / "agents" / "global-tools" / "service_locator" / "tool-schema.json",
            REPO_ROOT / "agents" / "global-tools" / "check_warranty" / "tool-schema.json",
            REPO_ROOT / "agents" / "global-tools" / "web_search" / "tool-schema.json",
        ]

        for schema_path in tool_schemas:
            with open(schema_path) as f:
                schema = json.load(f)

            # Tool name should not contain underscores
            assert "_" not in schema["name"], f"Tool name {schema['name']} contains underscore"
            # Tool name should contain hyphens (except single-word names)
            assert schema["name"].replace("-", "").isalnum()


class TestToolLambdaHandlers:
    """Test Gateway tool Lambda handlers exist."""

    def test_service_locator_handler_exists(self):
        """Service locator Lambda handler should exist."""
        handler_path = (
            REPO_ROOT / "agents" / "global-tools" / "service_locator" / "lambda_function.py"
        )
        assert handler_path.exists()

        # Read and verify handler function exists
        content = handler_path.read_text()
        assert "def handler(" in content

    def test_check_warranty_handler_exists(self):
        """Check warranty Lambda handler should exist."""
        handler_path = (
            REPO_ROOT / "agents" / "global-tools" / "check_warranty" / "lambda_function.py"
        )
        assert handler_path.exists()

        content = handler_path.read_text()
        assert "def handler(" in content

    def test_web_search_handler_exists(self):
        """Web search Lambda handler should exist."""
        handler_path = REPO_ROOT / "agents" / "global-tools" / "web_search" / "lambda_function.py"
        assert handler_path.exists()

        content = handler_path.read_text()
        assert "def handler(" in content
