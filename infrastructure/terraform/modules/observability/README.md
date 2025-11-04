# Observability Module

Provisions logging and tracing infrastructure for AgentCore platform.

## Features

- CloudWatch log groups with configurable retention
- X-Ray tracing configuration
- Centralized log aggregation
- Correlation ID propagation
- SSM Parameter Store integration

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Environment name | string | - | yes |
| agent_namespace | Agent namespace | string | - | yes |
| xray_tracing | Enable X-Ray | bool | true | no |
| log_retention_days | Log retention | number | 7 | no |
| tags | Additional tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| platform_log_group | Platform log group name |
| xray_enabled | X-Ray tracing status |

## SSM Parameters

- `/agentcore/{env}/observability/xray_enabled`
- `/agentcore/{env}/observability/log_group`
