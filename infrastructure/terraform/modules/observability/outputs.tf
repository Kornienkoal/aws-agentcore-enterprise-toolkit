# Observability Module Outputs

output "invocations_log_group" {
  description = "CloudWatch log group for agent invocations"
  value       = aws_cloudwatch_log_group.agent_invocations.name
}

output "tools_log_group" {
  description = "CloudWatch log group for agent tools"
  value       = aws_cloudwatch_log_group.agent_tools.name
}

output "gateway_log_group" {
  description = "CloudWatch log group for Bedrock Gateway access logs"
  value       = aws_cloudwatch_log_group.gateway.name
}

output "xray_sampling_rule" {
  description = "X-Ray sampling rule ARN"
  value       = aws_xray_sampling_rule.agent_traces.arn
}

output "kms_key_id" {
  description = "KMS key ID for log encryption (if enabled)"
  value       = var.enable_log_encryption ? aws_kms_key.logs[0].id : null
}

output "dashboard_name" {
  description = "CloudWatch dashboard name"
  value       = aws_cloudwatch_dashboard.agentcore.dashboard_name
}

output "gateway_latency_alarm" {
  description = "CloudWatch alarm for gateway latency"
  value       = aws_cloudwatch_metric_alarm.gateway_latency.arn
}

output "gateway_errors_alarm" {
  description = "CloudWatch alarm for gateway errors"
  value       = aws_cloudwatch_metric_alarm.gateway_errors.arn
}

output "memory_throttles_alarm" {
  description = "CloudWatch alarm for memory throttles"
  value       = aws_cloudwatch_metric_alarm.memory_throttles.arn
}

output "memory_read_latency_alarm" {
  description = "CloudWatch alarm for memory read latency"
  value       = aws_cloudwatch_metric_alarm.memory_read_latency.arn
}

# Publish outputs to SSM Parameter Store
resource "aws_ssm_parameter" "invocations_log_group" {
  name        = "${module.shared.ssm_prefix}/invocations_log_group"
  description = "CloudWatch log group for agent invocations"
  type        = "String"
  value       = aws_cloudwatch_log_group.agent_invocations.name
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "tools_log_group" {
  name        = "${module.shared.ssm_prefix}/tools_log_group"
  description = "CloudWatch log group for agent tools"
  type        = "String"
  value       = aws_cloudwatch_log_group.agent_tools.name
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "gateway_log_group" {
  name        = "${module.shared.ssm_prefix}/gateway_log_group"
  description = "CloudWatch log group for Bedrock Gateway access logs"
  type        = "String"
  value       = aws_cloudwatch_log_group.gateway.name
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "xray_enabled" {
  name        = "${module.shared.ssm_prefix}/xray_enabled"
  description = "Whether X-Ray tracing is enabled"
  type        = "String"
  value       = tostring(var.xray_tracing)
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "xray_sampling_rate" {
  name        = "${module.shared.ssm_prefix}/xray_sampling_rate"
  description = "X-Ray sampling rate"
  type        = "String"
  value       = tostring(var.xray_sampling_rate)
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "xray_sampling_rule_arn" {
  name        = "${module.shared.ssm_prefix}/xray_sampling_rule_arn"
  description = "X-Ray sampling rule ARN"
  type        = "String"
  value       = aws_xray_sampling_rule.agent_traces.arn
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "metrics_namespace" {
  name        = "${module.shared.ssm_prefix}/metrics_namespace"
  description = "CloudWatch metrics namespace"
  type        = "String"
  value       = "AWS/BedrockAgent"
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "dashboard_name" {
  name        = "${module.shared.ssm_prefix}/dashboard_name"
  description = "CloudWatch dashboard name"
  type        = "String"
  value       = aws_cloudwatch_dashboard.agentcore.dashboard_name
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "alarms_gateway_latency" {
  name        = "${module.shared.ssm_prefix}/alarms/gateway_latency"
  description = "CloudWatch alarm ARN for gateway latency"
  type        = "String"
  value       = aws_cloudwatch_metric_alarm.gateway_latency.arn
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "alarms_gateway_errors" {
  name        = "${module.shared.ssm_prefix}/alarms/gateway_errors"
  description = "CloudWatch alarm ARN for gateway errors"
  type        = "String"
  value       = aws_cloudwatch_metric_alarm.gateway_errors.arn
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "alarms_memory_throttles" {
  name        = "${module.shared.ssm_prefix}/alarms/memory_throttles"
  description = "CloudWatch alarm ARN for memory throttles"
  type        = "String"
  value       = aws_cloudwatch_metric_alarm.memory_throttles.arn
  tags        = module.shared.common_tags
}

resource "aws_ssm_parameter" "kms_key_id" {
  count       = var.enable_log_encryption ? 1 : 0
  name        = "${module.shared.ssm_prefix}/kms_key_id"
  description = "KMS key ID for log encryption"
  type        = "String"
  value       = aws_kms_key.logs[0].id
  tags        = module.shared.common_tags
}
