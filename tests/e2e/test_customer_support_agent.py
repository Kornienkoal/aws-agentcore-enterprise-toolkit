"""End-to-end style checks for the customer-support agent tools.

These tests exercise the public tool entrypoints with natural-language inputs
that mirror real user prompts. They help guard against regressions where the
agent responds with tool-call scaffolding instead of final answers.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module", autouse=True)
def add_agent_to_path():
    """Ensure the customer-support agent package is importable during tests."""

    agent_path = Path(__file__).parent.parent.parent / "agents" / "customer-support"
    # Clear cached modules that may have been imported by other agent tests
    modules_to_clear = [key for key in sys.modules if key == "tools" or key.startswith("tools.")]
    for module in modules_to_clear:
        sys.modules.pop(module, None)

    sys.path.insert(0, str(agent_path))
    yield
    sys.path.remove(str(agent_path))


def test_product_info_resolves_marketing_name():
    """Marketing product names should resolve via the get_product_info tool."""
    from tools.product_tools import get_product_info  # type: ignore[import-not-found]

    result = get_product_info(product_name="Contoso Laptop X1")

    assert result["product_id"] == "laptop-x1"
    assert result["specs"]["ram"] == "16GB"
    assert result["specs"]["battery_life"] == "12 hours"


def test_product_info_handles_unknown_items():
    """Unknown products should return an error payload rather than raising."""
    from tools.product_tools import get_product_info  # type: ignore[import-not-found]

    result = get_product_info(product_name="Mystery Gadget 9000")

    assert "error" in result
    assert result["available_products"]
