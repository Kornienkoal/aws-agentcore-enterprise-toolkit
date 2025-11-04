# Identity Module

Provisions AWS Cognito User Pools and App Clients for AgentCore authentication.

## Features

- Cognito User Pool for user authentication
- Machine-to-machine client with client_credentials flow
- OAuth2 support for frontend applications
- SSM Parameter Store integration for configuration publishing

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|----------|
| environment | Environment name | string | - | yes |
| agent_namespace | Agent namespace for naming | string | - | yes |
| tags | Additional resource tags | map(string) | {} | no |

## Outputs

| Name | Description |
|------|-------------|
| pool_id | Cognito User Pool ID |
| machine_client_id | M2M App Client ID |
| client_secret_parameter | SSM parameter name for client secret |

## SSM Parameters

- `/agentcore/{env}/identity/pool_id`
- `/agentcore/{env}/identity/machine_client_id`
- `/agentcore/{env}/identity/client_secret` (SecureString)

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.5.0 |
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
| [aws_cognito_resource_server.agentcore](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_resource_server) | resource |
| [aws_cognito_user_pool.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool) | resource |
| [aws_cognito_user_pool_client.frontend](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_client) | resource |
| [aws_cognito_user_pool_client.machine](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_client) | resource |
| [aws_cognito_user_pool_domain.main](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cognito_user_pool_domain) | resource |
| [aws_ssm_parameter.client_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.client_secret](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.cognito_domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.domain](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.frontend_client_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.frontend_client_secret](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.machine_client_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.pool_arn](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.pool_id](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_ssm_parameter.scope](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/ssm_parameter) | resource |
| [aws_region.current](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/region) | data source |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_agent_namespace"></a> [agent\_namespace](#input\_agent\_namespace) | Agent namespace for resource naming (e.g., myorg/team) | `string` | n/a | yes |
| <a name="input_environment"></a> [environment](#input\_environment) | Environment name (dev, staging, prod) | `string` | n/a | yes |
| <a name="input_identity_scope"></a> [identity\_scope](#input\_identity\_scope) | Default OAuth2 scope string to publish under /identity/scope (optional) | `string` | `"openid"` | no |
| <a name="input_tags"></a> [tags](#input\_tags) | Additional tags for resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_domain"></a> [domain](#output\_domain) | Cognito User Pool Domain |
| <a name="output_frontend_client_id"></a> [frontend\_client\_id](#output\_frontend\_client\_id) | Frontend App Client ID |
| <a name="output_machine_client_id"></a> [machine\_client\_id](#output\_machine\_client\_id) | M2M App Client ID |
| <a name="output_pool_arn"></a> [pool\_arn](#output\_pool\_arn) | Cognito User Pool ARN |
| <a name="output_pool_id"></a> [pool\_id](#output\_pool\_id) | Cognito User Pool ID |
<!-- END_TF_DOCS -->
