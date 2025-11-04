# Global MCP Tools

Lambda-based MCP tools that are deployed once per environment and shared by every agent over the Bedrock AgentCore Gateway. This stage keeps all tool code, schemas, and packaging logic in one place so Terraform can register them automatically.

## What ships out of the box?

| Tool (MCP name)        | Lambda directory                              | Purpose                                                 |
|------------------------|-----------------------------------------------|---------------------------------------------------------|
| `check-warranty-status`| `agents/global-tools/check_warranty/`          | Look up mock warranty coverage by product ID            |
| `service-locator`      | `agents/global-tools/service_locator/`         | Return authorized service centres for a given location |
| `web-search`           | `agents/global-tools/web_search/`              | Provide mock search results for troubleshooting queries |

Each tool directory contains:

- `lambda_function.py` – Handler with structured JSON logging
- `tool-schema.json` – MCP schema surfaced to the Gateway
- Optional `requirements.txt` – Pinned dependencies vendored by Terraform during deploy

## Prerequisites

- Terraform infrastructure initialised in `infrastructure/terraform/envs/{env}`
- AWS credentials with permission to deploy Lambda and Bedrock AgentCore resources
- Docker/Finch available locally (only required if you run unit tests that package the Lambda)

## Deploy or update the tools

Terraform detects changes to any file inside `agents/global-tools/*` and rebuilds the corresponding Lambda zip before updating Gateway targets.

```bash
cd infrastructure/terraform/envs/dev
terraform init -backend-config=../../globals/backend.tfvars  # first run only
terraform apply
```

During `apply`, you will see:

1. Lambda artefacts rebuilt for any tool whose source changed
2. IAM adjustments (if necessary) for the tool execution role
3. The custom resource re-registering gateway targets using the latest `tool-schema.json`

## Adding a new tool

1. Create a new directory under `agents/global-tools/{tool_name}/`
2. Add at minimum:
   - `lambda_function.py`
   - `tool-schema.json` (use **hyphenated** MCP name in `name` field)
   - Optional `requirements.txt`
3. Register the tool in your environment tfvars:
   ```hcl
   global_tools = [
     {
       name       = "my_tool"
       source_dir = "agents/global-tools/my-tool"
       description = "One-line summary shown in the Gateway console"
     }
   ]
   ```
4. Deploy with Terraform. The custom resource will create or update the Gateway target automatically.
5. Authorise the tool in each agent config (`agent-config/*.yaml`):
   ```yaml
   gateway:
     allowed_tools:
       - "my-tool"
   ```

## Testing and troubleshooting

### Invoke directly

```bash
aws lambda invoke \
  --function-name agentcore-check_warranty-tool-dev \
  --payload '{"body": {"product_id": "laptop-x1"}}' \
  response.json
cat response.json | jq .
```

### Tail logs

```bash
aws logs tail /aws/lambda/agentcore-check_warranty-tool-dev --since 5m --follow
```

Logs are emitted as JSON so you can filter by `action`, `request_id`, or any other field:

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/agentcore-service_locator-tool-dev \
  --filter-pattern '{ $.action = "error" }'
```

### Common issues

- **Gateway target missing?** Re-run `terraform apply` and confirm the tool appears in `aws bedrock-agentcore-control list-gateway-targets`.
- **Tool not listed in the agent?** Ensure the MCP name (hyphenated) is present in `gateway.allowed_tools` for that agent’s config file.
- **Authentication failures?** The Gateway assumes the Terraform-managed IAM role. Verify `/agentcore/{env}/gateway/role_arn` exists in SSM and that the role trust policy allows `bedrock-agentcore.amazonaws.com`.

## File structure reference

```
agents/
└── global-tools/
    ├── check_warranty/
    │   ├── lambda_function.py
    │   ├── tool-schema.json
    │   └── requirements.txt
    ├── service_locator/
    │   ├── lambda_function.py
    │   ├── tool-schema.json
    │   └── requirements.txt
    └── web_search/
        ├── lambda_function.py
        ├── tool-schema.json
        └── requirements.txt
```

For deeper development patterns (structured logging, JSON error responses, etc.) see the “Gateway Tools” section in `../README.md`.
