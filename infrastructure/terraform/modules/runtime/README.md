# Runtime Module

Provisions IAM execution roles, CloudWatch Logs, and X-Ray tracing for Amazon Bedrock AgentCore agents deployed via SDK.

## Overview

This module creates the foundational runtime infrastructure needed for deploying agents using the Bedrock AgentCore SDK. It provisions:

- **IAM Execution Role**: Allows Bedrock service to assume the role with permissions for:
  - Bedrock model invocation (Claude, Titan, etc.)
  - Bedrock Gateway invocation
  - Lambda tool invocation
  - CloudWatch Logs
  - X-Ray tracing
  - SSM Parameter Store read access
- **CloudWatch Log Group**: Centralized logging for all agents
- **SSM Parameters**: Configuration outputs for SDK-based deployment

## Agent Deployment Pattern

Agents are deployed via the Bedrock AgentCore SDK, NOT as Lambda functions. This module provides the execution role that the Bedrock service assumes when running your agent code.

**Example SDK deployment:**
```python
import boto3
from bedrock_agentcore import AgentBuilder

# Read infrastructure outputs from SSM
ssm = boto3.client('ssm')
runtime_role_arn = ssm.get_parameter(Name='/agentcore/dev/runtime/execution_role_arn')['Parameter']['Value']
gateway_id = ssm.get_parameter(Name='/agentcore/dev/gateway/gateway_id')['Parameter']['Value']
memory_id = ssm.get_parameter(Name='/agentcore/dev/memory/memory_id')['Parameter']['Value']

# Deploy agent via SDK
agent = AgentBuilder() \
    .with_name("customer-support") \
    .with_role(runtime_role_arn) \
    .with_gateway(gateway_id) \
    .with_memory(memory_id) \
    .with_model("anthropic.claude-3-7-sonnet-20250219-v1:0") \
    .build()

agent.deploy()
```

## Features

- **Bedrock Service Principals**: IAM role trusts both:
  - `bedrock.amazonaws.com` for SDK-based agent execution
  - `bedrock-agentcore.amazonaws.com` for containerized AgentCore runtime
- **Lambda Backward Compatibility**: Also trusts `lambda.amazonaws.com` for migration scenarios
- **Gateway Integration**: Permissions to invoke Bedrock Gateway and access shared Lambda tools
- **Memory Access**: Compatible with Memory module's IAM policy (attach via SDK)
- **Least-Privilege IAM**: Scoped permissions with resource tags and conditions
- **CloudWatch Observability**: Centralized logging with configurable retention
- **X-Ray Tracing**: Distributed tracing for agent execution paths
- **SSM Parameter Store**: Read access for runtime configuration

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Environment name (dev/staging/prod) | string | - | yes |
| agent_namespace | Agent namespace (e.g., myorg/team) | string | - | yes |
| xray_tracing_enabled | Enable AWS X-Ray tracing | bool | true | no |
| log_retention_days | CloudWatch log retention in days | number | 7 | no |
| tags | Additional resource tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| execution_role_arn | IAM execution role ARN (use for SDK agent deployment) |
| execution_role_name | IAM execution role name |
| log_group_name | CloudWatch log group name |
| log_group_arn | CloudWatch log group ARN |

## SSM Parameters

All outputs are published to SSM Parameter Store for SDK-based agent deployment:

- `/agentcore/{env}/runtime/execution_role_arn` - IAM role ARN to pass to AgentBuilder
- `/agentcore/{env}/runtime/execution_role_name` - IAM role name
- `/agentcore/{env}/runtime/log_group_name` - CloudWatch log group name
- `/agentcore/{env}/runtime/xray_enabled` - X-Ray tracing status (true/false)

## IAM Permissions

The execution role includes the following policies:

### Bedrock Model Invocation
```hcl
bedrock:InvokeModel
bedrock:InvokeModelWithResponseStream
```
**Scope**: Claude (anthropic.claude-*) and Titan (amazon.titan-*) models

### Bedrock Gateway Access
```hcl
bedrock-agent:InvokeAgentGateway
bedrock-agent:GetAgentGateway
```
**Scope**: Agent gateways tagged with matching Environment

### Lambda Tool Invocation
```hcl
lambda:InvokeFunction
```
**Scope**: Functions matching pattern `{agent_namespace}-*-tool-*`

### ECR Image Pull (AgentCore Runtime)
```hcl
ecr:GetAuthorizationToken
ecr:BatchGetImage
ecr:GetDownloadUrlForLayer
```
**Scope**: ECR repositories matching `bedrock-agentcore-*`

### CloudWatch Logs
```hcl
logs:CreateLogStream
logs:PutLogEvents
```
**Scope**: Via AWSLambdaBasicExecutionRole

### X-Ray Tracing (Optional)
```hcl
xray:PutTraceSegments
xray:PutTelemetryRecords
```
**Condition**: `xray_tracing_enabled = true`

### SSM Parameter Store
```hcl
ssm:GetParameter
ssm:GetParameters
```
**Scope**: `/agentcore/{env}/*` parameters

## Memory Module Integration

The Memory module creates a separate IAM policy for accessing Bedrock Memory APIs:
- `bedrock-agent:GetAgentMemory`
- `bedrock-agent:PutAgentMemory`
- `bedrock-agent:DeleteAgentMemory`

**To attach this policy to your agent:**
1. Read the policy ARN from SSM: `/agentcore/{env}/memory/iam_policy_arn`
2. Attach it to the execution role via SDK or Terraform data source

## Example Usage

```hcl
module "runtime" {
  source = "../../modules/runtime"

  environment            = "dev"
  agent_namespace        = "myorg/customer-support"
  xray_tracing_enabled   = true
  log_retention_days     = 30

  tags = {
    Team = "platform"
  }
}

# Use the execution role ARN in agent deployment scripts
output "agent_deployment_role" {
  value = module.runtime.execution_role_arn
}
```

## Dependencies

- **Identity Module**: Not required (Bedrock manages authentication internally)
- **Gateway Module**: Runtime role has permissions to invoke Gateway
- **Memory Module**: Compatible (attach Memory IAM policy as needed)
- **Observability Module**: Runtime logs flow to CloudWatch

## Migration Notes

**From Lambda-based agents:**
- Remove Lambda function resources
- Update agent deployment scripts to use Bedrock SDK
- Pass `execution_role_arn` to AgentBuilder instead of Lambda role
- CloudWatch log group remains the same (seamless log continuity)

**Trust Policy:**
- `bedrock.amazonaws.com` - For SDK-based agent execution
- `bedrock-agentcore.amazonaws.com` - For containerized AgentCore runtime
- `lambda.amazonaws.com` - Legacy support for backward compatibility

```

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | ~> 5.62 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | 5.100.0 |

## Modules

| Name | Source | Version |
|------|--------|---------|
| <a name="module_shared"></a> [shared](#module\_shared) | ../_shared | n/a |

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_log_group.runtime](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_iam_role.execution](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.bedrock_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.bedrock_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.ecr_pull](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.lambda_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy.ssm_read](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_iam_role_policy_attachment.logs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_iam_role_policy_attachment.xray](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment) | resource |
| [aws_ssm_parameter.execution_role_arn](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.execution_role_name](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.log_group_name](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.xray_enabled](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_caller_identity.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/caller_identity) | data source |
| [aws_iam_policy_document.assume_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.bedrock_gateway](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.bedrock_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.ecr_pull](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.lambda_invoke](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_iam_policy_document.ssm_read](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document) | data source |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |
| [aws_ssm_parameter.gateway_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/ssm_parameter) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_agent_namespace"></a> [agent\_namespace](#input\_agent\_namespace) | Agent namespace for resource naming | `string` | n/a | yes |
| <a name="input_environment"></a> [environment](#input\_environment) | Environment name (dev, staging, prod) | `string` | n/a | yes |
| <a name="input_log_retention_days"></a> [log\_retention\_days](#input\_log\_retention\_days) | CloudWatch Logs retention in days | `number` | `7` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Additional tags for resources | `map(string)` | `{}` | no |
| <a name="input_xray_tracing_enabled"></a> [xray\_tracing\_enabled](#input\_xray\_tracing\_enabled) | Enable X-Ray tracing | `bool` | `true` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_execution_role_arn"></a> [execution\_role\_arn](#output\_execution\_role\_arn) | IAM execution role ARN |
| <a name="output_execution_role_name"></a> [execution\_role\_name](#output\_execution\_role\_name) | IAM execution role name |
| <a name="output_log_group_arn"></a> [log\_group\_arn](#output\_log\_group\_arn) | CloudWatch log group ARN |
| <a name="output_log_group_name"></a> [log\_group\_name](#output\_log\_group\_name) | CloudWatch log group name |
<!-- END_TF_DOCS -->
