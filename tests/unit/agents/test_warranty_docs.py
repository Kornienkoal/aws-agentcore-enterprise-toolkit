"""Unit tests for warranty-docs agent runtime and tools."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def warranty_docs_path():
    """Add warranty-docs agent to path for imports and clear cached modules."""
    agent_path = Path(__file__).parent.parent.parent.parent / "agents" / "warranty-docs"

    # Clear any cached tool modules from other agents
    modules_to_clear = [key for key in sys.modules if key == "tools" or key.startswith("tools.")]
    for module in modules_to_clear:
        del sys.modules[module]

    # Insert warranty-docs path at front
    sys.path.insert(0, str(agent_path))
    yield

    # Clean up
    if str(agent_path) in sys.path:
        sys.path.remove(str(agent_path))


class TestProductTools:
    """Test warranty-docs product tools."""

    def test_get_product_info_success(self):
        """Should return product details for valid product ID."""
        from tools.product_tools import get_product_info

        result = get_product_info("laptop-x1")

        assert result["product_id"] == "laptop-x1"
        assert result["name"] == "Professional Laptop X1"
        assert result["category"] == "Laptops"
        assert result["warranty_months"] == 24
        assert "specs" in result
        assert result["specs"]["processor"] == "Intel Core i7-12700H"
        assert "compatible_accessories" in result

    def test_get_product_info_all_products(self):
        """Should return correct details for all products."""
        from tools.product_tools import get_product_info

        # Test laptop
        laptop = get_product_info("laptop-x1")
        assert laptop["warranty_months"] == 24
        assert "processor" in laptop["specs"]

        # Test monitor
        monitor = get_product_info("monitor-hd27")
        assert monitor["warranty_months"] == 12
        assert monitor["specs"]["resolution"] == "2560x1440"

        # Test keyboard
        keyboard = get_product_info("keyboard-k95")
        assert keyboard["warranty_months"] == 24
        assert keyboard["specs"]["switch_type"] == "Cherry MX Red"

    def test_get_product_info_not_found(self):
        """Should return error for unknown product ID."""
        from tools.product_tools import get_product_info

        result = get_product_info("invalid-product")

        assert "error" in result
        assert "not found" in result["error"]
        assert "available_products" in result
        assert "laptop-x1" in result["available_products"]

    def test_search_documentation_basic(self):
        """Should search documentation with basic query."""
        from tools.product_tools import search_documentation

        result = search_documentation("warranty")

        assert result["query"] == "warranty"
        assert result["total_results"] > 0
        assert "results" in result
        assert len(result["results"]) > 0
        # Should find warranty-related docs
        assert any("warranty" in doc["title"].lower() for doc in result["results"])

    def test_search_documentation_with_category(self):
        """Should filter documentation by category."""
        from tools.product_tools import search_documentation

        result = search_documentation("claim", category="warranty")

        assert result["category"] == "warranty"
        assert result["total_results"] > 0
        # All results should be in warranty category
        assert all(doc["category"] == "warranty" for doc in result["results"])

    def test_search_documentation_limit(self):
        """Should respect limit parameter."""
        from tools.product_tools import search_documentation

        # Test with limit=2
        result = search_documentation("warranty", limit=2)
        assert len(result["results"]) <= 2

        # Test with limit=1
        result = search_documentation("warranty", limit=1)
        assert len(result["results"]) <= 1

    def test_search_documentation_limit_bounds(self):
        """Should enforce min/max limits."""
        from tools.product_tools import search_documentation

        # Test max limit (should cap at 10)
        result = search_documentation("warranty", limit=100)
        assert len(result["results"]) <= 10

        # Test min limit (should be at least 1)
        result = search_documentation("warranty", limit=0)
        assert len(result["results"]) >= 0

    def test_search_documentation_categories(self):
        """Should find docs in different categories."""
        from tools.product_tools import search_documentation

        # Warranty category
        warranty = search_documentation("claim", category="warranty")
        assert warranty["total_results"] > 0

        # Setup category
        setup = search_documentation("setup", category="setup")
        assert setup["total_results"] > 0

        # Troubleshooting category
        trouble = search_documentation("power", category="troubleshooting")
        assert trouble["total_results"] > 0

        # Maintenance category
        maint = search_documentation("maintenance", category="maintenance")
        assert maint["total_results"] > 0

    def test_search_documentation_enhanced_ranking(self):
        """Should rank results based on enhanced scoring algorithm."""
        from tools.product_tools import search_documentation

        # Query that should match title strongly
        result = search_documentation("laptop power", limit=5)

        assert result["total_results"] > 0
        # First result should have "laptop" and "power" in title or excerpt
        first_doc = result["results"][0]
        title_lower = first_doc["title"].lower()
        excerpt_lower = first_doc["excerpt"].lower()
        assert "laptop" in title_lower or "laptop" in excerpt_lower
        assert "power" in title_lower or "power" in excerpt_lower

    def test_search_documentation_token_overlap(self):
        """Should boost scores based on token overlap."""
        from tools.product_tools import search_documentation

        # Multi-word query to test token matching
        result = search_documentation("wifi connectivity problems", limit=3)

        assert result["total_results"] > 0
        # Should find WiFi-related docs
        assert any(
            "wifi" in doc["title"].lower() or "wifi" in doc["excerpt"].lower()
            for doc in result["results"]
        )

    def test_search_documentation_empty_query_with_category(self):
        """Should return all docs in category when query is empty."""
        from tools.product_tools import search_documentation

        # Empty query with category filter
        result = search_documentation("", category="troubleshooting", limit=10)

        assert result["query"] == ""
        assert result["category"] == "troubleshooting"
        assert result["total_results"] > 0
        # All results should be troubleshooting
        assert all(doc["category"] == "troubleshooting" for doc in result["results"])

    def test_search_documentation_case_insensitive(self):
        """Should perform case-insensitive search."""
        from tools.product_tools import search_documentation

        # Test uppercase query
        upper = search_documentation("WARRANTY")
        # Test lowercase query
        lower = search_documentation("warranty")
        # Test mixed case
        mixed = search_documentation("Warranty")

        # All should return same number of results
        assert upper["total_results"] == lower["total_results"]
        assert upper["total_results"] == mixed["total_results"]

    def test_search_documentation_relevance_scores(self):
        """Should maintain relevance scores in results."""
        from tools.product_tools import search_documentation

        result = search_documentation("laptop", limit=5)

        # All results should have relevance_score
        for doc in result["results"]:
            assert "relevance_score" in doc
            assert 0 <= doc["relevance_score"] <= 1.0
            # Should not have computed_score in output
            assert "computed_score" not in doc

    def test_search_documentation_troubleshooting_articles(self):
        """Should find all troubleshooting articles."""
        from tools.product_tools import search_documentation

        # Search for troubleshooting category
        result = search_documentation("", category="troubleshooting", limit=10)

        # Should have 6 troubleshooting articles (from Phase 5 enhancements)
        assert result["total_results"] >= 6

        # Verify known troubleshooting articles exist
        titles = [doc["title"].lower() for doc in result["results"]]
        troubleshooting_keywords = [
            "power",
            "display",
            "keyboard",
            "wifi",
            "performance",
            "battery",
        ]

        # At least some of these keywords should appear
        found_keywords = sum(
            1 for keyword in troubleshooting_keywords if any(keyword in title for title in titles)
        )
        assert found_keywords >= 4  # Should find most troubleshooting topics

    def test_search_documentation_specific_troubleshooting(self):
        """Should find specific troubleshooting articles."""
        from tools.product_tools import search_documentation

        # Test specific troubleshooting queries
        test_cases = [
            ("laptop won't turn on", "power"),
            ("monitor no signal", "display"),
            ("keyboard not working", "keyboard"),
            ("slow performance", "performance"),
            ("battery draining", "battery"),
            ("wifi not connecting", "wifi"),
        ]

        for query, expected_keyword in test_cases:
            result = search_documentation(query, limit=3)
            assert result["total_results"] > 0, f"No results for query: {query}"

            # Check that at least one result contains the expected keyword
            found = any(
                expected_keyword in doc["title"].lower()
                or expected_keyword in doc["excerpt"].lower()
                for doc in result["results"]
            )
            assert found, f"Expected keyword '{expected_keyword}' not found for query '{query}'"

    def test_list_compatible_accessories_success(self):
        """Should return compatible accessories for valid product."""
        from tools.product_tools import list_compatible_accessories

        result = list_compatible_accessories("laptop-x1")

        assert result["product_id"] == "laptop-x1"
        assert result["product_name"] == "Professional Laptop X1"
        assert "compatible_accessories" in result
        assert result["total_count"] > 0
        # Should have specific accessories
        accessory_ids = [acc["id"] for acc in result["compatible_accessories"]]
        assert "docking-station-pro" in accessory_ids
        assert "travel-case-14" in accessory_ids

    def test_list_compatible_accessories_all_products(self):
        """Should return accessories for all products."""
        from tools.product_tools import list_compatible_accessories

        # Test each product has accessories
        for product_id in ["laptop-x1", "monitor-hd27", "keyboard-k95"]:
            result = list_compatible_accessories(product_id)
            assert result["total_count"] > 0
            assert len(result["compatible_accessories"]) > 0
            # Each accessory should have id and name
            for acc in result["compatible_accessories"]:
                assert "id" in acc
                assert "name" in acc

    def test_list_compatible_accessories_not_found(self):
        """Should handle unknown product ID."""
        from tools.product_tools import list_compatible_accessories

        result = list_compatible_accessories("invalid-product")

        assert "error" in result
        assert "not found" in result["error"]

    def test_list_compatible_accessories_specific_products(self):
        """Should return correct accessories for each product type."""
        from tools.product_tools import list_compatible_accessories

        # Laptop accessories
        laptop = list_compatible_accessories("laptop-x1")
        laptop_ids = [acc["id"] for acc in laptop["compatible_accessories"]]
        assert "docking-station-pro" in laptop_ids
        assert "travel-case-14" in laptop_ids
        assert len(laptop_ids) == 2

        # Monitor accessories
        monitor = list_compatible_accessories("monitor-hd27")
        monitor_ids = [acc["id"] for acc in monitor["compatible_accessories"]]
        assert "monitor-arm-dual" in monitor_ids
        assert "hdmi-cable-2m" in monitor_ids
        assert len(monitor_ids) == 2

        # Keyboard accessories
        keyboard = list_compatible_accessories("keyboard-k95")
        keyboard_ids = [acc["id"] for acc in keyboard["compatible_accessories"]]
        assert "wrist-rest-pro" in keyboard_ids
        assert "usb-c-cable-braided" in keyboard_ids
        assert len(keyboard_ids) == 2

    def test_list_compatible_accessories_structure(self):
        """Should return properly structured accessory data."""
        from tools.product_tools import list_compatible_accessories

        result = list_compatible_accessories("laptop-x1")

        # Check top-level structure
        assert "product_id" in result
        assert "product_name" in result
        assert "compatible_accessories" in result
        assert "total_count" in result

        # Check accessory structure
        for acc in result["compatible_accessories"]:
            assert "id" in acc
            assert "name" in acc
            assert isinstance(acc["id"], str)
            assert isinstance(acc["name"], str)
            assert len(acc["id"]) > 0
            assert len(acc["name"]) > 0

    def test_get_product_info_specs_structure(self):
        """Should return properly structured product specs."""
        from tools.product_tools import get_product_info

        # Test laptop specs
        laptop = get_product_info("laptop-x1")
        assert "specs" in laptop
        assert "processor" in laptop["specs"]
        assert "ram" in laptop["specs"]
        assert "storage" in laptop["specs"]
        assert "display" in laptop["specs"]

        # Test monitor specs
        monitor = get_product_info("monitor-hd27")
        assert "specs" in monitor
        assert "resolution" in monitor["specs"]
        assert "refresh_rate" in monitor["specs"]
        assert "panel_type" in monitor["specs"]

        # Test keyboard specs
        keyboard = get_product_info("keyboard-k95")
        assert "specs" in keyboard
        assert "switch_type" in keyboard["specs"]
        assert "backlighting" in keyboard["specs"]

    def test_get_product_info_warranty_coverage(self):
        """Should return correct warranty coverage for each product."""
        from tools.product_tools import get_product_info

        # Laptops have 24-month warranty
        laptop = get_product_info("laptop-x1")
        assert laptop["warranty_months"] == 24

        # Monitors have 12-month warranty
        monitor = get_product_info("monitor-hd27")
        assert monitor["warranty_months"] == 12

        # Keyboards have 24-month warranty
        keyboard = get_product_info("keyboard-k95")
        assert keyboard["warranty_months"] == 24

    def test_get_product_info_categories(self):
        """Should categorize products correctly."""
        from tools.product_tools import get_product_info

        laptop = get_product_info("laptop-x1")
        assert laptop["category"] == "Laptops"

        monitor = get_product_info("monitor-hd27")
        assert monitor["category"] == "Monitors"

        keyboard = get_product_info("keyboard-k95")
        assert keyboard["category"] == "Keyboards"


class TestPreferencesTools:
    """Test user preferences tools."""

    def test_save_user_preference_success(self):
        """Should save user preference successfully."""
        from tools.preferences import save_user_preference

        result = save_user_preference("user-123", "notification_email", "test@example.com")

        assert result["status"] == "saved"
        assert result["user_id"] == "user-123"
        assert result["preference_key"] == "notification_email"
        assert result["preference_value"] == "test@example.com"
        assert "message" in result
        assert "timestamp" in result

    def test_save_user_preference_various_types(self):
        """Should handle different preference value types."""
        from tools.preferences import save_user_preference

        # String value
        result = save_user_preference("user-123", "language", "en-US")
        assert result["status"] == "saved"
        assert result["preference_value"] == "en-US"

        # Boolean value
        result = save_user_preference("user-123", "notifications_enabled", True)
        assert result["status"] == "saved"
        assert result["preference_value"] is True

        # Numeric value
        result = save_user_preference("user-123", "max_results", 10)
        assert result["status"] == "saved"
        assert result["preference_value"] == 10

    def test_save_user_preference_validation(self):
        """Should validate required parameters."""
        from tools.preferences import save_user_preference

        # Missing user_id
        result = save_user_preference("", "key", "value")
        assert result["status"] == "error"
        assert "required" in result["message"]

        # Missing preference_key
        result = save_user_preference("user-123", "", "value")
        assert result["status"] == "error"
        assert "required" in result["message"]

    def test_save_user_preference_timestamp(self):
        """Should include timestamp in response."""
        from tools.preferences import save_user_preference

        result = save_user_preference("user-123", "theme", "dark")

        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        assert len(result["timestamp"]) > 0

    def test_save_user_preference_messages(self):
        """Should include descriptive messages."""
        from tools.preferences import save_user_preference

        result = save_user_preference("user-456", "language", "es")

        assert "message" in result
        assert "saved" in result["message"].lower()
        # Message should indicate successful save
        assert result["status"] == "saved"

    def test_save_user_preference_special_characters(self):
        """Should handle special characters in values."""
        from tools.preferences import save_user_preference

        # Email with special characters
        result = save_user_preference("user-123", "email", "user+test@example.com")
        assert result["status"] == "saved"
        assert result["preference_value"] == "user+test@example.com"

        # Value with spaces
        result = save_user_preference("user-123", "display_name", "John Doe")
        assert result["status"] == "saved"
        assert result["preference_value"] == "John Doe"

    def test_save_user_preference_empty_value(self):
        """Should handle empty preference values."""
        from tools.preferences import save_user_preference

        # Empty string value should be allowed (user might want to clear a preference)
        result = save_user_preference("user-123", "nickname", "")
        # Implementation-dependent: might save or reject empty values
        # This test documents the behavior
        assert "status" in result


class TestWarrantyDocsRuntime:
    """Test warranty-docs agent runtime."""

    def test_runtime_imports(self):
        """Runtime should import without errors."""
        with (
            patch("agentcore_common.load_agent_config") as mock_load_config,
            patch("agentcore_common.observability.setup_observability") as mock_observability,
            patch("boto3.client") as mock_boto_client,
        ):
            # Mock configuration
            mock_config = MagicMock()
            mock_config.name = "warranty-docs"
            mock_config.model.model_id = "test-model"
            mock_config.model.temperature = 0.7
            mock_config.model.max_tokens = 4096
            mock_config.system_prompt = "Test prompt"
            mock_config.runtime.region = "us-east-1"
            mock_config.gateway.gateway_id = "test-gateway-id"
            mock_config.observability = {"log_level": "INFO", "xray_tracing": False}
            mock_load_config.return_value = mock_config

            # Mock observability
            mock_logger = MagicMock()
            mock_observability.return_value = mock_logger

            # Mock boto3 client
            mock_control = MagicMock()
            mock_boto_client.return_value = mock_control

            try:
                import runtime  # noqa: F401

                assert True
            except ImportError as e:
                pytest.fail(f"Failed to import runtime: {e}")

    def test_tools_importable(self):
        """All warranty-docs tools should be importable."""
        from tools.preferences import save_user_preference
        from tools.product_tools import (
            get_product_info,
            list_compatible_accessories,
            search_documentation,
        )

        # Verify all tools are callable
        assert callable(get_product_info)
        assert callable(search_documentation)
        assert callable(list_compatible_accessories)
        assert callable(save_user_preference)

    def test_tools_expose_tool_metadata(self):
        """Decorated tools should publish tool_spec metadata."""
        from tools.preferences import save_user_preference
        from tools.product_tools import (
            get_product_info,
            list_compatible_accessories,
            search_documentation,
        )

        tool_expectations = {
            get_product_info: "get_product_info",
            search_documentation: "search_documentation",
            list_compatible_accessories: "list_compatible_accessories",
            save_user_preference: "save_user_preference",
        }

        for tool_fn, expected_name in tool_expectations.items():
            assert hasattr(tool_fn, "tool_spec"), f"{expected_name} missing tool_spec"
            spec = tool_fn.tool_spec
            assert spec["name"] == expected_name
            assert "inputSchema" in spec
            assert "json" in spec["inputSchema"]
            assert spec["inputSchema"]["json"]["type"] == "object"

    def test_runtime_has_required_functions(self):
        """Runtime should export required functions."""
        with (
            patch("agentcore_tools.runtime.load_agent_config") as mock_load_config,
            patch("agentcore_tools.runtime.setup_observability") as mock_observability,
            patch("boto3.client") as mock_boto_client,
        ):
            # Setup mocks
            mock_config = MagicMock()
            mock_config.name = "warranty-docs"
            mock_config.model.model_id = "test-model"
            mock_config.model.temperature = 0.7
            mock_config.model.max_tokens = 4096
            mock_config.system_prompt = "Test prompt"
            mock_config.runtime.region = "us-east-1"
            mock_config.gateway.gateway_id = "test-gateway-id"
            mock_config.observability = {"log_level": "INFO", "xray_tracing": False}
            mock_load_config.return_value = mock_config
            mock_observability.return_value = MagicMock()
            mock_boto_client.return_value = MagicMock()

            import runtime

            # Should have invoke function
            assert hasattr(runtime, "invoke")
            assert callable(runtime.invoke)

            # Should have app instance
            assert hasattr(runtime, "app")


class TestToolIntegration:
    """Test integration scenarios between tools."""

    def test_product_info_to_accessories_flow(self):
        """Should support product info -> accessories lookup flow."""
        from tools.product_tools import get_product_info, list_compatible_accessories

        # Get product info
        product = get_product_info("laptop-x1")
        assert "product_id" in product

        # Use product_id to get accessories
        accessories = list_compatible_accessories(product["product_id"])
        assert accessories["product_id"] == product["product_id"]
        assert accessories["total_count"] > 0

    def test_search_warranty_claim_flow(self):
        """Should support warranty claim documentation flow."""
        from tools.product_tools import search_documentation

        # Search for warranty claim process
        docs = search_documentation("file warranty claim", category="warranty")

        assert docs["total_results"] > 0
        # Should find claim-related documentation
        assert any("claim" in doc["title"].lower() for doc in docs["results"])

    def test_troubleshooting_by_category_flow(self):
        """Should support troubleshooting category browsing."""
        from tools.product_tools import search_documentation

        # Get all troubleshooting docs
        all_trouble = search_documentation("", category="troubleshooting", limit=10)

        assert all_trouble["total_results"] >= 6  # Phase 5 added 6 articles
        assert all(doc["category"] == "troubleshooting" for doc in all_trouble["results"])

        # Now search within troubleshooting
        power_trouble = search_documentation("power", category="troubleshooting")
        assert power_trouble["total_results"] > 0
        assert all(doc["category"] == "troubleshooting" for doc in power_trouble["results"])

    def test_product_and_documentation_correlation(self):
        """Should find relevant docs for products."""
        from tools.product_tools import get_product_info, search_documentation

        # Get laptop product
        laptop = get_product_info("laptop-x1")
        assert laptop["category"] == "Laptops"

        # Search for laptop-related docs
        laptop_docs = search_documentation("laptop")
        assert laptop_docs["total_results"] > 0

        # Should include setup, troubleshooting, or maintenance for laptops
        categories = {doc["category"] for doc in laptop_docs["results"]}
        expected_categories = {"setup", "troubleshooting", "maintenance"}
        assert len(categories & expected_categories) > 0

    def test_warranty_info_and_service_lookup_flow(self):
        """Should support warranty -> service center flow."""
        from tools.product_tools import get_product_info, search_documentation

        # Get product with warranty info
        product = get_product_info("laptop-x1")
        assert product["warranty_months"] == 24

        # Find service center documentation
        service_docs = search_documentation("service center", category="warranty")
        assert service_docs["total_results"] > 0

        # Should find service locator info
        assert any("service" in doc["title"].lower() for doc in service_docs["results"])


class TestDataValidation:
    """Test data validation and error handling."""

    def test_product_info_error_structure(self):
        """Product info errors should have consistent structure."""
        from tools.product_tools import get_product_info

        result = get_product_info("nonexistent-product")

        # Error response structure
        assert "error" in result
        assert isinstance(result["error"], str)
        assert "available_products" in result
        assert isinstance(result["available_products"], list)
        assert len(result["available_products"]) > 0

    def test_search_documentation_no_results(self):
        """Should handle queries with no matching results."""
        from tools.product_tools import search_documentation

        # Query unlikely to match anything
        result = search_documentation("xyzabc123nonexistent")

        assert result["query"] == "xyzabc123nonexistent"
        assert result["total_results"] == 0
        assert result["results"] == []

    def test_accessories_error_preserves_available_products(self):
        """Accessories error should show available products."""
        from tools.product_tools import list_compatible_accessories

        result = list_compatible_accessories("invalid-xyz")

        assert "error" in result
        # Should have same error structure as get_product_info
        assert "available_products" in result

    def test_all_tools_return_dict(self):
        """All tools should return dictionary responses."""
        from tools.preferences import save_user_preference
        from tools.product_tools import (
            get_product_info,
            list_compatible_accessories,
            search_documentation,
        )

        # Test all tools return dict
        assert isinstance(get_product_info("laptop-x1"), dict)
        assert isinstance(search_documentation("test"), dict)
        assert isinstance(list_compatible_accessories("laptop-x1"), dict)
        assert isinstance(save_user_preference("user", "key", "value"), dict)

    def test_documentation_url_format(self):
        """Documentation URLs should be properly formatted."""
        from tools.product_tools import search_documentation

        result = search_documentation("warranty", limit=5)

        for doc in result["results"]:
            assert "url" in doc
            assert isinstance(doc["url"], str)
            assert doc["url"].startswith("/docs/")
            assert len(doc["url"]) > len("/docs/")
