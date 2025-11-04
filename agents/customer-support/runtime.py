"""Customer Support Agent - Runtime Entry Point.

Based on AWS Bedrock AgentCore Lab 4 reference implementation.
Uses BedrockAgentCoreApp + Strands framework for agent orchestration.
"""

from agentcore_tools import create_runtime_app

# Import local tools
from tools.product_tools import get_product_info, search_documentation

# Create app and invoke handler with all runtime logic in agentcore_tools
app, invoke = create_runtime_app(
    agent_name="customer-support",
    local_tools=[
        get_product_info,
        search_documentation,
    ],
)

# Register the entrypoint
app.entrypoint(invoke)

# Entry point for AgentCore Runtime
if __name__ == "__main__":
    app.run()
