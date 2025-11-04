# Agents Overview

Two production-ready agents sharing common infrastructure (Gateway, Memory, Runtime, Observability):

- **customer-support**: Product inquiries, troubleshooting, warranty checks
- **warranty-docs**: Product documentation, warranty lookup, service centers

All agents use infrastructure provisioned once via Terraform, with separate configurations in `agent-config/*.yaml`.

## Quick Start

**Prerequisites:**
- Infrastructure deployed: `cd infrastructure/terraform/envs/dev && terraform apply`
- AWS credentials configured (us-east-1)
- Python 3.13+ with `uv` installed

**First-Time Setup (AgentCore CLI Configuration):**

The AgentCore CLI requires `.bedrock_agentcore.yaml` with your Terraform-provisioned resources:

```bash
# 1. Copy the example configuration
cp .bedrock_agentcore_example.yaml .bedrock_agentcore.yaml

# 2. Get your Terraform-provisioned execution role ARN
aws ssm get-parameter --name /agentcore/dev/runtime/execution_role_arn \
  --query 'Parameter.Value' --output text

# 3. Get your memory ID
aws ssm get-parameter --name /agentcore/dev/memory/memory_id \
  --query 'Parameter.Value' --output text

# 4. Edit .bedrock_agentcore.yaml and replace:
#    - <account-id> with your AWS account ID
#    - <aws-region> with us-east-1
#    - /ABSOLUTE/PATH/TO/REPO with your actual repo path
#    - execution_role ARN with the value from step 2
#    - memory_id with the value from step 3
#
# CRITICAL: Set execution_role_auto_create: false (we use Terraform roles)

# 5. Make it read-only to prevent accidental changes
chmod 444 .bedrock_agentcore.yaml
```

**Launch the Streamlit UI:**
```bash
uv sync
AGENTCORE_ENV=dev AWS_REGION=us-east-1 uv run streamlit run frontend/streamlit_app/main.py
```

Select an agent from the sidebar and start chatting!

## Deployment

Infrastructure and runtime code ship through two complementary flows:

1. **Terraform (once per environment)** – `terraform apply` in `infrastructure/terraform/envs/{env}` provisions Cognito, Gateway, Memory, IAM roles, CloudWatch dashboards, and packages every MCP Lambda tool (`check_warranty`, `service_locator`, `web_search`). Terraform detects source changes under `agents/global-tools/*` and redeploys the functions during apply.

2. **AgentCore CLI (per agent update)** – Use the AgentCore CLI to build and publish each agent runtime container. The CLI reads `.bedrock_agentcore.yaml`, builds the Docker image, pushes to ECR, and updates the AgentCore runtime endpoint.

```bash
# Example: deploy both agents after making code changes
agentcore launch --agent customer_support --local-build --auto-update-on-conflict
agentcore launch --agent warranty_docs   --local-build --auto-update-on-conflict

# See currently configured agents
agentcore configure list
```

> **Tip:** The `--local-build` flag lets you use your local Docker/Finch installation while still deploying to the managed AgentCore runtime.

**Updating global tools:**
```bash
cd infrastructure/terraform/envs/dev
terraform apply  # Detects code changes and redeploys shared Lambda tools
```

## Testing

**Interactive Testing (Recommended):**
```bash
# Launch Streamlit UI with full auth + Gateway tools
AGENTCORE_ENV=dev AWS_REGION=us-east-1 uv run streamlit run frontend/streamlit_app/main.py
```

**Unit Tests:**
```bash
# Fast, mocked tests (no AWS calls)
uv run pytest tests/unit/agents/ -v

# Test specific agent
uv run pytest tests/unit/agents/test_warranty_docs.py -v
```

**Integration Tests:**
```bash
# End-to-end tests (requires deployed infrastructure)
uv run pytest tests/e2e/ -v
```

**Docker Testing:**
```bash
# Test agent in Lambda-like container environment
./scripts/local/run-agent-docker.sh warranty-docs "What are laptop-x1 specs?"
```

## Gateway Tools (Shared Lambdas)

Gateway tools are Lambda functions deployed once per environment, available to all agents via MCP over HTTP.

**Available Tools:**

| Tool Name | Purpose | Lambda Function |
|-----------|---------|-----------------|
| `check-warranty-status` | Check warranty coverage by product ID | `agentcore-check_warranty-tool-dev` |
| `web-search` | Search the web for information | `agentcore-web_search-tool-dev` |
| `service-locator` | Find service centers by location | `agentcore-service_locator-tool-dev` |

**Tool Definition:**
- **Code**: `agents/global-tools/{tool}/lambda_function.py`
- **Schema**: `agents/global-tools/{tool}/tool-schema.json` (MCP format)
- **Deployment**: Automatic via Terraform when code changes detected
- **Logs**: `/aws/lambda/agentcore-{tool}-tool-dev` in CloudWatch

**Adding a New Tool:**

1. Create directory: `agents/global-tools/my-tool/`
2. Add files:
   - `lambda_function.py` - Handler with structured logging
   - `tool-schema.json` - MCP schema with name (use hyphens), description, inputSchema
   - `requirements.txt` - Dependencies (optional)
3. Add to `infrastructure/terraform/envs/dev/terraform.tfvars`:
   ```hcl
   global_tools = [
     {
       name       = "my_tool"
       source_dir = "agents/global-tools/my-tool"
     }
   ]
   ```
4. Deploy: `cd infrastructure/terraform/envs/dev && terraform apply`
5. Authorize in agent config (`agent-config/*.yaml`):
   ```yaml
   gateway:
     allowed_tools:
       - "my-tool"  # Use hyphenated MCP name
   ```

**Tool Logging (Structured JSON):**

All tools now log JSON for easy CloudWatch filtering:
```python
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    # Log invocation
    logger.info(json.dumps({
        "tool": "my-tool",
        "request_id": context.request_id,
        "event_keys": list(event.keys())
    }))

    # Business logic...

    # Log success/error
    logger.info(json.dumps({"action": "success", "result_count": 5}))
```

**Viewing Tool Logs:**
```bash
# Recent invocations for all tools
aws logs tail /aws/lambda/agentcore-check_warranty-tool-dev --follow

# Filter by action
aws logs filter-pattern '{$.action = "error"}' \
  /aws/lambda/agentcore-check_warranty-tool-dev

# Get logs for specific request
aws logs filter-pattern '{$.request_id = "abc-123"}' \
  /aws/lambda/agentcore-check_warranty-tool-dev
```

## Agent Architecture

**Minimal Runtime Code:**

Each agent runtime (`agents/{agent}/runtime.py`) is 26-35 lines:
```python
from agentcore_tools.runtime import create_runtime_app
from tools.product_tools import get_product_info, search_documentation

app, invoke = create_runtime_app(
    agent_name="warranty-docs",
    local_tools=[
        get_product_info,
        search_documentation,
    ],
)
```

**Common Logic in Packages:**

- **agentcore-common**: Auth, config loading, gateway control plane, observability
- **agentcore-tools**: Runtime lifecycle, MCP client, memory hooks, model creation

See `packages/agentcore-common/README.md` and `packages/agentcore-tools/README.md` for details.

## Troubleshooting

**`.bedrock_agentcore.yaml` configuration issues:**

This file is managed by the AgentCore CLI and should use Terraform-provisioned resources:

```bash
# Verify your configuration uses the correct execution role
grep execution_role .bedrock_agentcore.yaml

# Should show: arn:aws:iam::<account>:role/agentcore-runtime-dev-execution-role
# NOT: AmazonBedrockAgentCoreSDKRuntime-* (SDK auto-created - wrong!)

# If incorrect, restore from example and reconfigure:
cp .bedrock_agentcore_example.yaml .bedrock_agentcore.yaml
# Follow "First-Time Setup" steps above
chmod 444 .bedrock_agentcore.yaml

# Make read-only to prevent accidental overwrites
chmod 444 .bedrock_agentcore.yaml
```

**Gateway tools not working:**
```bash
# 1. Verify tools are registered
GATEWAY_ID=$(aws ssm get-parameter --name /agentcore/dev/gateway/gateway_id --query 'Parameter.Value' --output text)
aws bedrock-agentcore-control list-gateway-targets --gateway-identifier $GATEWAY_ID

# 2. Test tool directly
aws lambda invoke --function-name agentcore-check_warranty-tool-dev \
  --payload '{"body": {"product_id": "laptop-x1"}}' response.json
cat response.json | jq .

# 3. Check tool logs
aws logs tail /aws/lambda/agentcore-check_warranty-tool-dev --follow
```

**Agent config not loading:**
```bash
# Verify SSM parameters exist
aws ssm get-parameters-by-path --path /agentcore/dev/ --region us-east-1

# Check config file syntax
uv run python -c "import yaml; yaml.safe_load(open('agent-config/customer-support.yaml'))"
```

**Tools not being called by agent:**
- Check `allowed_tools` in agent config matches MCP names (hyphens: `check-warranty-status`)
- Verify system prompt mentions tool availability
- Review agent logs for tool selection decisions

## Further Reading

- **Infrastructure**: `../infrastructure/terraform/README.md`
- **Global tools**: `./global-tools/README.md`
- **Frontend**: `../frontend/streamlit_app/README.md`
- **Developer Guide**: `./DEVELOPER_GUIDE.md` (detailed architecture, patterns, creating new agents)
- **Contributing**: `../CONTRIBUTING.md`
