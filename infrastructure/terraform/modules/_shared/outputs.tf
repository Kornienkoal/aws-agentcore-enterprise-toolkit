# Shared Module Outputs
#
# Exposes locals for use in parent modules

output "name_prefix" {
  description = "Resource name prefix: {namespace}-{component}-{env}"
  value       = local.name_prefix
}

output "agentcore_name_prefix" {
  description = "Bedrock AgentCore resource name prefix (CamelCase for Gateway/Memory)"
  value       = local.agentcore_name_prefix
}

output "common_tags" {
  description = "Common tags for all resources"
  value       = local.common_tags
}

output "ssm_prefix" {
  description = "SSM parameter path prefix"
  value       = local.ssm_prefix
}
