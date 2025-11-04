"""Warranty & Documentation Assistant - Runtime Entry Point.

Agent focused on warranty status checking, service center location,
and product documentation search.

Uses BedrockAgentCoreApp + Strands framework for agent orchestration.
"""

from agentcore_tools import create_runtime_app

# Import local tools
from tools.preferences import save_user_preference
from tools.product_tools import (
    get_product_info,
    list_compatible_accessories,
    search_documentation,
)

# Create app and invoke handler with all runtime logic in agentcore_tools
app, invoke = create_runtime_app(
    agent_name="warranty-docs",
    local_tools=[
        get_product_info,
        search_documentation,
        list_compatible_accessories,
        save_user_preference,
    ],
)

# Register the entrypoint
app.entrypoint(invoke)

# Entry point for AgentCore Runtime
if __name__ == "__main__":
    app.run()
