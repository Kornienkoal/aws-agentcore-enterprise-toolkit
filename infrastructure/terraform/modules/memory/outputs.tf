# Memory Module Outputs
#
# Publishes outputs to SSM Parameter Store per constitution paths:
# /agentcore/{env}/memory/*
#
# NOTE: Bedrock Memory outputs are published by the Lambda custom resource.
# The custom resource stores the following SSM parameters:
# - /agentcore/{env}/memory/memory_id
# - /agentcore/{env}/memory/memory_arn
# - /agentcore/{env}/memory/enabled_strategies
# - /agentcore/{env}/memory/short_term_ttl
# - /agentcore/{env}/memory/long_term_retention
# - /agentcore/{env}/memory/embedding_model_arn (if semantic enabled)
# - /agentcore/{env}/memory/max_tokens (if semantic enabled)

# Data source to read SSM parameters created by custom resource
data "aws_ssm_parameter" "memory_id" {
  name = "/agentcore/${var.environment}/memory/memory_id"

  depends_on = [null_resource.memory_provisioning]
}

data "aws_ssm_parameter" "memory_arn" {
  name = "/agentcore/${var.environment}/memory/memory_arn"

  depends_on = [null_resource.memory_provisioning]
}

data "aws_ssm_parameter" "enabled_strategies" {
  name = "/agentcore/${var.environment}/memory/enabled_strategies"

  depends_on = [null_resource.memory_provisioning]
}

# Terraform outputs (for module consumers)
output "memory_id" {
  description = "Bedrock Memory ID"
  value       = data.aws_ssm_parameter.memory_id.value
}

output "memory_arn" {
  description = "Bedrock Memory ARN"
  value       = data.aws_ssm_parameter.memory_arn.value
}

output "enabled_strategies" {
  description = "Comma-separated list of enabled memory strategies"
  value       = data.aws_ssm_parameter.enabled_strategies.value
}

output "iam_policy_arn" {
  description = "IAM policy ARN for agent access to Bedrock Memory"
  value       = aws_iam_policy.memory_access.arn
}

output "provisioner_function_name" {
  description = "Lambda provisioner function name"
  value       = module.memory_provisioner_lambda.lambda_function_name
}
