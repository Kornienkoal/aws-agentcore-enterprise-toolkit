# Customer Support Agent

General-purpose customer support agent for product inquiries and troubleshooting.

## Purpose

Helps customers with:
- Product information and specifications
- Warranty status checking
- Documentation search
- General troubleshooting

## Tools

**Gateway Tools (shared):**
- `check-warranty-status` - Check warranty coverage by product ID
- `web-search` - Search the web for product information

**Local Tools:**
- `get_product_info(product_id)` - Retrieve detailed product specifications
- `search_documentation(query, category, limit)` - Search internal knowledge base

## Configuration

**File:** `agent-config/customer-support.yaml`

**Model:** Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`)

**System Prompt Highlights:**
- Friendly and professional tone
- Always use check_warranty tool for warranty inquiries
- Use web_search for current information
- Admit when uncertain

## Example Interactions

**Check warranty:**
```
User: "What's the warranty status for laptop-x1?"
Agent: [Uses check-warranty-status tool]
       "Your laptop-x1 has an active warranty that expires on 2026-03-15.
        You have 503 days remaining. The warranty covers manufacturing defects..."
```

**Product information:**
```
User: "Tell me about the monitor-hd27 specs"
Agent: [Uses get_product_info tool]
       "The 27-inch HD Monitor features: 2560x1440 resolution, 144Hz refresh rate,
        IPS panel, 1ms response time..."
```

**Documentation search:**
```
User: "How do I reset my laptop password?"
Agent: [Uses search_documentation tool]
       "Here's the password reset guide: Power off your laptop, then hold F8
        during boot..."
```

## Usage

**Via Streamlit UI:**
```bash
uv run streamlit run frontend/streamlit_app/main.py
```
1. Authenticate with Cognito
2. Select "Customer Support" from agent dropdown
3. Start chatting!

**Deploy or update the runtime (AgentCore CLI):**
```bash
agentcore launch --agent customer_support --local-build --auto-update-on-conflict
```
This builds the container locally, pushes it to the environment ECR repository, and updates the
Bedrock AgentCore runtime in place. Ensure `.bedrock_agentcore.yaml` is configured for your AWS
account and environment before running the command.

**Testing:**
```bash
uv run pytest tests/unit/agents/test_customer_support.py -v
```

## Files

- `runtime.py` - Agent entrypoint with BedrockAgentCoreApp
- `tools/product_tools.py` - Local tool implementations
- `agent-config/customer-support.yaml` - Agent configuration

For deployment and architecture details, see `../README.md`.
