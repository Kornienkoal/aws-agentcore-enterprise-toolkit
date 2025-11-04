# Tools Module

Provision and register global MCP tools (Lambda-based) for the AgentCore Gateway using Terraform.

Features:
- Packages and deploys tool Lambdas from `agents/global-tools/*`
- Python 3.13 runtime, X-Ray tracing, structured logging
- Idempotent registration of Gateway Targets via custom resource
- Standard tagging and SSM conventions

Inputs:
- `agent_namespace` (string)
- `environment` ("dev" | "staging" | "prod")
- `tags` (map)
- `gateway_ready_token` (string) — dependency token emitted by the Gateway module to ensure targets register after provisioning
- `tools` (list of objects):
  - `name` (string)
  - `source_dir` (string) — path relative to repository root (e.g., `global-tools/check_warranty`)
  - `handler` (string, optional, default `lambda_function.handler`)
  - `description` (string, optional)
  - `memory_size` (number, optional, default 256)
  - `timeout` (number, optional, default 15)
  - `environment` (map(string), optional)

Outputs:
- `tool_lambda_arns` — map of tool name to Lambda ARN
- `registration_function_name` — name of the registration Lambda

Notes:
- Lambda names follow: `{agent_namespace}-{tool}-tool-{env}`
- Invocation restricted via Gateway role IAM (identity-based policies)
- Note: Lambda resource-based policies for Gateway-only access are documented in research.md Decision 2 as a future enhancement
