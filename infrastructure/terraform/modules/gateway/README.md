# Gateway Module

Provisions Bedrock AgentCore Gateway via Lambda custom resource for agent invocations and shared tools.

## Resources

- Bedrock AgentCore Gateway with Lambda MCP tool targets
- Lambda integration for MCP tools
- Resource policies enforcing least-privilege access
- SSM Parameter Store integration

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Environment name | string | - | yes |
| agent_namespace | Agent namespace | string | - | yes |
| cognito_user_pool_arn | Cognito pool ARN | string | - | yes |
| tags | Additional tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| gateway_id | Bedrock Gateway ID |
| gateway_arn | Bedrock Gateway ARN |
| invoke_url | Bedrock Gateway invoke URL |
| authorizer_id | Cognito authorizer ID |

## SSM Parameters

- `/agentcore/{env}/gateway/gateway_id`
- `/agentcore/{env}/gateway/gateway_arn`
- `/agentcore/{env}/gateway/invoke_url`
