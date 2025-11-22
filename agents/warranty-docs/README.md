# Warranty & Documentation Assistant

Specialized agent for warranty checking, service center location, and product documentation.

## Purpose

Helps customers with:
- Checking warranty status and coverage
- Finding authorized service centers
- Searching product documentation
- Finding compatible accessories
- Saving user preferences

## Tools

**Gateway Tools (shared):**
- `check-warranty-status` - Check warranty coverage and expiration by product ID
- `service-locator` - Find authorized service centers by city/region
- `web-search` - Search the web for additional information

**Local Tools:**
- `get_product_info(product_id)` - Retrieve product specs and warranty details
- `search_documentation(query, category, limit)` - Search knowledge base (warranty, setup, troubleshooting, maintenance)
- `list_compatible_accessories(product_id)` - Find compatible accessories for a product
- `save_user_preference(user_id, key, value)` - Save user preferences (email, language, etc.)

## Configuration

**File:** `agent-config/warranty-docs.yaml`

**Model:** Claude Haiku 4.5 (`us.anthropic.claude-haiku-4-5-20251001-v1:0`)

**System Prompt Highlights:**
- Specialized in warranty and documentation
- Follows structured workflow: product info → warranty check → service centers → docs
- Professional and clear communication
- Explains warranty terms clearly

## Example Interactions

**Check warranty and find service center:**
```
User: "I have laptop-x1, check warranty and find service centers in New York"
Agent: [Uses check-warranty-status + service-locator tools]
       "Your laptop-x1 warranty is active until 2026-03-15 (503 days remaining).

        Authorized service centers in New York:
        1. Tech Solutions NYC - 123 Broadway, (212) 555-0100
        2. Manhattan Tech Repair - 456 5th Avenue, (212) 555-0200"
```

**Search documentation:**
```
User: "How do I file a warranty claim?"
Agent: [Uses search_documentation with category='warranty']
       "To file a warranty claim:
        1. Have your serial number ready
        2. Check warranty status online
        3. Contact an authorized service center
        4. Provide proof of purchase
        Claims are processed within 5 business days."
```

**Find accessories:**
```
User: "What accessories work with laptop-x1?"
Agent: [Uses list_compatible_accessories tool]
       "Compatible accessories for laptop-x1:
        - USB-C Docking Station Pro
        - 14-inch Protective Travel Case"
```

**Save preferences:**
```
User: "Save my email as contact@example.com"
Agent: [Uses save_user_preference tool]
       "I've saved your notification email. You'll receive updates at contact@example.com"
```

**Troubleshooting queries:**
```
User: "My laptop won't power on"
Agent: [Uses search_documentation with enhanced ranking]
       "Here's how to troubleshoot laptop power issues:
        1. Check power adapter connection
        2. Remove battery and reconnect
        3. Hold power button for 30 seconds to reset
        4. Test with different outlet
        If issue persists, contact support.

        Full guide: /docs/laptop-power-troubleshooting"
```

**Web search fallback (when needed):**
```
User: "Where can I download the latest drivers for monitor-hd27?"
Agent: [May use web-search Gateway tool if internal docs insufficient]
       "Here are the official driver sources for monitor-hd27..."
```

## Test Data

**Products:**
- `laptop-x1` - Professional Laptop (24-month warranty, Active until 2026-03-15)
- `monitor-hd27` - 27-inch Monitor (12-month warranty, Active until 2025-06-20)
- `keyboard-k95` - Mechanical Keyboard (24-month warranty, Expired 2024-09-01)

**Service Centers:**
- New York: 2 locations
- San Francisco: 2 locations
- Los Angeles, Austin, Seattle, Chicago: 1 location each

**Troubleshooting Documentation (11 articles):**
- Warranty guides (3): Coverage overview, claim filing, service centers
- Setup guide (1): Laptop initial setup
- Troubleshooting guides (6): Power issues, display problems, keyboard, WiFi, performance, battery
- Maintenance guide (1): Best practices

**Enhanced Search Features:**
- Query-aware ranking with keyword matching
- Token overlap scoring for partial matches
- Category filtering (warranty, setup, troubleshooting, maintenance)
- Title and excerpt match boosting
- Relevance scores capped at 1.0

## Usage

**Via Streamlit UI:**
```bash
uv run streamlit run services/frontend_streamlit/main.py
```
1. Authenticate with Cognito
2. Select "Warranty & Docs" from agent dropdown
3. Try: "Check warranty for laptop-x1 and find service centers in San Francisco"

**Deploy or update the runtime (AgentCore CLI):**
```bash
agentcore launch --agent warranty_docs --local-build --auto-update-on-conflict
```
Configure `.bedrock_agentcore.yaml` with your environment’s IDs before running the command. The
CLI builds the container locally, pushes it to the environment ECR repository, and updates the
Bedrock AgentCore runtime in place.

**Testing:**
```bash
uv run pytest tests/unit/agents/test_warranty_docs.py -v
```

## Files

- `runtime.py` - Agent entrypoint with BedrockAgentCoreApp
- `tools/product_tools.py` - Product info, documentation, and accessories tools
- `tools/preferences.py` - User preference storage tool
- `agent-config/warranty-docs.yaml` - Agent configuration

For deployment and architecture details, see `../README.md`.
