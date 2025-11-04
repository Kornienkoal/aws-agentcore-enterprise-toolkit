"""Customer Support agent - local product tools.

These helpers power the agent's local context lookups for product catalog
details and knowledge-base snippets. They intentionally mirror the data
shape used by the warranty-docs agent so that test fixtures can exercise
both agents interchangeably.
"""

from __future__ import annotations

from typing import Any

from strands.tools import tool


@tool
def get_product_info(
    product_id: str | None = None,
    *,
    product_name: str | None = None,
) -> dict[str, Any]:
    """Retrieve detailed product information.

    Supports lookup by canonical product_id or by friendly marketing name.

    Args:
        product_id: Canonical identifier (e.g., ``laptop-x1``)
        product_name: Friendly product name used by customers/marketing

    Returns:
        Dictionary describing the product or an error payload when not found.
    """

    mock_products: dict[str, dict[str, Any]] = {
        "laptop-x1": {
            "product_id": "laptop-x1",
            "name": "Professional Laptop X1",
            "category": "Laptops",
            "warranty_months": 24,
            "specs": {
                "processor": "Intel Core i7-12700H",
                "ram": "16GB",
                "storage": "512GB SSD",
                "battery_life": "12 hours",
                "display": "14-inch FHD",
            },
            "price_usd": 1299.99,
            "in_stock": True,
            "aliases": ["contoso laptop x1", "professional laptop x1"],
        },
        "monitor-hd27": {
            "product_id": "monitor-hd27",
            "name": "27-inch HD Monitor",
            "category": "Monitors",
            "warranty_months": 12,
            "specs": {
                "resolution": "2560x1440",
                "refresh_rate": "144Hz",
                "panel_type": "IPS",
                "ports": "HDMI 2.0, DisplayPort 1.4, USB-C",
            },
            "price_usd": 399.99,
            "in_stock": True,
            "aliases": ["contoso hd27", "27-inch monitor"],
        },
        "smartphone-s10": {
            "product_id": "smartphone-s10",
            "name": "Smartphone S10",
            "category": "Smartphones",
            "warranty_months": 12,
            "specs": {
                "screen_size": "6.5 inches",
                "storage": "128GB",
                "camera": "48MP triple lens",
                "battery_life": "24 hours",
            },
            "price_usd": 699.99,
            "in_stock": False,
            "aliases": ["contoso s10", "smartphone series 10"],
        },
    }

    # Prefer explicit product_id lookup
    lookup_id = product_id

    # Resolve friendly marketing names
    if not lookup_id and product_name:
        normalized = product_name.lower().strip()
        for candidate_id, details in mock_products.items():
            aliases = [details["name"].lower()] + details.get("aliases", [])
            if normalized in aliases:
                lookup_id = candidate_id
                break

    if not lookup_id:
        return {
            "error": "Either product_id or product_name must be provided",
            "available_products": list(mock_products.keys()),
        }

    product = mock_products.get(lookup_id)
    if not product:
        return {
            "error": f"Product '{lookup_id}' not found",
            "available_products": list(mock_products.keys()),
        }

    return product


@tool
def search_documentation(query: str, category: str | None = None, limit: int = 5) -> dict[str, Any]:
    """
    Search product documentation and knowledge base.

    Args:
        query: Search query string
        category: Optional category filter (setup, troubleshooting, warranty, maintenance)
        limit: Maximum number of results (default 5)

    Returns:
        Matching documentation articles

    Example:
        >>> search_documentation('laptop password reset', category='troubleshooting')
        {
            'query': 'laptop password reset',
            'results': [
                {
                    'title': 'How to Reset Laptop Password',
                    'category': 'troubleshooting',
                    'excerpt': '...'
                }
            ]
        }
    """
    # In production, this would:
    # 1. Query Knowledge Base via BedrockAgent retrieve API
    # 2. Use semantic search on vector embeddings
    # 3. Rank results by relevance

    # For template demo, reuse the richer troubleshooting catalog from the
    # warranty-docs agent so responses stay consistent across agents.
    mock_docs = [
        {
            "doc_id": "doc-001",
            "title": "Laptop Password Reset Guide",
            "category": "troubleshooting",
            "excerpt": "To reset your laptop password, power off the device, then hold F8 during boot until the recovery screen appears. Select 'Troubleshoot' then 'Reset this PC'.",
            "relevance_score": 0.92,
            "url": "/docs/laptop-password-reset",
        },
        {
            "doc_id": "doc-002",
            "title": "Laptop Initial Setup",
            "category": "setup",
            "excerpt": "When setting up your new laptop for the first time, connect to WiFi, sign in with your account, and apply the latest updates before installing additional software.",
            "relevance_score": 0.78,
            "url": "/docs/laptop-setup",
        },
        {
            "doc_id": "doc-003",
            "title": "Laptop Warranty Service",
            "category": "warranty",
            "excerpt": "Your laptop includes a 24-month warranty covering manufacturing defects. Contact an authorized service center with your serial number to file a claim.",
            "relevance_score": 0.81,
            "url": "/docs/laptop-warranty",
        },
        {
            "doc_id": "doc-004",
            "title": "Monitor Calibration Guide",
            "category": "setup",
            "excerpt": "For optimal display quality, calibrate your monitor using the built-in OSD tools or download our ICC profiles for accurate color reproduction.",
            "relevance_score": 0.67,
            "url": "/docs/monitor-calibration",
        },
        {
            "doc_id": "doc-005",
            "title": "Smartphone Wireless Connectivity",
            "category": "troubleshooting",
            "excerpt": "If your smartphone cannot connect to WiFi or Bluetooth, toggle airplane mode, reboot the device, and re-pair your accessories.",
            "relevance_score": 0.74,
            "url": "/docs/smartphone-connectivity",
        },
        {
            "doc_id": "doc-006",
            "title": "Laptop Won't Power On - Troubleshooting",
            "category": "troubleshooting",
            "excerpt": "If the laptop will not power on, check the power adapter, perform a hard reset, and test with a known-good outlet before contacting support.",
            "relevance_score": 0.76,
            "url": "/docs/laptop-power-troubleshooting",
        },
        {
            "doc_id": "doc-007",
            "title": "WiFi Connectivity Problems",
            "category": "troubleshooting",
            "excerpt": "WiFi not working? Restart your router, update network drivers, and run the network troubleshooter to reset adapters.",
            "relevance_score": 0.73,
            "url": "/docs/wifi-troubleshooting",
        },
    ]

    query_lower = query.lower()
    query_tokens = set(query_lower.split())

    scored_docs: list[dict[str, Any]] = []
    for doc in mock_docs:
        title_lower = str(doc["title"]).lower()
        excerpt_lower = str(doc["excerpt"]).lower()

        if query and query_lower not in title_lower and query_lower not in excerpt_lower:
            token_overlap = query_tokens & (set(title_lower.split()) | set(excerpt_lower.split()))
            if not token_overlap:
                continue

        score = float(str(doc["relevance_score"]))
        if query_lower and query_lower in title_lower:
            score += 0.15
        if query_lower and query_lower in excerpt_lower:
            score += 0.1
        overlap = len(query_tokens & set(title_lower.split())) + len(
            query_tokens & set(excerpt_lower.split())
        )
        if overlap:
            score += min(0.05 * overlap, 0.2)

        if category and doc["category"] != category:
            continue

        scored_docs.append({**doc, "computed_score": min(score, 1.0)})

    scored_docs.sort(key=lambda d: d["computed_score"], reverse=True)

    limited_docs = scored_docs[: max(1, min(limit, 10))]
    for doc in limited_docs:
        doc.pop("computed_score", None)

    return {
        "query": query,
        "category": category,
        "total_results": len(limited_docs),
        "results": limited_docs,
    }
