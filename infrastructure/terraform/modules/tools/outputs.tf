# Tools Module Outputs

# Map of tool name to Lambda function ARN
output "tool_lambda_arns" {
  description = "Map of tool name to Lambda function ARN"
  value       = { for k, v in module.tool_lambdas : k => v.lambda_function_arn }
}

# Registration function name
output "registration_function_name" {
  description = "Lambda function name for Gateway target registration"
  value       = module.targets_provisioner.lambda_function_name
}
