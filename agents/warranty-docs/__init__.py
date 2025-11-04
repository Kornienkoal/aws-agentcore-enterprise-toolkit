"""Warranty & Docs Assistant Agent.

This agent provides warranty checking, product documentation search,
and service center location services. It uses both local tools and
shared Gateway MCP tools (check-warranty-status, web-search, service-locator).

Architecture:
- Runtime: BedrockAgentCoreApp + Strands framework
- Local tools: get_product_info, search_documentation, list_compatible_accessories, save_user_preference
- Gateway tools: check-warranty-status, web-search, service-locator
- Config: agent-config/warranty-docs.yaml (SSM resolution)
- Auth: Cognito (via Gateway)
- Observability: CloudWatch Logs + X-Ray
"""

__version__ = "0.1.0"
