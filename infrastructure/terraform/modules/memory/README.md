# Memory Module

Provisions Bedrock AgentCore Memory via Lambda custom resource with multiple strategies.

## Resources

- Bedrock AgentCore Memory with userPreference and semantic strategies
- Point-in-time recovery enabled
- Pay-per-request billing
- IAM conditions for partition key enforcement
- SSM Parameter Store integration

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Environment name | string | - | yes |
| agent_namespace | Agent namespace | string | - | yes |
| enabled_strategies | Memory strategies to enable | list(string) | ["userPreferenceMemoryStrategy", "semanticMemoryStrategy"] | no |
| point_in_time_recovery | Enable PITR | bool | true | no |
| tags | Additional tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| memory_id | Bedrock Memory ID |
| memory_arn | Bedrock Memory ARN |

## SSM Parameters

- `/agentcore/{env}/memory/memory_id`
- `/agentcore/{env}/memory/memory_arn`
- `/agentcore/{env}/memory/enabled_strategies`
- `/agentcore/{env}/memory/table_arn`

## Partition Key Schema

- Partition key: `pk` (format: `{env}#{agent}#{user_id}`)
- Sort key: `sk` (format: `{session_id}#{timestamp}`)
